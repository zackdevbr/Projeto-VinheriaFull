# CP5 — Vinheria Full: Plano de Implementação

> **Para executores:** use `superpowers:subagent-driven-development` ou `superpowers:executing-plans`. Passos usam checkbox `- [ ]`.

## Context

CP5 de Edge Computing & Computer Systems (Prof. Dr. Fábio H. Cabrini, FIAP) — entrega **26/10/2026**. Evolui o projeto Smart Lamp (LDR + LED via FIWARE/MQTT) para uma solução completa de monitoramento de vinherias: ESP32 com **DHT-11 + LDR + buzzer + LED azul**, integrado ao FIWARE em AWS EC2, com **dashboard web dinâmico** para cadastro de IoT Devices, gráficos históricos (STH-Comet 8666), ajuste de triggers e disparo remoto de alertas sonoros/visuais pelo front-end.

FIWARE e Postman já configurados pelo usuário (stack `fabiocabrini/fiware`). Equipe = mesma do Smart Lamp. Estado em 05/10/2026: Task 1 com os passos 1–5 prontos e sensores validados no Wokwi; falta o Passo 6.

**Critérios de nota:** Encapsulamento 10% · Diferencial 10% · Manual SW+HW 10% · Front-end 20% · GitHub/README/arquitetura 10% · Hands-on 40%.

**Decisões já tomadas (não reabrir):**
- Front-end: **React + JavaScript puro** (Vite, sem TypeScript).
- Back-end: **FastAPI + Uvicorn** (Swagger em `/docs`).
- Triggers: **backend decide, ESP32 obedece** — poller compara leituras com limites e envia comando; front-end controla tudo.
- Chatbot: **Google Gemini** (`google-genai`) com **function calling** sobre dados reais do STH-Comet.
- Execução na apresentação: dashboard local no notebook apontando para o IP público da EC2.
- **IP da EC2 muda a cada boot** → IP configurável em runtime pelo front, persistido no backend, usado por todos os módulos.
- Diferenciais: chatbot Gemini + exportar relatório CSV/PDF + score de qualidade do ambiente + histórico de alertas.

**Revisão de escopo (05/10/2026, após conversa com o professor) — também não reabrir:**
- **Múltiplas vinherias.** O sistema cadastra N vinherias e controla todas pelo mesmo site. Demo: 1 ESP32 físico (DHT-11) no hands-on + 4 Wokwi em outros computadores = 5 vinherias.
- **Nomes padrão:** `device_id = vinheria00N` e `entity_id = urn:ngsi-ld:Vinheria:00N` (type `Vinheria`). `vinheria001` é só o exemplo.
- **Cadastro:** `device_id`, `name` (ex.: "Vinheria São Paulo") e `city`. Triggers continuam por device, com default de vinheria.
- **Offline:** vinheria sem atualização de `TimeInstant` no Orion por mais de `offline_seconds` (default 30 s, configurável) fica offline: abre alerta `attr="offline"` e não recebe comando.
- **Um poller para a frota:** uma chamada `GET /v2/entities?type=Vinheria` por tick.
- **Aviso no site:** banner/toast global gerado no navegador a partir de `GET /api/fleet` (polling de 5 s). Sem WebSocket.
- **Chatbot multi-vinheria (sai do adiamento):** responde por vinheria em linguagem natural ("como está a temperatura da vinheria de São Paulo?") usando os registros do STH-Comet, e avisa sozinho de vinherias em alerta ou offline. As tools aceitam id, nome ou cidade como texto livre, resolvido no backend.
- **Ordem:** T1 → T0 → T2 → T3 → T4 → T5 → T6 → **T7A chatbot** → T7B relatórios (primeiro corte se o prazo apertar) → T8.

---

## Arquitetura em camadas

