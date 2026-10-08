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
- ~~IP da EC2 muda a cada boot~~ → **substituído na revisão 2:** a EC2 usa **IP elástico** (fixo entre liga/desliga). O IP continua configurável em runtime pelo front e persistido no backend, mas o default vem do `.env` (`FIWARE_HOST`), então no uso normal ninguém precisa digitá-lo.
- Diferenciais: chatbot Gemini + exportar relatório CSV/PDF + score de qualidade do ambiente + histórico de alertas.

**Revisão de escopo (05/10/2026, após conversa com o professor) — também não reabrir:**
- **Múltiplas vinherias.** O sistema cadastra N vinherias e controla todas pelo mesmo site. Demo: 1 ESP32 físico (DHT-11) no hands-on + 4 Wokwi em outros computadores = 5 vinherias.
- **Nomes padrão:** `device_id = vinheria00N` e `entity_id = urn:ngsi-ld:Vinheria:00N` (type `Vinheria`). `vinheria001` é só o exemplo.
- **Cadastro:** `device_id`, `name` (ex.: "Vinheria São Paulo") e `city`. Triggers continuam por device, com default de vinheria.
- **Offline:** vinheria sem atualização de `TimeInstant` no Orion por mais de `offline_seconds` (default 30 s, configurável) fica offline: abre alerta `attr="offline"` e não recebe comando.
- **Um poller para a frota:** uma chamada `GET /v2/entities?type=Vinheria` por tick.
- **Aviso no site:** banner/toast global gerado no navegador a partir de `GET /api/fleet` (polling de 5 s). Sem WebSocket.
- **Chatbot multi-vinheria (sai do adiamento):** responde por vinheria em linguagem natural ("como está a temperatura da vinheria de São Paulo?") usando os registros do STH-Comet, e avisa sozinho de vinherias em alerta ou offline. As tools aceitam id, nome ou cidade como texto livre, resolvido no backend.
- **Ordem:** T1 (até o Passo 6b) → T1B (marca + boot animado + IP elástico) → commit final da T1 → T0 → T2 → T3 → T4 → T5 → T6 → **T7A chatbot** → T7B relatórios (primeiro corte se o prazo apertar) → T8.

**Revisão 2 (05/10/2026) — também não reabrir:**
- **IP elástico na EC2.** O IP do FIWARE fica fixo. Default no `backend/.env` (`FIWARE_HOST`) e no bloco de configuração do firmware (`BROKER_MQTT`); o campo de IP do site vira configuração avançada (recolhida), e o indicador de saúde continua visível.
- **Marca Smart Solutions.** A empresa fictícia da equipe é **Smart Solutions**; o nome "Vinheria Agnello" sai do projeto. No LCD, o boot mostra "Smart Solutions" centralizado (linha 2 vazia) e em seguida uma **animação de um cacho de uva sendo espremido e enchendo uma taça**. A animação é **só no LCD**; no site, apenas o nome "Smart Solutions" no cabeçalho e no `<title>`.

**Revisão 3 (05/10/2026, durante a Task 0) — também não reabrir:**
- **Faixa ideal = limites dos triggers.** Um único min/max por atributo por vinheria, definido pelo usuário no painel. Ele dispara os alertas e define o score 100 (penalidade proporcional fora da faixa). A faixa 12–18 °C / 50–70 % / luz 0–30 % vira só o default de vinheria recém-cadastrada.
- **A faixa é propagada.** Ao salvar (`PUT /api/devices/{id}/triggers`): grava no SQLite, publica `temp_min`, `temp_max`, `hum_min`, `hum_max`, `lux_min`, `lux_max` como atributos da entidade no Orion e envia ao ESP32 o novo comando **`set_limits`** com valor `"tmin;tmax;hmin;hmax;lmin;lmax"` (separador `;` para não colidir com o `|` do UltraLight). Também enviar no cadastro, com o default.
- **No ESP32 a faixa é só informativa.** Guarda a última recebida e mostra no carrossel do LCD. "Backend decide, ESP32 obedece" continua valendo.
- **Remoção apaga no FIWARE.** `DELETE /api/devices/{id}` remove o device no IoT Agent, a entidade e as subscriptions dela no Orion, e o cadastro local. O histórico no STH-Comet é mantido.
- **Impacto nas tasks:** Task 2 (`FiwareClient` ganha `delete_device`, `delete_entity`, `delete_subscriptions(entity_id)` e `update_attrs(entity_id, attrs)`); Task 3 (`quality_score(reading, limits)`, provisionamento declara `set_limits`, remoção completa); Task 4 (PUT de triggers propaga a faixa; confirmar na EC2 se os atributos `*_min/*_max` vão por `PATCH` direto no Orion ou provisionados no device); nova **Task 4B** de firmware (comando `set_limits` com parse e ack, tela do carrossel com a faixa), depois da Task 4.

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
│   ├── boot_animacao.h             # marca Smart Solutions: uva espremida enchendo a taça (LCD)
│   ├── diagram.json                # Wokwi (DHT-22 + LDR + buzzer + LED)
│   ├── libraries.txt
│   └── wokwi-project.txt
├── postman/
│   ├── FIWARE Descomplicado.postman_collection.json   # base do professor (já presente)
│   └── CP5-Vinheria.postman_collection.json           # fork adaptado: entidade Vinheria, 4 comandos, 3 subscriptions
├── backend/
│   ├── requirements.txt
│   ├── .env.example                # FIWARE_HOST (IP elástico), GEMINI_API_KEY, GEMINI_MODEL
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
- Comandos: `blink_temp`, `blink_hum`, `blink_lux`, `alert_off`, `set_limits` (revisão 3)
- Atributos da faixa ideal no Orion (revisão 3): `temp_min`, `temp_max`, `hum_min`, `hum_max`, `lux_min`, `lux_max`

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
  "provider": { "http": { "url": "http://iot-agent:4041" }, "legacyForwarding": false }
}
```
> **Corrigido em 05/10/2026 após teste real:** com `http://<EC2>:4041` e `legacyForwarding: true` o `PATCH` de comando devolvia `404 NotFound`. A forma que funciona (igual à do `Lamp:200` já em produção) usa o hostname interno do Docker `iot-agent` e `legacyForwarding: false`. O hostname deve vir de config/`.env` (`IOTA_INTERNAL_URL`, default `http://iot-agent:4041`), não ficar hardcoded. Registrations duplicadas para a mesma entidade também quebram o encaminhamento: o `provision_device` precisa remover registrations antigas da entidade antes de criar a nova (ou criar só se não existir).
>
> **Armadilhas do Postman vistas no teste:** a collection base tem comentários `//` dentro dos bodies JSON (o IoT Agent rejeita com `SyntaxError`), e todo request ao Orion precisa dos headers `fiware-service: smart` e `fiware-servicepath: /` (sem eles a entidade dá `NotFound`). A `postman/CP5-Vinheria.postman_collection.json` da Task 8 deve sair sem comentários e com os headers.
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
DELETE   /api/devices/{id}              # remove do SQLite, do IoT Agent e do Orion (entidade + subscriptions); STH mantido
GET      /api/devices/{id}/current     # estado atual via Orion
GET      /api/devices/{id}/history     # ?attr=t&lastN=100  ou  ?dateFrom&dateTo  (STH 8666)
GET      /api/devices/{id}/score       # quality_score
GET/PUT  /api/devices/{id}/triggers    # faixa ideal min/max por atributo; PUT propaga ao Orion e ao ESP32 (set_limits)
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

