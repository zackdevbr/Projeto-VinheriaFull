# Arquitetura — Smart Solutions: Monitoramento de Vinherias

Este documento descreve como as partes da solução se conectam: as camadas, os componentes de cada uma e os caminhos que os dados percorrem do sensor até a tela e da tela de volta ao dispositivo.

Os contratos completos (payloads de provisionamento, endpoints e regras) estão no [`PRD.md`](../PRD.md) e no [`PLANO-CP5-VINHERIA.md`](../PLANO-CP5-VINHERIA.md).

---

## 1. Visão em camadas

A solução tem sete camadas. Cada uma conversa só com a vizinha, o que permite trocar ou testar uma parte sem mexer nas outras.

| # | Camada | Onde roda | Componentes |
|---|---|---|---|
| 1 | Dispositivo (Edge) | Cada vinheria | ESP32, DHT-11 (DHT-22 no Wokwi), LDR, buzzer, LED azul, LCD 16x2 I2C |
| 2 | Comunicação | AWS EC2 | Wi-Fi + Mosquitto MQTT (1883), payload UltraLight 2.0 |
| 3 | Middleware IoT | AWS EC2 | IoT Agent MQTT (4041) |
| 4 | Contexto | AWS EC2 | Orion Context Broker (1026) + MongoDB (27017) |
| 5 | Persistência histórica | AWS EC2 | STH-Comet (8666) |
| 6 | Aplicação | Notebook (local) | Backend FastAPI + SQLite + Google Gemini |
| 7 | Apresentação | Notebook (navegador) | Painel React + Vite |

As camadas 2 a 5 são a stack `fabiocabrini/fiware` em containers Docker numa EC2 com **IP elástico**, então o endereço não muda quando a instância é desligada e religada.

```mermaid
flowchart TB
    subgraph EDGE["1 · Dispositivo (Edge) — N vinherias"]
        direction LR
        V1["ESP32 vinheria001<br/>DHT-11 físico"]
        V2["ESP32 vinheria002<br/>Wokwi"]
        VN["ESP32 vinheria00N<br/>Wokwi"]
    end

    subgraph EC2["AWS EC2 — IP elástico — Docker"]
        MQTT["2 · Mosquitto MQTT<br/>:1883"]
        IOTA["3 · IoT Agent MQTT<br/>:4041<br/>UltraLight ⇄ NGSI-v2"]
        ORION["4 · Orion Context Broker<br/>:1026<br/>estado atual"]
        MONGO[("MongoDB<br/>:27017")]
        STH["5 · STH-Comet<br/>:8666<br/>séries históricas"]
    end

    subgraph LOCAL["Notebook da apresentação"]
        API["6 · Backend FastAPI<br/>:8000"]
        DB[("SQLite<br/>devices · triggers<br/>alertas · config")]
        WEB["7 · Painel React<br/>:5173"]
    end

    GEMINI["Google Gemini<br/>gemini-2.5-flash"]

    V1 & V2 & VN <-->|"Wi-Fi · MQTT"| MQTT
    MQTT <--> IOTA
    IOTA <-->|"NGSI-v2"| ORION
    ORION --- MONGO
    ORION -->|"subscriptions"| STH
    STH --- MONGO
    API <-->|"HTTP"| IOTA
    API <-->|"HTTP"| ORION
    API -->|"HTTP"| STH
    API --- DB
    API <-->|"function calling"| GEMINI
    WEB <-->|"HTTP /api"| API
```

Todas as vinherias usam o mesmo broker e o mesmo IoT Agent. Cada uma se diferencia pelo `device_id` (`vinheria00N`), que define os tópicos MQTT e a entidade no Orion (`urn:ngsi-ld:Vinheria:00N`, type `Vinheria`).

---

## 2. Fluxo de telemetria (sensor → tela)

A cada 2 segundos, cada ESP32 lê os sensores e publica uma linha UltraLight. O IoT Agent traduz os nomes curtos (`t`, `h`, `l`) para os nomes longos da entidade (`temperature`, `humidity`, `luminosity`) e preenche o `TimeInstant`. O Orion notifica o STH-Comet, que guarda o histórico. O backend lê o estado atual no Orion e o histórico no STH, e o painel lê o backend.

```mermaid
sequenceDiagram
    autonumber
    participant ESP as ESP32 (vinheria001)
    participant MQ as Mosquitto :1883
    participant IA as IoT Agent :4041
    participant OR as Orion :1026
    participant ST as STH-Comet :8666
    participant BE as Backend FastAPI
    participant FE as Painel React

    loop a cada 2 s
        ESP->>MQ: publish /TEF/vinheria001/attrs<br/>t|24.3|h|58|l|42
        MQ->>IA: entrega a mensagem
        IA->>OR: atualiza temperature, humidity,<br/>luminosity e TimeInstant
        OR->>ST: notifica (subscription por atributo)
    end

    loop a cada poll_seconds
        BE->>OR: GET /v2/entities?type=Vinheria
        OR-->>BE: estado atual de todas as vinherias
        BE->>BE: atualiza status da frota,<br/>avalia faixas e offline
    end

    loop a cada 5 s
        FE->>BE: GET /api/fleet
        BE-->>FE: status, valores, score e alertas ativos
    end

    FE->>BE: GET /api/devices/vinheria001/history?attr=t&lastN=50
    BE->>ST: GET /STH/v1/contextEntities/.../attributes/temperature?lastN=50
    ST-->>BE: série histórica
    BE-->>FE: [{ ts, value }, ...]
```