```
[1] Camada de Dispositivo (Edge)
    ESP32 + DHT-11 (DHT-22 no Wokwi) + LDR + Buzzer + LED azul
    Firmware .ino — leitura de sensores, publish UltraLight 2.0, execução de comandos de alerta

[2] Camada de Comunicação
    Wi-Fi -> Mosquitto MQTT (1883)
    Tópicos: /TEF/<device_id>/attrs (telemetria) · /TEF/<device_id>/cmd (comandos) · /TEF/<device_id>/cmdexe (ack)

[3] Camada de Middleware IoT
    IoT Agent MQTT (4041) — tradução UltraLight 2.0 <-> NGSI-v2, provisionamento de service group e devices

[4] Camada de Contexto
    Orion Context Broker (1026) — estado atual das entidades + subscriptions
    MongoDB (27017) — persistência interna

[5] Camada de Persistência Histórica
    STH-Comet (8666) — séries temporais consultadas por lastN / dateFrom-dateTo

[6] Camada de Aplicação (backend Python — FastAPI)
    fiware_client · device_registry · trigger_engine · alert_log · quality_score · report · chatbot (Gemini)
    SQLite local: devices, triggers, alertas, config

[7] Camada de Apresentação (React + Vite)
    Dashboard: Devices · Gráficos dinâmicos · Triggers · Alertas · Chat IA · Relatórios
```

---

## Estrutura de arquivos

```
projetovinheria/
├── README.md                       # integrantes, descrição, arquitetura, manual HW+SW, links Wokwi/vídeo
├── PRD.md                          # documento de produto (Task 0)
├── CLAUDE.md                       # regras de trabalho para agentes (Task 0)
├── docs/
│   ├── arquitetura.md              # diagrama em camadas + fluxo de dados
│   ├── manual-hardware.md          # montagem, pinagem, lista de materiais
│   └── manual-software.md          # instalação FIWARE/EC2, provisionamento, execução
├── firmware/
│   ├── vinheria_full.ino           # sketch principal
│   ├── diagram.json                # Wokwi (DHT-22 + LDR + buzzer + LED)
│   ├── libraries.txt
│   └── wokwi-project.txt
├── postman/
│   ├── FIWARE Descomplicado.postman_collection.json   # base do professor (já presente)
│   └── CP5-Vinheria.postman_collection.json           # fork adaptado: entidade Vinheria, 4 comandos, 3 subscriptions
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                 # app FastAPI, CORS, lifespan (start/stop poller)
│   │   ├── core/
│   │   │   ├── config.py           # Settings (env) + ConfigStore (IP EC2 em runtime)
│   │   │   └── db.py               # conexão SQLite + criação de schema
│   │   ├── models/schemas.py       # Pydantic: Device, Trigger, Reading, Alert, ChatMessage
│   │   ├── services/
│   │   │   ├── fiware_client.py    # httpx: IoT Agent 4041, Orion 1026, STH 8666
│   │   │   ├── device_registry.py  # CRUD devices + provisionamento no FIWARE
│   │   │   ├── trigger_engine.py   # loop asyncio: compara, debounce, offline, comanda alerta
│   │   │   ├── fleet_state.py      # snapshot em memória do status de todas as vinherias
│   │   │   ├── alert_log.py        # grava/consulta histórico de alertas
│   │   │   ├── quality_score.py    # score 0-100 do ambiente
│   │   │   ├── report.py           # CSV + PDF (matplotlib)
│   │   │   └── chatbot.py          # Gemini + function calling sobre os services
│   │   └── api/
│   │       ├── routes_config.py    # GET/PUT config (IP EC2, intervalo do poller)
│   │       ├── routes_devices.py
│   │       ├── routes_data.py      # histórico, estado atual, score
│   │       ├── routes_fleet.py     # visão geral da frota (status de todas as vinherias)
│   │       ├── routes_triggers.py
│   │       ├── routes_alerts.py
│   │       ├── routes_report.py
│   │       └── routes_chat.py
│   └── tests/                      # pytest + respx (mock HTTP do FIWARE)
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                 # layout + rotas
        ├── api/client.js           # fetch wrapper (base URL do backend)
        ├── context/
        │   ├── ConfigContext.jsx
        │   └── FleetContext.jsx    # polling de /api/fleet (5 s) + eventos de transição
        ├── components/
        │   ├── FiwareBar.jsx       # input do IP da EC2 + status de conexão
        │   ├── AlertBanner.jsx     # faixa fixa + toasts de alerta/offline
        │   ├── VinheriaCard.jsx    # card da visão geral (status, valores, score)
        │   ├── DeviceForm.jsx      # device_id, nome, cidade
        │   ├── DeviceList.jsx
        │   ├── SensorChart.jsx     # Chart.js: linha dinâmica por atributo
        │   ├── GaugeScore.jsx
        │   ├── TriggerPanel.jsx    # sliders min/max temp, umidade, luminosidade
        │   ├── AlertTimeline.jsx
        │   └── ChatBox.jsx
        └── pages/
            ├── Overview.jsx        # grid de cards, uma por vinheria
            ├── VinheriaDetail.jsx  # gráficos, score, triggers e alertas de uma vinheria
            ├── Devices.jsx
            ├── Triggers.jsx
            ├── Alerts.jsx
            └── Chat.jsx
```