> **FEITA em 05/10/2026**, escrita pelo Opus por exceção autorizada pelo usuário (docs, não código). Commits `f21afdd` (PRD), `2a9a7de` (revisão 3), `bd3f218` (README) e o de `docs/arquitetura.md`, um por documento no lugar do commit único do Passo 5. Os 7 diagramas mermaid foram validados com `@mermaid-js/mermaid-cli`. **Revisar no fechamento (Task 8):** URL do repositório da stack `fabiocabrini/fiware` citada no README e o comando de instalação do FIWARE na seção "Como rodar".

**Files:** criar `PRD.md`, `CLAUDE.md`, `README.md`, `docs/arquitetura.md`

- [x] **Passo 1:** escrever `PRD.md` com as seções: Visão e problema (monitoramento global de vinherias) · Objetivos e critérios de aceite mapeados nos pesos da nota · Personas (enólogo/operador, professor-avaliador) · Escopo (in/out) · Requisitos funcionais numerados RF01..RFnn (cadastro de device, gráficos dinâmicos, ajuste de triggers, alerta remoto com som distinto, chat IA, relatório, score, log de alertas, **cadastro de múltiplas vinherias com nome e cidade, visão geral da frota, detecção de offline, aviso global no site, chatbot multi-vinheria em linguagem natural**) · Requisitos não funcionais (IP da EC2 trocável em runtime, código comentado, encapsulamento em camadas, rodar local) · Arquitetura em camadas (copiar o bloco deste plano) · Contratos FIWARE e tabela de alertas · Riscos (IP elástico: cobrança da AWS por IPv4 público mesmo com a EC2 desligada fora do free tier, e IP exposto no firmware público — portas abertas sem autenticação; DHT-11 vs DHT-22, limites do free tier, chave Gemini, 5 instâncias simultâneas na demo, `TimeInstant` ausente quebrando o offline) · Cronograma até 26/10/2026 · Entregáveis (GitHub, .ino, dashboard+requirements.txt, link Wokwi, vídeo, Forms).
- [x] **Passo 2 (FEITO):** `CLAUDE.md` já escrito na raiz — contrato Opus planeja / Sonnet executa, formato obrigatório de plano (Contexto → Objetivo → Detalhes técnicos → Ferramentas → Passos → Verificação), passos de 2–5 min com evidência e commit por passo, stack fixada, regras de camadas e nomes canônicos. Conteúdo original previsto: stack fixada (FastAPI + React JS puro + Gemini), estrutura de pastas, regras — comentários em português, nada hardcoded, camadas não se cruzam (rota não chama `httpx` direto; só `services`), testes com `pytest` + `respx`, não commitar `.env`, nomes de entidade/atributos/comandos canônicos, convenção de commits, comandos de dev (`uvicorn app.main:app --reload`, `npm run dev`).
- [x] **Passo 3:** `README.md` com integrantes (Eduarda Soares Moraes RM569369, Isac Nilton Fernandes de Oliveira RM573282, João Benedito de Oliveira Simplício RM570206, Julia Souza Matarazzo RM571340, Mariana Malagutti Gomes Peixoto RM570290), descrição da solução, placeholders de links (Wokwi, vídeo) e sumário dos manuais.
- [x] **Passo 4:** `docs/arquitetura.md` com o diagrama em camadas (mermaid), mostrando N devices publicando no mesmo Mosquitto/IoT Agent, e o fluxo sensor → MQTT → IoT Agent → Orion → STH → backend → React, mais o fluxo reverso de comando.
- [x] **Passo 5:** commit `docs: add PRD, CLAUDE.md and architecture baseline`.

### Task 1: Firmware ESP32 (`firmware/vinheria_full.ino`)

**Files:** criar `firmware/vinheria_full.ino`, `firmware/diagram.json`, `firmware/libraries.txt`
**Produces:** tópicos/atributos/comandos consumidos pelo backend.

