# Smart Solutions — Monitoramento de Vinherias

Solução IoT para monitorar o ambiente de uma rede de vinherias. Cada loja tem um ESP32 que mede temperatura, umidade e luminosidade, envia as leituras ao FIWARE na nuvem e avisa no local, com luz e som, quando algo sai da faixa ideal. Um painel web único mostra todas as vinherias, guarda o histórico, permite ajustar a faixa ideal de cada uma e responde perguntas em linguagem natural por meio de um chatbot.

Projeto do **Check Point 5** de Edge Computing & Computer Systems — FIAP, Prof. Dr. Fábio H. Cabrini. Entrega em 26/10/2026.

> **Status:** em desenvolvimento. Firmware concluído e validado no Wokwi; backend, painel web e chatbot em construção. O andamento de cada etapa está na seção [Roadmap](#roadmap).

---

## Equipe — Smart Solutions

| Nome | RM |
|---|---|
| Eduarda Soares Moraes | RM569369 |
| Isac Nilton Fernandes de Oliveira | RM573282 |
| João Benedito de Oliveira Simplício | RM570206 |
| Julia Souza Matarazzo | RM571340 |
| Mariana Malagutti Gomes Peixoto | RM570290 |

---

## Links

| Recurso | Link |
|---|---|
| Simulação no Wokwi | _a definir_ |
| Vídeo de apresentação | _a definir_ |
| Collection do Postman | [`postman/CP5-Vinheria.postman_collection.json`](postman/CP5-Vinheria.postman_collection.json) |
| Documento de produto (PRD) | [`PRD.md`](PRD.md) |
| Plano de implementação | [`PLANO-CP5-VINHERIA.md`](PLANO-CP5-VINHERIA.md) |

---

## O problema

Vinho é sensível ao ambiente. Temperatura alta acelera o envelhecimento e pode estragar a bebida; umidade baixa resseca a rolha e deixa o oxigênio entrar; luz em excesso degrada os aromas. Em uma rede com lojas em várias cidades, ninguém consegue vigiar cada adega o tempo todo, e um problema costuma ser percebido só quando o estoque já foi afetado.

## A solução

- **No local:** o ESP32 lê os sensores a cada 2 segundos, mostra os valores num LCD e, quando recebe um alerta, pisca o LED azul e toca no buzzer um padrão de som diferente para cada problema (temperatura, umidade ou luminosidade). Assim, quem está na loja sabe o que aconteceu só pelo som.
- **Na nuvem:** o FIWARE recebe as leituras por MQTT, mantém o estado atual de cada vinheria e guarda o histórico.
- **No painel:** uma visão geral mostra todas as vinherias com status (ok, alerta ou offline). Para cada vinheria há gráficos históricos, score de qualidade do ambiente, ajuste da faixa ideal e linha do tempo de alertas. O backend compara cada leitura com a faixa e dispara o alerta remoto sozinho.
- **Chatbot:** responde perguntas como "como está a temperatura da vinheria de São Paulo?" ou "qual vinheria está mais úmida agora?" com os dados reais do histórico, e avisa por conta própria quando alguma vinheria está em alerta ou offline.

### Funcionalidades

- Cadastro de várias vinherias (ID, nome e cidade), com provisionamento automático no FIWARE e remoção completa.
- Visão geral da frota com status, valores atuais, score e tempo desde a última leitura.
- Gráficos históricos dinâmicos por atributo (últimos N pontos ou intervalo de datas).
- Faixa ideal configurável por vinheria: dispara os alertas, define o score e é enviada ao ESP32, que a mostra no LCD.
- Alerta remoto sonoro e visual, com padrão distinto por anomalia, disparado automaticamente ou pelo painel.
- Detecção de vinheria offline (sem leitura há mais de 30 s, configurável).
- Aviso global no painel (faixa fixa e notificações) quando uma vinheria entra em alerta, fica offline ou volta ao normal.
- Histórico de alertas com início, fim e duração.
- Score de qualidade do ambiente de 0 a 100.
- Chatbot com Google Gemini que responde por vinheria em linguagem natural.
- Exportação de relatório CSV e PDF por vinheria.
- Animação de marca no boot do LCD (cacho de uva rolando para dentro da taça).

---

## Arquitetura

A solução é organizada em sete camadas, do sensor à tela:

```
[1] Dispositivo (Edge)        ESP32 + DHT-11/22 + LDR + buzzer + LED azul + LCD 16x2
[2] Comunicação               Wi-Fi -> Mosquitto MQTT (1883), payload UltraLight 2.0
[3] Middleware IoT            IoT Agent MQTT (4041): UltraLight <-> NGSI-v2
[4] Contexto                  Orion Context Broker (1026) + MongoDB (27017)
[5] Persistência histórica    STH-Comet (8666)
[6] Aplicação                 Backend FastAPI + SQLite (triggers, alertas, score, chatbot, relatórios)
[7] Apresentação              Painel React + Vite
```

As camadas 2 a 5 rodam em Docker numa instância AWS EC2 com IP elástico (stack [`fabiocabrini/fiware`](https://github.com/fabiocabrini/fiware)). O backend e o painel rodam localmente e se conectam à EC2.

**Fluxo de telemetria:** sensor → ESP32 → MQTT → IoT Agent → Orion → STH-Comet → backend → painel.
**Fluxo de comando:** painel/backend → Orion → IoT Agent → MQTT → ESP32 (LED e buzzer) → confirmação de volta ao Orion.

Diagramas detalhados em [`docs/arquitetura.md`](docs/arquitetura.md).

---

## Stack

| Camada | Tecnologias |
|---|---|
| Firmware | C++ (Arduino) no ESP32 · `PubSubClient` · `DHT sensor library` · `Adafruit Unified Sensor` · `LiquidCrystal I2C` · simulação no Wokwi |
| Middleware | FIWARE em Docker na AWS EC2: Orion Context Broker, IoT Agent MQTT (UltraLight 2.0), STH-Comet, Mosquitto, MongoDB |
| Backend | Python 3.11+ · FastAPI · Uvicorn · httpx · Pydantic · SQLite · pandas · matplotlib · reportlab · testes com pytest e respx |
| Front-end | React (JavaScript, sem TypeScript) · Vite · Chart.js via react-chartjs-2 · react-router-dom |
| Chatbot | Google Gemini (`gemini-2.5-flash`) via `google-genai`, com function calling |
| Ferramentas | Postman · Git/GitHub |

---

## Detalhes técnicos

### Hardware

| Componente | Pino do ESP32 | Função |
|---|---|---|
| DHT-11 (DHT-22 no Wokwi) | GPIO 4 | Temperatura e umidade |
| LDR (divisor de tensão) | GPIO 34 (ADC) | Luminosidade, mapeada de 0 a 100 % |
| LED azul | GPIO 2 | Alerta visual |
| Buzzer | GPIO 5 | Alerta sonoro |
| LCD 16x2 I2C | SDA/SCL, endereço `0x27` | Boot animado e carrossel de leituras |

O relógio do LCD vem de NTP (UTC−3). Cada instância do firmware é configurada num único bloco no topo do `.ino` (`CONFIGURAÇÃO DESTA INSTÂNCIA`): ID da vinheria, rede Wi-Fi, endereço do broker e modelo do DHT.

### Nomes no FIWARE

| Item | Valor |
|---|---|
| Device | `vinheria00N` (ex.: `vinheria001`) |
| Entidade | `urn:ngsi-ld:Vinheria:00N`, type `Vinheria` |
| Headers | `fiware-service: smart` · `fiware-servicepath: /` |
| API key | `TEF` |
| Atributos | `t` → `temperature` · `h` → `humidity` · `l` → `luminosity` |
| Comandos | `blink_temp` · `blink_hum` · `blink_lux` · `alert_off` · `set_limits` |

### MQTT

| Tópico | Direção | Exemplo |
|---|---|---|
| `/TEF/<device_id>/attrs` | ESP32 → FIWARE | `t\|24.3\|h\|58\|l\|42` |
| `/TEF/<device_id>/cmd` | FIWARE → ESP32 | `vinheria001@blink_temp\|` |
| `/TEF/<device_id>/cmdexe` | ESP32 → FIWARE | `vinheria001@blink_temp\|ok` |

### Padrões de alerta

| Anomalia | Comando | LED azul | Buzzer |
|---|---|---|---|
| Temperatura | `blink_temp` | pisca a cada 500 ms | 2 bipes curtos a cada 2 s |
| Umidade | `blink_hum` | pisca a cada 250 ms | 1 bipe longo a cada 3 s |
| Luminosidade | `blink_lux` | pisca a cada 125 ms | 3 bipes rápidos a cada 2 s |
| — | `alert_off` | apagado | silêncio |

Os padrões rodam numa máquina de estado com `millis()`, sem `delay()`, então o ESP32 continua lendo e publicando enquanto alerta.

### Regras de alerta

O backend consulta o Orion a cada ciclo (uma chamada para a frota inteira) e compara cada leitura com a faixa ideal da vinheria:

- leitura sai da faixa → envia o comando do atributo uma única vez e abre o alerta;
- todas as leituras voltam à faixa → envia `alert_off` e fecha o alerta;
- vinheria sem leitura nova há mais de 30 s → fica offline, abre alerta `offline` e não recebe comandos até voltar.

A faixa padrão de uma vinheria nova é 12–18 °C, 50–70 % de umidade e luz de 0 a 30 %.

### API do backend

```
GET/PUT  /api/config                  configuração (IP do FIWARE, portas, intervalos)
GET      /api/config/health           saúde de Orion, IoT Agent e STH-Comet
GET      /api/fleet                   status de todas as vinherias
GET/POST /api/devices                 listar / cadastrar vinheria
DELETE   /api/devices/{id}            remover vinheria (local e FIWARE)
GET      /api/devices/{id}/current    estado atual
GET      /api/devices/{id}/history    histórico (lastN ou intervalo de datas)
GET      /api/devices/{id}/score      score de qualidade
GET/PUT  /api/devices/{id}/triggers   faixa ideal
GET      /api/alerts                  histórico de alertas
GET      /api/report                  relatório CSV ou PDF
POST     /api/chat                    chatbot
```

Documentação interativa (Swagger) em `http://localhost:8000/docs` com o backend rodando.

### Princípios de código

- Encapsulamento em camadas: rota → service → cliente FIWARE. Só `services/fiware_client.py` faz HTTP com o FIWARE; componentes React só usam `src/api/client.js`.
- Nenhum IP, porta ou chave fixos em código de lógica: tudo vem do `.env` ou da configuração salva. O IP do FIWARE pode ser trocado em runtime pelo painel.
- Código comentado em português.
- Segredos (como a chave do Gemini) só no `.env`, que não é versionado.

---

## Estrutura do repositório

```
projetovinheria/
├── README.md
├── PRD.md                  documento de produto
├── PLANO-CP5-VINHERIA.md   plano de implementação
├── CLAUDE.md               regras de trabalho do repositório
├── docs/                   arquitetura e manuais
├── firmware/               sketch do ESP32, animação de boot e projeto Wokwi
├── postman/                collections do FIWARE
├── backend/                API FastAPI (em construção)
└── frontend/               painel React (em construção)
```

---

## Como rodar

O passo a passo completo estará em [`docs/manual-software.md`](docs/manual-software.md). Resumo:

**1. FIWARE na EC2**

```bash
git clone https://github.com/fabiocabrini/fiware
cd fiware
docker-compose up -d
```

Liberar no Security Group as portas 1026, 4041, 8666 e 1883.

**2. Firmware**

Abrir o projeto no Wokwi (ou na Arduino IDE para o ESP32 físico), ajustar o bloco `CONFIGURAÇÃO DESTA INSTÂNCIA` com o ID da vinheria e o IP do broker, e iniciar a simulação.

**3. Backend**

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # preencher FIWARE_HOST e GEMINI_API_KEY
uvicorn app.main:app --reload
pytest tests -v
```

**4. Front-end**

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

**5. Cadastrar a vinheria** pelo painel, na página de dispositivos, com o mesmo ID usado no firmware.

---

## Manuais

| Documento | Conteúdo | Status |
|---|---|---|
| [`docs/arquitetura.md`](docs/arquitetura.md) | Diagrama em camadas, fluxos de telemetria e de comando | pronto |
| [`docs/manual-hardware.md`](docs/manual-hardware.md) | Lista de materiais, pinagem, montagem, DHT-11 vs DHT-22 | a fazer |
| [`docs/manual-software.md`](docs/manual-software.md) | EC2 e FIWARE, IP elástico, Postman, backend, front-end, rodar uma vinheria Wokwi em outro computador, troubleshooting | a fazer |

---

## Roadmap

- [x] Firmware ESP32: sensores, publicação MQTT, alertas não bloqueantes, várias instâncias
- [x] Marca Smart Solutions e animação de boot no LCD
- [x] Documentação base: PRD, README e arquitetura
- [x] Backend: configuração e cliente FIWARE
- [ ] Backend: cadastro de vinherias, histórico e score
- [ ] Backend: motor de triggers, offline e log de alertas
- [ ] Firmware: recebimento e exibição da faixa ideal
- [ ] Painel: base, configuração e cadastro
- [ ] Painel: visão geral, gráficos, triggers, alertas e score
- [ ] Chatbot Gemini multi-vinheria
- [ ] Relatórios CSV e PDF
- [ ] Manuais, collection final do Postman e vídeo