---

## Contratos-chave

**Entidade FIWARE padrão** (segue o padrão do Smart Lamp; `vinheria001` é o exemplo, cada nova vinheria segue `vinheria00N`):
- `device_id`: `vinheria00N` (regex `^vinheria\d{3}$`) · `entity_name`: `urn:ngsi-ld:Vinheria:00N` · `entity_type`: `Vinheria`
- Headers: `fiware-service: smart` · `fiware-servicepath: /`
- API key: `TEF` · protocolo `PDI-IoTA-UltraLight` (MQTT)
- Atributos: `t` (temperature), `h` (humidity), `l` (luminosity)
- Comandos: `blink_temp`, `blink_hum`, `blink_lux`, `alert_off`

**Payload UltraLight publicado pelo ESP32:**
`/TEF/vinheria001/attrs` → `t|24.3|h|58|l|42`

**Comando (backend → device):** `PATCH http://<EC2>:1026/v2/entities/urn:ngsi-ld:Vinheria:001/attrs`
```json
{ "blink_temp": { "type": "command", "value": "" } }
```

**Sequência de provisionamento** (derivada de `postman/FIWARE Descomplicado.postman_collection.json`, que usa `{{url}}` sem valor fixo — mesma ideia do IP em runtime). Todos os requests levam `fiware-service: smart` e `fiware-servicepath: /`.

1. `POST :4041/iot/services` — service group (idempotente; tratar 409 como OK)
```json
{ "services": [ { "apikey": "TEF", "cbroker": "http://<EC2>:1026", "entity_type": "Thing", "resource": "", "timestamp": true } ] }
```
> `timestamp: true` faz o IoT Agent preencher `TimeInstant` a cada medição; a detecção de offline depende disso. Confirmar na EC2 no smoke da Task 3; se o campo não vier, parar e voltar ao planejamento.
2. `POST :4041/iot/devices` — device com atributos e comandos
```json
{ "devices": [ {
  "device_id": "vinheria001",
  "entity_name": "urn:ngsi-ld:Vinheria:001",
  "entity_type": "Vinheria",
  "protocol": "PDI-IoTA-UltraLight",
  "transport": "MQTT",
  "commands": [
    { "name": "blink_temp", "type": "command" },
    { "name": "blink_hum",  "type": "command" },
    { "name": "blink_lux",  "type": "command" },
    { "name": "alert_off",  "type": "command" }
  ],
  "attributes": [
    { "object_id": "t", "name": "temperature", "type": "Float" },
    { "object_id": "h", "name": "humidity",    "type": "Float" },
    { "object_id": "l", "name": "luminosity",  "type": "Integer" }
  ]
} ] }
```
3. `POST :1026/v2/registrations` — **obrigatório**, senão o `PATCH` de comando falha
```json
{
  "description": "Vinheria Commands",
  "dataProvided": {
    "entities": [ { "id": "urn:ngsi-ld:Vinheria:001", "type": "Vinheria" } ],
    "attrs": ["blink_temp", "blink_hum", "blink_lux", "alert_off"]
  },
  "provider": { "http": { "url": "http://<EC2>:4041" }, "legacyForwarding": true }
}
```
4. `POST :1026/v2/subscriptions` — **uma por atributo** (3 chamadas: `temperature`, `humidity`, `luminosity`)
```json
{
  "description": "Notify STH-Comet of temperature changes",
  "subject": {
    "entities": [ { "id": "urn:ngsi-ld:Vinheria:001", "type": "Vinheria" } ],
    "condition": { "attrs": ["temperature"] }
  },
  "notification": {
    "http": { "url": "http://<EC2>:8666/notify" },
    "attrs": ["temperature"],
    "attrsFormat": "legacy"
  }
}
```
5. Consulta histórica: `GET :8666/STH/v1/contextEntities/type/Vinheria/id/urn:ngsi-ld:Vinheria:001/attributes/temperature?lastN=30`