- [ ] **Passo 1:** base no sketch do Smart Lamp (WiFi + PubSubClient + tópicos `/TEF/<id>/attrs|cmd|cmdexe`); trocar id para `vinheria001`.
- [ ] **Passo 2:** adicionar DHT (`DHT.h`, pino 4, `DHTTYPE` comentado DHT11/DHT22) e LDR (ADC 34, mapear 0–100 %).
- [ ] **Passo 3:** publicar a cada 2 s `t|<temp>|h|<umid>|l|<lux>`; se leitura DHT for `NaN`, não publicar aquele ciclo e logar no Serial.
- [ ] **Passo 4:** implementar máquina de estado de alerta não bloqueante (`millis()`): variável `alertMode` ∈ {NONE, TEMP, HUM, LUX}; LED azul (GPIO 2) e buzzer (GPIO 5, `tone`/`ledcWriteTone`) seguindo a tabela de padrões; comandos `blink_temp|blink_hum|blink_lux|alert_off` no callback MQTT; responder em `/TEF/vinheria001/cmdexe` com `vinheria001@<cmd>|ok`.
- [ ] **Passo 5:** montar `diagram.json` do Wokwi (ESP32 + DHT22 + LDR + buzzer + LED azul + resistores) e `libraries.txt` (`PubSubClient`, `DHT sensor library`, `Adafruit Unified Sensor`).
- [x] **Passo 6 (teste) — FEITO em 05/10/2026:** Wokwi publicando no IP elástico; `vinheria001` provisionada; `blink_temp` (2 bipes), `blink_hum` (1 longo), `blink_lux` (3 bipes) e `alert_off` (para tudo) confirmados, com ack `ok` no Orion e `TimeInstant` presente. **Observações para conferir no ESP32 físico:** um bipe residual depois do `alert_off` e o tom "desafinado" (prováveis artefatos do áudio do Wokwi a 37% de velocidade, não verificado); uma ocorrência isolada de 2 bipes no `blink_lux` (hipótese: `loop()` travado pela leitura do DHT, ciclo de 2 s alinhado ao intervalo de publicação; não reproduziu).
- [x] **Passo 6b (multi-instância) — FEITO em 05/10/2026:** `vinheria002` provisionada e rodando em segunda aba Wokwi; dados separados no Orion (001: 2,6 °C / 28,5 % / 31; 002: 24 °C / 40 % / 24); comando enviado só à 002 reagiu só nela. O status do comando ficou `PENDING` no Orion (ack atrasado pela simulação lenta, não investigado). **Achado:** o IoT Agent cria a registration dos comandos sozinho ao provisionar o device; registrar à mão duplica e quebra o encaminhamento, então o `register_commands` da Task 3 provavelmente é desnecessário (confirmar no planejamento da Task 3). Escopo original do passo: agrupar no topo do `.ino` um bloco `// ===== CONFIGURAÇÃO DESTA INSTÂNCIA =====` com `ID_DEVICE`, `SSID`, `PASSWORD`, `BROKER_MQTT` e `DHTTYPE` (cada computador edita só ele). Rodar uma segunda instância Wokwi com `vinheria002` e confirmar no Serial que os tópicos `/TEF/vinheria002/*` estão separados dos de `vinheria001`.
- [x] **Passo 7 — FEITO:** firmware commitado ao longo dos passos (último: `434c470`).

### Task 1B: Marca Smart Solutions, animação de boot no LCD e IP elástico

> **FEITA em 05/10/2026** (commits `b0009d4` a `35f7229`). A animação final difere do desenho original, por decisão do usuário durante a validação no Wokwi: cacho compacto de 6 uvas (talo, folha e fileiras de 3, 2 e 1) que se desfaz de baixo para cima; cada uva cai, rola pela pista de 3 caracteres e entra no copo, que enche em 5 níveis; 17 quadros, 4,25 s. Usa os 8 slots de caracteres do LCD e só reenvia ao display os bitmaps que mudaram. Os bitmaps foram gerados por script a partir de desenhos em texto. O usuário vai pedir **ajustes visuais depois**; os tempos ficam na tabela `ROTEIRO` de `firmware/boot_animacao.h`. Achado: a biblioteca no `libraries.txt` do Wokwi precisa ser `LiquidCrystal I2C` (com espaço), pois com underline o gerenciador não a encontra.

**Contexto.** Revisão 2. O boot atual (`logo()` em `firmware/vinheria_full.ino`) mostra "Smart Solutions / Vinheria Agn." e "Inicializando...". O nome "Vinheria Agnello" sai do projeto, e a equipe quer uma animação de marca. O IP da EC2 agora é elástico, então o `BROKER_MQTT` pode ser fixo no bloco de configuração. Vem depois do Passo 6b da Task 1 (que cria o bloco `CONFIGURAÇÃO DESTA INSTÂNCIA`) e antes do commit final da Task 1. Nada depois depende dela, exceto o manual de hardware (Task 8), que cita a sequência de boot.

**Objetivo.** No Wokwi, ao ligar o ESP32, o LCD mostra "Smart Solutions" centralizado por 2 s, depois uma animação de ~4 s de um cacho de uva sendo espremido e enchendo uma taça, depois "Inicializando..." e o carrossel normal com os ícones de taça/gota/sol intactos. O ESP32 conecta ao Mosquitto pelo IP elástico sem edição antes da sessão.