Pontos de atenção:

- O payload UltraLight usa os nomes curtos; Orion, STH-Comet, subscriptions e comandos usam os nomes longos.
- Se a leitura do DHT falha (`NaN`), o ESP32 não publica naquele ciclo.
- O backend faz **uma única** chamada ao Orion por ciclo para a frota inteira, não uma por vinheria.

---

## 3. Fluxo de comando (tela → dispositivo)

Comandos seguem o caminho inverso. O backend faz um `PATCH` no atributo de comando da entidade; o Orion encaminha ao IoT Agent (pela registration que o próprio IoT Agent cria ao provisionar o device), que publica no tópico `cmd` da vinheria. O ESP32 executa e responde no tópico `cmdexe`, e o resultado volta ao Orion.

```mermaid
sequenceDiagram
    autonumber
    participant BE as Backend FastAPI
    participant OR as Orion :1026
    participant IA as IoT Agent :4041
    participant MQ as Mosquitto :1883
    participant ESP as ESP32 (vinheria002)

    BE->>OR: PATCH /v2/entities/urn:ngsi-ld:Vinheria:002/attrs<br/>{ "blink_temp": { "type": "command", "value": "" } }
    OR->>IA: encaminha o comando (registration)
    IA->>MQ: publish /TEF/vinheria002/cmd<br/>vinheria002@blink_temp|
    MQ->>ESP: entrega o comando
    ESP->>ESP: LED azul 500 ms + 2 bipes curtos a cada 2 s
    ESP->>MQ: publish /TEF/vinheria002/cmdexe<br/>vinheria002@blink_temp|ok
    MQ->>IA: entrega o ack
    IA->>OR: blink_temp_status = OK, blink_temp_info = ok
```

Só a vinheria endereçada reage: as outras não assinam o tópico `/TEF/vinheria002/cmd`.

| Comando | Efeito no ESP32 |
|---|---|
| `blink_temp` | LED azul a cada 500 ms + 2 bipes curtos a cada 2 s |
| `blink_hum` | LED azul a cada 250 ms + 1 bipe longo a cada 3 s |
| `blink_lux` | LED azul a cada 125 ms + 3 bipes rápidos a cada 2 s |
| `alert_off` | apaga o LED e silencia o buzzer |
| `set_limits` | guarda a faixa ideal recebida e a mostra no LCD |

---

## 4. Motor de triggers e detecção de offline

A decisão de alertar fica no backend; o ESP32 só obedece. O motor guarda um estado por par `(vinheria, atributo)` e só envia comando quando esse estado muda, então uma leitura que continua fora da faixa não gera comandos repetidos.

```mermaid
stateDiagram-v2
    [*] --> OK
    OK --> ALERTA: leitura fora da faixa<br/>envia blink_attr e abre alerta
    ALERTA --> ALERTA: continua fora<br/>nenhum comando
    ALERTA --> OK: volta à faixa<br/>fecha alerta e envia alert_off<br/>se nenhum outro atributo em alerta
    OK --> OFFLINE: TimeInstant parado<br/>há mais de offline_seconds
    ALERTA --> OFFLINE: TimeInstant parado<br/>há mais de offline_seconds
    OFFLINE --> OK: nova leitura chega<br/>fecha alerta offline
```

- **Offline:** uma vinheria cujo `TimeInstant` no Orion não muda há mais de `offline_seconds` (padrão 30 s) é marcada como offline, ganha um alerta com `attr="offline"` e não recebe comandos até voltar.
- **Isolamento:** o estado de uma vinheria nunca afeta o das outras.
- **Registro:** cada alerta fica no SQLite com vinheria, atributo, valor, início, fim e duração.

---

## 5. Fluxo da faixa ideal

A faixa ideal (mínimo e máximo de temperatura, umidade e luminosidade) é definida pelo usuário por vinheria. Ela é ao mesmo tempo o limite dos alertas e a referência do score de qualidade. Ao salvar, o backend a propaga para o FIWARE e para o dispositivo.

```mermaid
sequenceDiagram
    autonumber
    participant FE as Painel React
    participant BE as Backend FastAPI
    participant DB as SQLite
    participant OR as Orion :1026
    participant ESP as ESP32

    FE->>BE: PUT /api/devices/vinheria001/triggers<br/>{ temperature: [12, 18], humidity: [50, 70], luminosity: [0, 30] }
    BE->>BE: valida mínimo < máximo
    BE->>DB: grava a faixa
    BE->>OR: grava temp_min ... lux_max na entidade
    BE->>OR: PATCH set_limits = "12#59;18#59;50#59;70#59;0#59;30"
    OR-->>ESP: comando via IoT Agent e MQTT (fluxo da seção 3)
    ESP->>ESP: guarda a faixa e mostra no carrossel do LCD
    BE-->>FE: faixa salva
```