> Atenção: o `object_id` curto (`t`/`h`/`l`) é o que vai no payload UltraLight; o nome longo (`temperature`/`humidity`/`luminosity`) é o que o Orion e o STH usam. Comando e subscription usam o nome longo.

**Alerta sonoro distinto por anomalia** (buzzer, não bloqueante, via `millis()`):
| Anomalia | LED azul | Buzzer |
|---|---|---|
| Temperatura | pisca 500 ms | 2 bipes curtos (100 ms) a cada 2 s |
| Umidade | pisca 250 ms | 1 bipe longo (700 ms) a cada 3 s |
| Luminosidade | pisca 125 ms | 3 bipes rápidos (60 ms) a cada 2 s |

**Endpoints do backend:**
```
GET/PUT  /api/config                  # { ec2_ip, orion_port, sth_port, iota_port, poll_seconds, offline_seconds }
GET      /api/config/health            # testa Orion/IoT Agent/STH no IP atual
GET      /api/fleet                    # status de todas as vinherias (ok|alerta|offline), valores, score, alertas ativos
GET/POST /api/devices                  # listar / cadastrar { device_id, name, city } (provisiona no IoT Agent + subscription STH)
DELETE   /api/devices/{id}
GET      /api/devices/{id}/current     # estado atual via Orion
GET      /api/devices/{id}/history     # ?attr=t&lastN=100  ou  ?dateFrom&dateTo  (STH 8666)
GET      /api/devices/{id}/score       # quality_score
GET/PUT  /api/devices/{id}/triggers    # limites min/max por atributo
GET      /api/alerts                   # ?device_id&limit
GET      /api/report                   # ?device_id&format=csv|pdf
POST     /api/chat                     # { message, history[] } -> resposta Gemini (sem device_id: o bot resolve a vinheria pelo texto)
```

**Resposta de `GET /api/fleet`:**
```json
[{ "device_id": "vinheria001", "name": "Vinheria São Paulo", "city": "São Paulo",
   "status": "ok|alerta|offline", "last_seen": "2026-10-20T14:03:11Z", "seconds_since": 4,
   "current": { "temperature": 14.2, "humidity": 62, "luminosity": 20 },
   "score": 92, "active_alerts": [{ "attr": "temperature", "value": 21.3, "since": "..." }] }]
```

**Função do trigger engine** (estado por `(device_id, attr)`, com histerese para não tremer):
```
leitura fora da faixa    -> se estado == OK:    envia blink_<attr>, grava alerta, estado = ALERTA
leitura dentro da faixa  -> se estado == ALERTA: envia alert_off (se nenhum outro atributo em alerta),
                                                 fecha alerta no log, estado = OK
```

---

## Global Constraints

- Python 3.11+; `requirements.txt` com versões fixadas: `fastapi`, `uvicorn[standard]`, `httpx`, `pydantic`, `python-dotenv`, `google-genai`, `pandas`, `matplotlib`, `reportlab`, `pytest`, `respx`.
- Node 20+; front em **JavaScript puro** (`.jsx`), sem TypeScript. Deps: `react`, `react-dom`, `react-router-dom`, `chart.js`, `react-chartjs-2`.
- **Todo o código comentado** (exigência da entrega) — comentários em português explicando propósito de cada módulo/função.
- Nenhum IP, chave ou porta hardcoded em módulo de lógica: sempre via `ConfigStore`/`.env`. `ANTHROPIC`/`GEMINI_API_KEY` só em `.env` (nunca commitado; `.env.example` sim).
- Modelo Gemini default: `gemini-2.5-flash`, sobrescrevível por `GEMINI_MODEL`.
- Firmware: `#define DHTTYPE DHT22` (Wokwi) com comentário de como trocar para `DHT11` (hardware real). Nenhum `delay()` nos padrões de alerta.
- Commits frequentes, mensagens `feat:`/`docs:`/`test:`.

---

## Tarefas

### Task 0: Documentação base (PRD + CLAUDE.md + esqueleto do README)

**Files:** criar `PRD.md`, `CLAUDE.md`, `README.md`, `docs/arquitetura.md`