**Detalhes técnicos.**
- Criar `firmware/boot_animacao.h` (o `.ino` já passa de 500 linhas). Conteúdo: bitmaps e `void animacaoBoot(LiquidCrystal_I2C& lcd)`, com comentários em português.
- Restrição do hardware: o HD44780 guarda só **8 caracteres customizados** (slots 0–7), e os slots 0–3 já são usados por taça/gota/sol. A animação **redefine os slots 0–3 a cada quadro** com `lcd.createChar()`. O texto já impresso na tela muda sozinho quando o bitmap do slot muda.
- Depois de cada `createChar`, chamar `lcd.setCursor()` antes de qualquer `write`/`print`, porque o `createChar` deixa o endereço apontando para a CGRAM.
- Layout em 2×2 caracteres no centro da tela (colunas 7–8): slots 0 e 1 = cacho (linha 0), slots 2 e 3 = taça (linha 1). Cada caractere tem 5×8 px, então cada figura tem 10×8 px.
- Bitmaps:
  - `UVA[4][2][8]`: cheio → espremendo 1 → espremendo 2 → bagaço. As linhas de baixo do cacho podem mostrar a gota saindo.
  - `TACA[6][2][8]`: vazia (só contorno) → líquido nos níveis 1 a 5. A primeira linha da taça pode mostrar a gota caindo.
- Sequência (~300 ms por quadro):
  1. Uva cheia + taça vazia.
  2. Uva espremendo 1 e 2, com a gota aparecendo.
  3. Taça subindo do nível 1 ao 5, com a uva alternando entre espremendo 1 e 2.
  4. Uva bagaço + taça cheia, parado por 1 s.
- `delay()` é permitido aqui: roda no `setup()`, antes do `loop()` (mesma justificativa do `logo()` atual). A regra de não usar `delay()` vale para os padrões de alerta.
- Em `vinheria_full.ino`:
  - `logo()` passa a fazer: tela "Smart Solutions" centralizada (`setCursor(0, 0)`; 15 caracteres em 16 colunas), linha 2 vazia, 2 s → `animacaoBoot(lcd)` → "Inicializando...".
  - Em `setup()`, os 4 `lcd.createChar(...)` dos ícones normais passam para **depois** de `logo()`, para restaurar taça/gota/sol.
  - Cabeçalho do arquivo: "Vinheria Full" → "Smart Solutions — monitoramento de vinherias".
  - No bloco `CONFIGURAÇÃO DESTA INSTÂNCIA`, `BROKER_MQTT` recebe o IP elástico e o `TODO` sai.
- Fora do firmware: `CLAUDE.md` §5 (Smart Solutions e gate de design), §6 (IP elástico) e §9 (candidato a skill "subir o ambiente FIWARE e revalidar") — **já atualizado** em 05/10/2026, então o passo 8 abaixo é só conferência.

**Ferramentas e requisitos.**
- Nenhuma lib nova (`LiquidCrystal_I2C` já está em `libraries.txt`).
- IP elástico alocado e associado à EC2 pelo usuário no console AWS (EC2 → Elastic IPs → Allocate → Associate). Informar o IP antes do passo 7.
- Wokwi aberto. Lá é preciso **adicionar o arquivo `boot_animacao.h`** no projeto (botão "+" ao lado das abas). O mesmo vale para os 4 Wokwi das outras máquinas, que devem abrir o link do projeto atualizado.

**Passos.**
1. Criar `boot_animacao.h` só com o esqueleto: include guard, `#include <LiquidCrystal_I2C.h>` e `animacaoBoot()` vazia. Incluir no `.ino`. Resultado: o Wokwi compila e o boot fica igual. Commit.
2. Desenhar os bitmaps `UVA` e `TACA` (cheia/vazia e os quadros intermediários) e implementar um único quadro estático (uva cheia + taça vazia, 2 s). Resultado: as figuras aparecem no Wokwi. **O usuário aprova o desenho** antes de seguir. Commit.
3. Implementar a sequência completa de quadros. Resultado: a animação roda inteira no Wokwi e o usuário aprova o ritmo. Commit.
4. Alterar `logo()`: "Smart Solutions" centralizado, linha 2 vazia, sem "Vinheria Agn.", chamando `animacaoBoot`. Resultado: a sequência nome → animação → "Inicializando..." aparece no Wokwi. Commit.
5. Mover os `createChar` dos ícones normais para depois de `logo()` em `setup()`. Resultado: o carrossel mostra taça/gota/sol corretos após o boot. Commit.
6. Atualizar o cabeçalho do `.ino` com o nome Smart Solutions. Commit.
7. Colocar o IP elástico em `BROKER_MQTT` e remover o `TODO`. Resultado: o Serial mostra a conexão MQTT OK. Commit.
8. Conferir que o `CLAUDE.md` já reflete IP elástico e Smart Solutions (`grep -n "elástico\|Smart Solutions" CLAUDE.md`). Sem commit se nada mudar.

**Como verificar.**
- Reiniciar a simulação no Wokwi e confirmar 4 coisas:
  - (a) "Smart Solutions" centralizado por ~2 s, sem segunda linha;
  - (b) uva espremendo e taça enchendo em ~4 s, terminando cheia;
  - (c) "Inicializando...";
  - (d) o carrossel com os ícones taça/gota/sol corretos, não os bitmaps da uva.
- O Serial mostra a conexão MQTT no IP elástico sem nenhuma edição antes da sessão.
- `grep -rn "Agn" firmware/` → nenhum resultado.

### Task 2: Backend — config, DB e cliente FIWARE

> **FEITA em 07/10/2026** — executada pelo plano docs/specs/task-2-backend-config-fiware/plan.md (commits `91e19ff`..`590ff48`). 59 testes passando sem rede; verificação real na EC2: health `ok:true` nos três serviços, troca de IP em runtime sem reiniciar e `list_entities()` devolvendo `vinheria001` e `vinheria002` com `TimeInstant`. Por decisão do usuário, o cliente foi dividido em módulos por componente (`fiware_base`, `fiware_iota`, `fiware_orion`, `fiware_sth`, `fiware_constants`), com `fiware_client.py` como fachada; o `httpx` agora vive só em `fiware_base.py`.