A partir do próximo ciclo, o motor de triggers e o score já usam a faixa nova. A forma exata de gravar os atributos `*_min`/`*_max` no Orion será confirmada contra a EC2 na Task 4.

---

## 6. Cadastro e remoção de uma vinheria

**Cadastro** (`POST /api/devices` com `device_id`, nome e cidade):

1. Valida o formato `vinheria00N` e deriva a entidade `urn:ngsi-ld:Vinheria:00N`.
2. Garante o service group no IoT Agent (`apikey TEF`, `timestamp: true`).
3. Provisiona o device no IoT Agent com os atributos (`t`, `h`, `l`) e os comandos.
4. Cria no Orion uma subscription por atributo, apontando para o STH-Comet.
5. Envia a faixa padrão à entidade e ao ESP32.
6. Grava no SQLite. Se algum passo no FIWARE falha, o cadastro local é desfeito.

**Remoção** (`DELETE /api/devices/{id}`): apaga o device no IoT Agent, a entidade e as subscriptions dela no Orion, e o cadastro local. O histórico no STH-Comet é mantido.

---

## 7. Camada de aplicação por dentro

O backend segue camadas estritas: rotas recebem a requisição e chamam services; só o `fiware_client` faz HTTP com o FIWARE. No painel, componentes nunca chamam `fetch` direto, só o `api/client.js`.

```mermaid
flowchart LR
    subgraph FRONT["Painel React"]
        PAGES["pages/<br/>Overview · VinheriaDetail<br/>Devices · Alerts · Chat"]
        COMP["components/"]
        CTX["context/<br/>ConfigContext · FleetContext"]
        CLIENT["api/client.js"]
        PAGES --> COMP
        PAGES --> CTX
        COMP --> CLIENT
        CTX --> CLIENT
    end

    subgraph BACK["Backend FastAPI"]
        ROUTES["api/routes_*.py"]
        SERV["services/<br/>device_registry · trigger_engine<br/>fleet_state · alert_log<br/>quality_score · report · chatbot"]
        FC["services/fiware_client.py"]
        CORE["core/<br/>config · db"]
        ROUTES --> SERV
        SERV --> FC
        SERV --> CORE
        FC --> CORE
    end

    CLIENT -->|"HTTP /api"| ROUTES
    FC -->|"HTTP"| FIWARE["FIWARE na EC2"]
    SERV -->|"chatbot"| GEM["Google Gemini"]
```

| Módulo | Responsabilidade |
|---|---|
| `core/config.py` | Lê o `.env` e mantém a configuração em runtime (IP do FIWARE, portas, intervalos) |
| `core/db.py` | Conexão e schema do SQLite |
| `services/fiware_client.py` | Única porta de saída HTTP para IoT Agent, Orion e STH-Comet |
| `services/device_registry.py` | Cadastro, remoção e busca de vinherias por id, nome ou cidade |
| `services/trigger_engine.py` | Ciclo do poller: compara leituras, detecta offline, envia comandos |
| `services/fleet_state.py` | Retrato em memória do status de todas as vinherias |
| `services/alert_log.py` | Abre, fecha e consulta alertas |
| `services/quality_score.py` | Score de 0 a 100 a partir da faixa ideal |
| `services/report.py` | Relatórios CSV e PDF |
| `services/chatbot.py` | Gemini com function calling sobre os services acima |

O IP do FIWARE vem do `.env` (`FIWARE_HOST`) e pode ser trocado em runtime pelo painel Avançado; o `fiware_client` monta as URLs a cada chamada a partir da configuração atual, sem reiniciar o backend.

---

## 8. Chatbot

O chatbot não acessa o FIWARE diretamente: ele chama funções do backend (tools), que usam os mesmos services do painel. A vinheria é citada em texto livre ("a de São Paulo", "vinheria002") e resolvida no backend.

```mermaid
sequenceDiagram
    autonumber
    participant FE as Painel (Chat)
    participant BE as Backend /api/chat
    participant GM as Google Gemini
    participant SV as Services (tools)

    FE->>BE: POST /api/chat { message, history }
    BE->>BE: anexa resumo do status da frota
    BE->>GM: mensagem + declaração das tools
    GM-->>BE: chamar estatisticas("São Paulo", "temperature")
    BE->>SV: resolve vinheria e consulta o STH-Comet
    SV-->>BE: média, mín, máx, tendência
    BE->>GM: resultado da tool
    GM-->>BE: resposta em português
    BE-->>FE: resposta
```

Tools disponíveis: `listar_vinherias`, `estado_atual`, `estatisticas`, `comparar`, `alertas` e `limites`. O loop de function calling tem no máximo 5 iterações por pergunta.