- [ ] **Passo 1:** escrever `PRD.md` com as seções: Visão e problema (monitoramento global de vinherias) · Objetivos e critérios de aceite mapeados nos pesos da nota · Personas (enólogo/operador, professor-avaliador) · Escopo (in/out) · Requisitos funcionais numerados RF01..RFnn (cadastro de device, gráficos dinâmicos, ajuste de triggers, alerta remoto com som distinto, chat IA, relatório, score, log de alertas) · Requisitos não funcionais (IP da EC2 trocável em runtime, código comentado, encapsulamento em camadas, rodar local) · Arquitetura em camadas (copiar o bloco deste plano) · Contratos FIWARE e tabela de alertas · Riscos (IP dinâmico, DHT-11 vs DHT-22, limites do free tier, chave Gemini) · Cronograma até 26/10/2026 · Entregáveis (GitHub, .ino, dashboard+requirements.txt, link Wokwi, vídeo, Forms).
- [x] **Passo 2 (FEITO):** `CLAUDE.md` já escrito na raiz — contrato Opus planeja / Sonnet executa, formato obrigatório de plano (Contexto → Objetivo → Detalhes técnicos → Ferramentas → Passos → Verificação), passos de 2–5 min com evidência e commit por passo, stack fixada, regras de camadas e nomes canônicos. Conteúdo original previsto: stack fixada (FastAPI + React JS puro + Gemini), estrutura de pastas, regras — comentários em português, nada hardcoded, camadas não se cruzam (rota não chama `httpx` direto; só `services`), testes com `pytest` + `respx`, não commitar `.env`, nomes de entidade/atributos/comandos canônicos, convenção de commits, comandos de dev (`uvicorn app.main:app --reload`, `npm run dev`).
- [ ] **Passo 3:** `README.md` com integrantes (Eduarda Soares Moraes RM569369, Isac Nilton Fernandes de Oliveira RM573282, João Benedito de Oliveira Simplício RM570206, Julia Souza Matarazzo RM571340, Mariana Malagutti Gomes Peixoto RM570290), descrição da solução, placeholders de links (Wokwi, vídeo) e sumário dos manuais.
- [ ] **Passo 4:** `docs/arquitetura.md` com o diagrama em camadas (mermaid) e o fluxo sensor → MQTT → IoT Agent → Orion → STH → backend → React, mais o fluxo reverso de comando.
- [ ] **Passo 5:** commit `docs: add PRD, CLAUDE.md and architecture baseline`.

### Task 1: Firmware ESP32 (`firmware/vinheria_full.ino`)

**Files:** criar `firmware/vinheria_full.ino`, `firmware/diagram.json`, `firmware/libraries.txt`
**Produces:** tópicos/atributos/comandos consumidos pelo backend.

- [ ] **Passo 1:** base no sketch do Smart Lamp (WiFi + PubSubClient + tópicos `/TEF/<id>/attrs|cmd|cmdexe`); trocar id para `vinheria001`.
- [ ] **Passo 2:** adicionar DHT (`DHT.h`, pino 4, `DHTTYPE` comentado DHT11/DHT22) e LDR (ADC 34, mapear 0–100 %).
- [ ] **Passo 3:** publicar a cada 2 s `t|<temp>|h|<umid>|l|<lux>`; se leitura DHT for `NaN`, não publicar aquele ciclo e logar no Serial.
- [ ] **Passo 4:** implementar máquina de estado de alerta não bloqueante (`millis()`): variável `alertMode` ∈ {NONE, TEMP, HUM, LUX}; LED azul (GPIO 2) e buzzer (GPIO 5, `tone`/`ledcWriteTone`) seguindo a tabela de padrões; comandos `blink_temp|blink_hum|blink_lux|alert_off` no callback MQTT; responder em `/TEF/vinheria001/cmdexe` com `vinheria001@<cmd>|ok`.
- [ ] **Passo 5:** montar `diagram.json` do Wokwi (ESP32 + DHT22 + LDR + buzzer + LED azul + resistores) e `libraries.txt` (`PubSubClient`, `DHT sensor library`, `Adafruit Unified Sensor`).
- [ ] **Passo 6 (teste):** rodar no Wokwi, conferir no Serial a publicação e, via Postman (`PATCH` command), ver LED/buzzer mudarem de padrão por anomalia e pararem com `alert_off`.
- [ ] **Passo 7:** commit `feat: add ESP32 firmware with DHT, LDR and multi-pattern alerts`.

### Task 2: Backend — config, DB e cliente FIWARE