> **Planejada em 05/10/2026 (spec-driven).** Executar por [`docs/specs/task-2-backend-config-fiware/plan.md`](docs/specs/task-2-backend-config-fiware/plan.md), que segue a [`spec.md`](docs/specs/task-2-backend-config-fiware/spec.md) da mesma pasta. Os passos abaixo são o resumo original; em caso de divergência, a spec manda. Mudanças em relação a este resumo: `register_commands` sai (o IoT Agent registra sozinho), `subscribe_attr` recebe `entity_id`, erros viram `FiwareError` traduzido por handler central, `.gitignore` é antecipado da Task 7A, e entram `delete_device`, `delete_entity`, `delete_subscriptions` e `update_attrs` (revisão 3).

**Files:** criar `backend/requirements.txt`, `.env.example`, `app/main.py`, `app/core/config.py`, `app/core/db.py`, `app/models/schemas.py`, `app/services/fiware_client.py`, `app/api/routes_config.py`, `tests/test_fiware_client.py`, `tests/test_config.py`
**Multi-vinheria:** `config` inclui `offline_seconds` (default 30); schema `devices`: `device_id TEXT PK, entity_id TEXT, name TEXT, city TEXT, created_at TEXT`; service group com `"timestamp": true`.
**Produces:** `ConfigStore.get()/update()`, `FiwareClient(base_cfg)` com `provision_service_group()`, `provision_device(device)`, `register_commands(device)`, `subscribe_attr(device, attr)`, `get_entity(entity_id)`, `list_entities(entity_type)` (`GET :1026/v2/entities?type=Vinheria&options=keyValues`, devolve `TimeInstant`), `send_command(entity_id, command)`, `query_history(entity_type, entity_id, attr, last_n=None, date_from=None, date_to=None)`, `health()`.

- [x] **Passo 1:** teste falhando — `ConfigStore` usa `FIWARE_HOST` do `.env` como `ec2_ip` quando o SQLite ainda não tem valor salvo, persiste `ec2_ip` no SQLite quando atualizado, e `FiwareClient` monta URLs `http://<ip>:1026/...`, `:4041`, `:8666` a partir do config atual (trocar o IP troca a URL sem reiniciar o app).
- [x] **Passo 2:** rodar `pytest backend/tests -v` → falha.
- [x] **Passo 3:** implementar `config.py` (Settings via `.env` + ConfigStore em SQLite), `db.py` (schema: `config`, `devices`, `triggers`, `alerts`), `schemas.py`, `fiware_client.py` (httpx, headers `fiware-service`/`fiware-servicepath`, timeouts, erros traduzidos em `HTTPException`), `routes_config.py` (GET/PUT + `/health` pingando as três portas).
- [x] **Passo 4:** `main.py` com CORS liberado para `http://localhost:5173` e inclusão dos routers; rodar `pytest` → passa; subir `uvicorn app.main:app --reload` e checar `/docs`.
- [x] **Passo 5:** commit `feat: add config store and FIWARE client layer`.

### Task 3: Backend — cadastro de devices e leitura de dados

> **FEITA em 08/10/2026** — executada pelo plano docs/specs/task-3-cadastro-historico-score/plan.md (commits `568d33d`..`149082d`). 160 testes passando sem rede. Verificação real na EC2: `vinheria001` (Vinheria Paulista, São Paulo) e `vinheria002` (Vinheria Mineira, Minas Gerais) adotadas com `set_limits`, faixa padrão no Orion e 3 subscriptions cada; `alert_off` respondido pelo Wokwi depois do upsert; histórico `{ts, value}` e score conferido à mão (16,7 para 24 °C / 40 % / 76); ciclo da `vinheria099` limpo. A primeira tentativa achou que `POST /attrs` dá 404 antes da primeira leitura, e o `update_attrs` passou a usar `POST /v2/op/update` (append).
>
> *Planejamento original:* [`docs/specs/task-3-cadastro-historico-score/plan.md`](docs/specs/task-3-cadastro-historico-score/plan.md), que segue a [`spec.md`](docs/specs/task-3-cadastro-historico-score/spec.md) da mesma pasta. Os passos abaixo são o resumo original; em caso de divergência, a spec manda. Mudanças em relação a este resumo, decididas com o usuário e com uma sonda na EC2 (IoT Agent 3.7.0):
> - `register_commands` sai do plano.
> - O cadastro **re-provisiona** o device que já existe no IoT Agent, para a 001 e a 002 ganharem `set_limits` (o IoT Agent não aceita acrescentar comandos com `PUT`).
> - As subscriptions são recriadas a cada cadastro, e a faixa padrão é publicada no Orion já no cadastro (a entidade nasce no provisionamento).
> - O score usa média proporcional e fica `null` com uma mensagem de motivo quando falta leitura.
> - Não há rollback compensatório: o FIWARE vem primeiro e o SQLite por último.

**Files:** criar `app/services/device_registry.py`, `app/services/quality_score.py`, `app/api/routes_devices.py`, `app/api/routes_data.py`, `tests/test_device_registry.py`, `tests/test_quality_score.py`
**Consumes:** `FiwareClient`, `ConfigStore`. **Produces:** `DeviceRegistry.create(device_id, name, city)/list/delete`, `resolve_vinheria(texto) -> Device` (lança `AmbiguousVinheria(options)` ou `VinheriaNotFound`), `quality_score(reading)`.

- [x] **Passo 0 (multi-vinheria):** `create_device` valida `^vinheria\d{3}$` e deriva `entity_id`; `resolve_vinheria` normaliza (sem acento, minúsculas) e casa primeiro com o id, depois com nome/cidade. Testes: cadastrar 2 devices gera 2× a sequência de provisionamento; resolver com "sao paulo", "São Paulo", "vinheria002", "vinheria" (ambíguo) e "Recife" (não encontrado).
- [x] **Passo 1:** teste falhando — `create_device` grava no SQLite e executa a sequência completa de provisionamento (service group → device → `register_commands` → `subscribe_attr` para os 3 atributos), devolvendo o device com `entity_name` derivado do id; `quality_score` devolve 100 em condição ideal (temp 12–18 °C, umid 50–70 %, luz ≤ 30 %) e penaliza proporcionalmente fora dela.
- [x] **Passo 2:** rodar os testes → falham (mock HTTP com `respx`).
- [x] **Passo 3:** implementar registry (rollback no SQLite se o provisionamento falhar), `quality_score`, rotas de device (POST/GET/DELETE), rotas de dados (`/current`, `/history` com `lastN` ou janela de datas, `/score`), normalizando a resposta do STH para `[{ "ts": iso, "value": float }]`.
- [x] **Passo 4:** testes passam; smoke real contra a EC2: cadastrar `vinheria001` e ver o Wokwi aparecer no Orion, **com `TimeInstant` atualizando a cada leitura**. Se o campo não vier, parar e voltar ao planejamento (a detecção de offline depende dele).
- [x] **Passo 5:** commit `feat: add device registry, history queries and quality score`.

### Task 4: Backend — triggers, poller e log de alertas

**Files:** criar `app/services/trigger_engine.py`, `app/services/fleet_state.py`, `app/services/alert_log.py`, `app/api/routes_triggers.py`, `app/api/routes_alerts.py`, `app/api/routes_fleet.py`, `tests/test_trigger_engine.py`, `tests/test_fleet.py`; modificar `app/main.py` (lifespan start/stop da task)
**Consumes:** `FiwareClient`, `DeviceRegistry`. **Produces:** `TriggerEngine.tick()` (uma passada, testável sem loop; faz uma chamada `list_entities` e avalia triggers e offline de cada device cadastrado), `TriggerEngine.run()` (loop asyncio), `AlertLog.open/close/list`, `FleetState.snapshot() -> list[VinheriaStatus]`, `GET /api/fleet`.

- [ ] **Passo 1:** teste falhando com leituras sintéticas — valor acima do máximo dispara exatamente um `blink_temp` e abre um alerta; segundo tick com o mesmo valor **não** reenvia comando; retorno à faixa envia `alert_off` e fecha o alerta; duas anomalias simultâneas mantêm o alerta ativo até a última normalizar. Offline: device sem atualização há mais de `offline_seconds` abre alerta `attr="offline"` e não recebe comando; ao voltar, o alerta fecha. Um device em alerta não altera o estado dos outros.
- [ ] **Passo 2:** rodar → falha.
- [ ] **Passo 3:** implementar `trigger_engine` (dict de estado por `(device_id, attr)`, histerese configurável, `tick()` puro + `run()` com `asyncio.sleep(poll_seconds)`), `alert_log`, rotas de triggers (GET/PUT por device, defaults de vinheria) e de alertas; iniciar/parar a task no lifespan do FastAPI.
- [ ] **Passo 4:** testes passam; teste manual: baixar o máximo de temperatura pelo `PUT /triggers` e ver o ESP32 piscar/apitar, depois voltar e ver parar.
- [ ] **Passo 5:** commit `feat: add trigger engine with remote alert dispatch and alert log`.

### Task 5: Front-end React — base, config de IP e devices

**Files:** criar `frontend/package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/api/client.js`, `src/context/ConfigContext.jsx`, `src/context/FleetContext.jsx`, `src/components/FiwareBar.jsx`, `AlertBanner.jsx`, `DeviceForm.jsx`, `DeviceList.jsx`, `src/pages/Devices.jsx`
**Consumes:** `/api/config`, `/api/devices`, `/api/fleet`.

> **Gate de design (vale para as Tasks 5, 6 e 7A no front):** antes de qualquer passo de front-end, o usuário envia anexos e exemplos de referência (modelo, layout, cores, tipografia, estilo). Nenhuma decisão visual é tomada antes disso. Fluxo: receber as referências → planejar o design system e os layouts em Opus (cores, fontes, componentes, telas) e registrar neste plano → só então o Sonnet implementa. Os passos abaixo definem estrutura e comportamento, não aparência.
**Rotas:** `/` Visão Geral · `/vinherias/:id` detalhe · `/alertas` · `/dispositivos` · `/chat`.

- [ ] **Passo 1:** scaffold Vite + React (JS), instalar deps, `vite.config.js` com proxy `/api` → `http://localhost:8000`.
- [ ] **Passo 2:** `client.js` — wrapper `request(path, options)` com base URL do backend (`localStorage`, default `http://localhost:8000`) e tratamento de erro padronizado.
- [ ] **Passo 3:** `ConfigContext` carrega `/api/config` no mount e expõe `config`/`saveConfig`; `FiwareBar` fixo no topo com o nome **Smart Solutions**, indicador verde/vermelho vindo de `/api/config/health` (revalida a cada 30 s) e o IP do FIWARE em um painel "Avançado" recolhido (input + Salvar). O IP já vem do `.env` (IP elástico); esse painel é o único lugar onde ele pode ser trocado. `<title>` do `index.html`: "Smart Solutions — Monitoramento de Vinherias".
- [ ] **Passo 4:** página Devices — formulário (`device_id`, nome, cidade) + lista com status e botão excluir.
- [ ] **Passo 4b:** `FleetContext` faz polling de `/api/fleet` a cada 5 s, guarda o snapshot anterior e gera eventos nas transições `ok→alerta`, `*→offline` e `offline→ok`. `AlertBanner` mostra faixa fixa enquanto houver vinheria em alerta ou offline, mais toasts empilháveis e fecháveis por evento, com link para `/vinherias/:id`.
- [ ] **Passo 5 (teste):** `npm run dev`, trocar o IP com a EC2 desligada (indicador vermelho) e ligada (verde); cadastrar e remover um device; parar um Wokwi e ver o toast de offline em até ~35 s.
- [ ] **Passo 6:** commit `feat: add React dashboard shell with runtime FIWARE IP config and device CRUD`.