**Files:** criar `backend/requirements.txt`, `.env.example`, `app/main.py`, `app/core/config.py`, `app/core/db.py`, `app/models/schemas.py`, `app/services/fiware_client.py`, `app/api/routes_config.py`, `tests/test_fiware_client.py`, `tests/test_config.py`
**Produces:** `ConfigStore.get()/update()`, `FiwareClient(base_cfg)` com `provision_service_group()`, `provision_device(device)`, `register_commands(device)`, `subscribe_attr(device, attr)`, `get_entity(entity_id)`, `send_command(entity_id, command)`, `query_history(entity_type, entity_id, attr, last_n=None, date_from=None, date_to=None)`, `health()`.

- [ ] **Passo 1:** teste falhando — `ConfigStore` persiste `ec2_ip` no SQLite e `FiwareClient` monta URLs `http://<ip>:1026/...`, `:4041`, `:8666` a partir do config atual (trocar o IP troca a URL sem reiniciar o app).
- [ ] **Passo 2:** rodar `pytest backend/tests -v` → falha.
- [ ] **Passo 3:** implementar `config.py` (Settings via `.env` + ConfigStore em SQLite), `db.py` (schema: `config`, `devices`, `triggers`, `alerts`), `schemas.py`, `fiware_client.py` (httpx, headers `fiware-service`/`fiware-servicepath`, timeouts, erros traduzidos em `HTTPException`), `routes_config.py` (GET/PUT + `/health` pingando as três portas).
- [ ] **Passo 4:** `main.py` com CORS liberado para `http://localhost:5173` e inclusão dos routers; rodar `pytest` → passa; subir `uvicorn app.main:app --reload` e checar `/docs`.
- [ ] **Passo 5:** commit `feat: add config store and FIWARE client layer`.

### Task 3: Backend — cadastro de devices e leitura de dados

**Files:** criar `app/services/device_registry.py`, `app/services/quality_score.py`, `app/api/routes_devices.py`, `app/api/routes_data.py`, `tests/test_device_registry.py`, `tests/test_quality_score.py`
**Consumes:** `FiwareClient`, `ConfigStore`. **Produces:** `DeviceRegistry.create/list/delete`, `quality_score(reading)`.

- [ ] **Passo 1:** teste falhando — `create_device` grava no SQLite e executa a sequência completa de provisionamento (service group → device → `register_commands` → `subscribe_attr` para os 3 atributos), devolvendo o device com `entity_name` derivado do id; `quality_score` devolve 100 em condição ideal (temp 12–18 °C, umid 50–70 %, luz ≤ 30 %) e penaliza proporcionalmente fora dela.
- [ ] **Passo 2:** rodar os testes → falham (mock HTTP com `respx`).
- [ ] **Passo 3:** implementar registry (rollback no SQLite se o provisionamento falhar), `quality_score`, rotas de device (POST/GET/DELETE), rotas de dados (`/current`, `/history` com `lastN` ou janela de datas, `/score`), normalizando a resposta do STH para `[{ "ts": iso, "value": float }]`.
- [ ] **Passo 4:** testes passam; smoke real contra a EC2: cadastrar `vinheria001` e ver o Wokwi aparecer no Orion.
- [ ] **Passo 5:** commit `feat: add device registry, history queries and quality score`.

### Task 4: Backend — triggers, poller e log de alertas

**Files:** criar `app/services/trigger_engine.py`, `app/services/alert_log.py`, `app/api/routes_triggers.py`, `app/api/routes_alerts.py`, `tests/test_trigger_engine.py`; modificar `app/main.py` (lifespan start/stop da task)
**Consumes:** `FiwareClient`, `DeviceRegistry`. **Produces:** `TriggerEngine.tick()` (uma passada, testável sem loop), `TriggerEngine.run()` (loop asyncio), `AlertLog.open/close/list`.

- [ ] **Passo 1:** teste falhando com leituras sintéticas — valor acima do máximo dispara exatamente um `blink_temp` e abre um alerta; segundo tick com o mesmo valor **não** reenvia comando; retorno à faixa envia `alert_off` e fecha o alerta; duas anomalias simultâneas mantêm o alerta ativo até a última normalizar.
- [ ] **Passo 2:** rodar → falha.
- [ ] **Passo 3:** implementar `trigger_engine` (dict de estado por `(device_id, attr)`, histerese configurável, `tick()` puro + `run()` com `asyncio.sleep(poll_seconds)`), `alert_log`, rotas de triggers (GET/PUT por device, defaults de vinheria) e de alertas; iniciar/parar a task no lifespan do FastAPI.
- [ ] **Passo 4:** testes passam; teste manual: baixar o máximo de temperatura pelo `PUT /triggers` e ver o ESP32 piscar/apitar, depois voltar e ver parar.
- [ ] **Passo 5:** commit `feat: add trigger engine with remote alert dispatch and alert log`.