### Task 6: Front-end — visão geral, gráficos dinâmicos, triggers, alertas e score

**Files:** criar `src/components/SensorChart.jsx`, `GaugeScore.jsx`, `TriggerPanel.jsx`, `AlertTimeline.jsx`, `VinheriaCard.jsx`, `src/pages/Overview.jsx`, `VinheriaDetail.jsx`, `Alerts.jsx`

- [ ] **Passo 0:** `Overview` + `VinheriaCard` — grid de cards com nome, cidade, cor do status (verde/vermelho/cinza), valores atuais, score e "visto há Ns", alimentados por `FleetContext`; clicar abre `/vinherias/:id`.

- [ ] **Passo 1:** `SensorChart` — `react-chartjs-2` Line, props `deviceId`/`attr`/`lastN`, auto-refresh a cada 10 s, seletor de janela (lastN 20/50/100 ou dateFrom–dateTo), linhas tracejadas nos limites do trigger.
- [ ] **Passo 2:** `VinheriaDetail` (rota `/vinherias/:id`) — três cards (temperatura, umidade, luminosidade) com valor atual + gráfico, `GaugeScore` com o score e semáforo, badge de alerta ativo, `TriggerPanel` e timeline da vinheria.
- [ ] **Passo 3:** `TriggerPanel` — min/max para os três atributos com validação (min < max), salvando em `PUT /api/devices/{id}/triggers`; feedback de sucesso.
- [ ] **Passo 4:** `AlertTimeline` — lista de `/api/alerts` com tipo (incluindo `offline`), valor, início, fim e duração; página `/alertas` com a timeline global e filtro por vinheria.
- [ ] **Passo 5 (teste):** com 2 ou mais Wokwi rodando, apertar o LDR/temperatura em um deles e ver só o card, o gráfico, o badge, a timeline e o ESP32 daquela vinheria reagirem, enquanto as outras seguem verdes.
- [ ] **Passo 6:** commit `feat: add dynamic charts, trigger tuning, score gauge and alert timeline`.

### Task 7A: Chatbot Gemini multi-vinheria

> **Sai do adiamento (revisão de 05/10/2026).** Vem logo depois da Task 6, pois precisa de `/api/fleet`, do resolver e dos dados do STH prontos. Entram aqui também `.gitignore` (ignorando `.env`, `__pycache__/`, `node_modules/`, `*.db`) e `backend/.env.example` com `GEMINI_API_KEY=` vazio. A chave real só no `.env` local, nunca commitada.

**Files:** criar `app/services/chatbot.py`, `app/api/routes_chat.py`, `src/components/ChatBox.jsx`, `src/pages/Chat.jsx`, `tests/test_chatbot_tools.py`
**Consumes:** `DeviceRegistry.resolve_vinheria`, `FleetState`, `alert_log`, `quality_score`, `FiwareClient.query_history`. **Produces:** `ask(message, history) -> str`, `POST /api/chat`.

- [ ] **Passo 1:** teste falhando nas **tools** (funções puras, sem chamar a API), com dados sintéticos via pandas. O parâmetro `vinheria` é texto livre (id, nome ou cidade), resolvido por `resolve_vinheria`; se ambíguo, a tool devolve erro listando as opções.
  - `listar_vinherias()` → id, nome, cidade, status
  - `estado_atual(vinheria)`
  - `estatisticas(vinheria, atributo, horas=1)` → média, mín, máx, desvio, n e `tendencia` ∈ {estável, subindo, caindo}. É "estável" se a amplitude (máx−mín) for < 1,0 °C (temperatura), 3 % (umidade) ou 5 % (luminosidade); senão o sinal da inclinação decide.
  - `comparar(atributo, horas=1)` → média por vinheria ("qual está mais quente?")
  - `alertas(vinheria=None, horas=24)`
  - `limites(vinheria)`
- [ ] **Passo 2:** rodar → falha; implementar as tools e fazer passar.
- [ ] **Passo 3:** `chatbot.py` — `google.genai` com declaração das tools, loop de function calling (máx. 5 iterações). System instruction: responder em português, só com dados das tools, citar números e unidades, recomendar ação de vinheria quando houver anomalia. A cada pergunta, injetar no prompt um resumo do status da frota para o bot avisar sozinho de vinherias em alerta ou offline.
- [ ] **Passo 4:** `routes_chat.py` — `POST /api/chat { message, history[] }`, sem `device_id`.
- [ ] **Passo 5:** `ChatBox` — histórico de mensagens, textarea, estado de carregando, chips ("Como está a vinheria de São Paulo?", "Alguma vinheria em alerta?", "Qual vinheria está mais úmida agora?").
- [ ] **Passo 6 (teste):** com 2 ou mais vinherias com dados reais no STH, perguntar as três chips e conferir que os números batem com o gráfico do detalhe; parar um Wokwi e confirmar que o bot cita a vinheria offline.
- [ ] **Passo 7:** commit `feat: add multi-vinheria Gemini chatbot with data tools`.

### Task 7B: Relatórios CSV/PDF

> **Primeiro corte se o prazo apertar.** Fazer depois da Task 7A.

**Files:** criar `app/services/report.py`, `app/api/routes_report.py`; modificar `src/pages/VinheriaDetail.jsx`
**Consumes:** `routes_data`/`alert_log`/`quality_score`.

- [ ] **Passo 1:** `report.py` — CSV via pandas e PDF via matplotlib + reportlab (gráfico dos três atributos, estatísticas e alertas do período), por vinheria.
- [ ] **Passo 2:** `routes_report` devolve `StreamingResponse` com `Content-Disposition`; botão de exportar CSV/PDF em `VinheriaDetail` (a vinheria vem da rota).
- [ ] **Passo 3 (teste):** baixar CSV e PDF de duas vinherias diferentes e conferir que cada arquivo traz só os dados da sua vinheria.
- [ ] **Passo 4:** commit `feat: add CSV and PDF reports per vinheria`.