### Task 5: Front-end React — base, config de IP e devices

**Files:** criar `frontend/package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/api/client.js`, `src/context/ConfigContext.jsx`, `src/components/FiwareBar.jsx`, `DeviceForm.jsx`, `DeviceList.jsx`, `src/pages/Devices.jsx`
**Consumes:** `/api/config`, `/api/devices`.

- [ ] **Passo 1:** scaffold Vite + React (JS), instalar deps, `vite.config.js` com proxy `/api` → `http://localhost:8000`.
- [ ] **Passo 2:** `client.js` — wrapper `request(path, options)` com base URL do backend (`localStorage`, default `http://localhost:8000`) e tratamento de erro padronizado.
- [ ] **Passo 3:** `ConfigContext` carrega `/api/config` no mount e expõe `config`/`saveConfig`; `FiwareBar` fixo no topo com input do **IP da EC2**, botão Salvar e indicador verde/vermelho vindo de `/api/config/health` (revalida a cada 30 s). Esse é o único lugar onde o IP é digitado.
- [ ] **Passo 4:** página Devices — formulário (device_id, entity_type, rótulo/local) + lista com status e botão excluir.
- [ ] **Passo 5 (teste):** `npm run dev`, trocar o IP com a EC2 desligada (indicador vermelho) e ligada (verde); cadastrar e remover um device.
- [ ] **Passo 6:** commit `feat: add React dashboard shell with runtime FIWARE IP config and device CRUD`.

### Task 6: Front-end — gráficos dinâmicos, triggers, alertas e score

**Files:** criar `src/components/SensorChart.jsx`, `GaugeScore.jsx`, `TriggerPanel.jsx`, `AlertTimeline.jsx`, `src/pages/Dashboard.jsx`, `Triggers.jsx`, `Alerts.jsx`

- [ ] **Passo 1:** `SensorChart` — `react-chartjs-2` Line, props `deviceId`/`attr`/`lastN`, auto-refresh a cada 10 s, seletor de janela (lastN 20/50/100 ou dateFrom–dateTo), linhas tracejadas nos limites do trigger.
- [ ] **Passo 2:** `Dashboard` — três cards (temperatura, umidade, luminosidade) com valor atual + gráfico, `GaugeScore` com o score e semáforo, e badge de alerta ativo.
- [ ] **Passo 3:** `TriggerPanel` — min/max para os três atributos com validação (min < max), salvando em `PUT /api/devices/{id}/triggers`; feedback de sucesso.
- [ ] **Passo 4:** `AlertTimeline` — lista de `/api/alerts` com tipo, valor, início, fim e duração.
- [ ] **Passo 5 (teste):** com o Wokwi rodando, apertar o LDR/temperatura no simulador e ver gráfico, badge, timeline e o ESP32 reagindo.
- [ ] **Passo 6:** commit `feat: add dynamic charts, trigger tuning, score gauge and alert timeline`.

### Task 7: Diferencial — chatbot Gemini e relatórios

> **Adiada por decisão do usuário.** Fazer depois das Tasks 0–6. Nesta task entram também `.gitignore` (ignorando `.env`, `__pycache__/`, `node_modules/`, `*.db`) e `backend/.env.example` com `GEMINI_API_KEY=` vazio. A chave real só no `.env` local, nunca commitada. Até lá, `routes_chat` não existe e o front não mostra a aba Chat.

**Files:** criar `app/services/chatbot.py`, `app/services/report.py`, `app/api/routes_chat.py`, `routes_report.py`, `src/components/ChatBox.jsx`, `src/pages/Chat.jsx`, `tests/test_chatbot_tools.py`
**Consumes:** `routes_data`/`alert_log`/`quality_score`. **Produces:** `ask(message, device_id) -> str`.

- [ ] **Passo 1:** teste falhando nas **tools** (funções puras, sem chamar a API): `tool_get_current`, `tool_get_stats` (média/min/máx/desvio/oscilação = máx−mín por janela), `tool_get_history`, `tool_get_alerts`, `tool_get_triggers` — validados com dados sintéticos via pandas.
- [ ] **Passo 2:** rodar → falha; implementar as tools e fazer passar.
- [ ] **Passo 3:** `chatbot.py` — `google.genai` com declaração das tools, loop de function calling (máx. 5 iterações), system instruction: responder em português, só com dados retornados pelas tools, citar números e unidades, recomendar ação de vinheria quando houver anomalia.
- [ ] **Passo 4:** `report.py` — CSV via pandas e PDF via matplotlib + reportlab (gráfico dos três atributos, estatísticas e alertas do período); `routes_report` devolve `StreamingResponse` com `Content-Disposition`.
- [ ] **Passo 5:** `ChatBox` — histórico de mensagens, textarea, estado de carregando, chips de perguntas prontas ("qual a média de temperatura hoje?", "houve picos de luminosidade?", "quais alertas nas últimas 24 h?"); botão de exportar CSV/PDF no Dashboard.
- [ ] **Passo 6 (teste):** perguntar as três chips com dados reais no STH e conferir que os números batem com o gráfico; baixar CSV e PDF.
- [ ] **Passo 7:** commit `feat: add Gemini chatbot with data tools and CSV/PDF reports`.

### Task 8: Manuais, Postman e fechamento da entrega

**Files:** criar `docs/manual-hardware.md`, `docs/manual-software.md`, `postman/CP5-Vinheria.postman_collection.json`; modificar `README.md`, `PRD.md`

- [ ] **Passo 1:** `manual-hardware.md` — lista de materiais, tabela de pinagem (DHT-11 GPIO 4, LDR GPIO 34, buzzer GPIO 5, LED azul GPIO 2), esquema de montagem, cuidados (resistor de pull-up do DHT, divisor do LDR) e diferenças DHT-11 vs DHT-22.
- [ ] **Passo 2:** `manual-software.md` — subir a EC2, `docker-compose up -d` do `fabiocabrini/fiware`, portas no Security Group (1026, 4041, 8666, 1883), provisionamento via Postman, instalar/rodar backend (`pip install -r requirements.txt`, `.env`, `uvicorn`) e front (`npm install`, `npm run dev`), **procedimento de troca de IP após reiniciar a EC2** e troubleshooting.
- [ ] **Passo 3:** criar `postman/CP5-Vinheria.postman_collection.json` a partir da collection base do professor: variável `{{url}}` mantida, entidade `urn:ngsi-ld:Vinheria:001`/type `Vinheria`, os 4 comandos no provisionamento e na registration, e as 3 subscriptions (temperature, humidity, luminosity) — remover os requests de Lamp que não se aplicam.
- [ ] **Passo 4:** finalizar `README.md` (arquitetura em camadas, links do Wokwi e do vídeo, prints do dashboard) e revisar o `PRD.md` contra o que foi construído.
- [ ] **Passo 5:** roteiro do pitch/vídeo em `docs/` (problema → arquitetura → demo ao vivo do alerta → diferenciais → encerramento), 5–7 min.
- [ ] **Passo 6:** commit `docs: add hardware/software manuals, Postman collection and final README`.

---

## Verificação end-to-end (ensaio do hands-on)

1. EC2 ligada; `docker ps` mostra orion, iot-agent, sth-comet, mosquitto, mongo.
2. `GET /api/config/health` com o IP novo → três portas OK.
3. Wokwi (ou ESP32 físico) conectado; `GET /api/devices/vinheria001/current` retorna `t`, `h`, `l`.
4. `GET /api/devices/vinheria001/history?attr=t&lastN=20` retorna série do STH e o gráfico desenha.
5. Pelo front, baixar o máximo de temperatura → LED azul pisca a 500 ms + 2 bipes curtos; subir o limite de novo → para. Repetir para umidade (bipe longo) e luminosidade (3 bipes rápidos), confirmando padrões distintos.
6. Timeline de alertas mostra os três eventos com início, fim e duração.
7. Chat: "qual foi a média e o pico de temperatura na última hora?" → números conferem com o gráfico.
8. Exportar CSV e PDF do período.
9. `pytest backend/tests -v` tudo verde.