### Task opcional: atribuição automática do id ao dispositivo

> **Registrada em 07/10/2026, a pedido do usuário. Só depois que a demo central (Tasks 4 a 6) funcionar.** Precisa de planejamento próprio em Opus antes de qualquer código.

**Ideia.** O operador não precisa mais editar o `ID_DEVICE` no firmware.
1. O ESP32 sem id salvo na flash (`Preferences`) entra em "aguardando cadastro" e mostra no LCD um código curto (ex.: `K7Q2`).
2. O operador cadastra a vinheria no painel informando esse código.
3. O backend manda o id pelo comando `assign` (valor `"K7Q2;vinheria003"`) de um device fixo `bootstrap`, provisionado no IoT Agent. Todos os ESP32 sem id escutam o tópico dele.
4. Só o ESP32 com o código certo grava o id, refaz os tópicos e passa a publicar como `vinheria003`.

**Primeiro passo:** rodar duas abas do Wokwi com `Serial.println(WiFi.macAddress())`, para saber se o MAC é diferente em cada uma. Se não for, o código precisa ser aleatório.

**Limitação conhecida:** o Wokwi não guarda a flash entre execuções, então o id precisaria ser reatribuído a cada reinício da simulação. No ESP32 físico funciona normalmente.

**Escopo estimado:** 1 a 1,5 dia, cobrindo firmware, backend (device `bootstrap` e ação de atribuir no `DeviceRegistry`) e front.

### Task 8: Manuais, Postman e fechamento da entrega

**Files:** criar `docs/manual-hardware.md`, `docs/manual-software.md`, `postman/CP5-Vinheria.postman_collection.json`; modificar `README.md`, `PRD.md`

- [ ] **Passo 1:** `manual-hardware.md` — lista de materiais, tabela de pinagem (DHT-11 GPIO 4, LDR GPIO 34, buzzer GPIO 5, LED azul GPIO 2), esquema de montagem, cuidados (resistor de pull-up do DHT, divisor do LDR) e diferenças DHT-11 vs DHT-22.
- [ ] **Passo 2:** `manual-software.md` — subir a EC2, `docker-compose up -d` do `fabiocabrini/fiware`, portas no Security Group (1026, 4041, 8666, 1883), provisionamento via Postman, instalar/rodar backend (`pip install -r requirements.txt`, `.env`, `uvicorn`) e front (`npm install`, `npm run dev`), **alocar e associar o IP elástico à EC2** (e o que fazer se precisar trocá-lo: `.env`, bloco do firmware, variável `{{url}}` do Postman, painel Avançado do site) e troubleshooting. Incluir a seção **"Rodar uma vinheria Wokwi em outro computador"**: abrir o link do Wokwi, editar o bloco `CONFIGURAÇÃO DESTA INSTÂNCIA` (`ID_DEVICE`, `BROKER_MQTT`), Start e cadastrar a vinheria no site (`device_id`, nome, cidade).
- [ ] **Passo 3:** criar `postman/CP5-Vinheria.postman_collection.json` a partir da collection base do professor: variável `{{url}}` mantida, entidade `urn:ngsi-ld:Vinheria:001`/type `Vinheria` (variáveis para trocar o `00N` e provisionar as outras vinherias), os 4 comandos no provisionamento e na registration, e as 3 subscriptions (temperature, humidity, luminosity) — remover os requests de Lamp que não se aplicam.
- [ ] **Passo 4:** finalizar `README.md` (arquitetura em camadas, links do Wokwi e do vídeo, prints do dashboard) e revisar o `PRD.md` contra o que foi construído.
- [ ] **Passo 5:** roteiro do pitch/vídeo em `docs/` (problema → arquitetura → demo ao vivo com as 5 vinherias, alerta e offline → chatbot → diferenciais → encerramento), 5–7 min. Ensaiar com as 5 instâncias (1 física + 4 Wokwi).
- [ ] **Passo 6:** commit `docs: add hardware/software manuals, Postman collection and final README`.

---

## Verificação end-to-end (ensaio do hands-on)

1. EC2 ligada; `docker ps` mostra orion, iot-agent, sth-comet, mosquitto, mongo.
2. Backend recém-iniciado, sem digitar IP: `GET /api/config/health` usa o IP elástico do `.env` → três portas OK.
3. 5 instâncias ligadas (1 física + 4 Wokwi, `vinheria001` a `vinheria005`) e cadastradas; a Visão Geral mostra 5 cards verdes. `GET /api/devices/vinheria001/current` retorna `t`, `h`, `l`.
4. `GET /api/devices/vinheria001/history?attr=t&lastN=20` retorna série do STH e o gráfico desenha.
5. Pelo front, baixar o máximo de temperatura **só da vinheria002** → apenas o LED/buzzer dela reage (LED azul a 500 ms + 2 bipes curtos); banner aparece e os outros cards seguem verdes. Subir o limite de novo → para. Repetir para umidade (bipe longo) e luminosidade (3 bipes rápidos).
6. Parar um Wokwi → em até ~35 s o card fica cinza "offline", aparece o toast e a timeline registra `offline`. Religar → volta para ok e o alerta fecha.
7. Timeline de alertas mostra os eventos com início, fim e duração, filtráveis por vinheria.
8. Chat: "Como está a temperatura da vinheria de São Paulo?" → resposta com média, unidade e tendência, números conferem com o gráfico. "Alguma vinheria com problema?" → cita a vinheria em alerta ou offline.
9. Exportar CSV e PDF do período de uma vinheria (Task 7B, se entrar).
10. `pytest backend/tests -v` tudo verde.
