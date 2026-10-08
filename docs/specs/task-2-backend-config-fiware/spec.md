# Spec — Task 2: Backend com configuração, banco e cliente FIWARE

> Método spec-driven: esta spec diz **o que** a Task 2 entrega e **como saber que está certo**. O passo a passo de execução fica em [`plan.md`](plan.md), que segue esta spec item por item. Se as duas divergirem, a spec manda e o executor para e devolve para planejamento.
>
> Fonte: Task 2 de [`PLANO-CP5-VINHERIA.md`](../../../PLANO-CP5-VINHERIA.md), revisões 1 a 3. Formato do `CLAUDE.md` §3: Contexto → Objetivo → Detalhes técnicos → Ferramentas e requisitos → Passos (no plano) → Como verificar.

---

## 1. Contexto

**Por que existe.** É a fundação do backend. Todas as tasks seguintes de backend (cadastro de vinherias, triggers, frota, chatbot e relatórios) precisam de três coisas: saber onde o FIWARE está, guardar dados localmente e falar HTTP com o FIWARE. Pelo `CLAUDE.md` §6, só um módulo pode falar HTTP com o FIWARE, e este é o momento de criá-lo.

**O que já está pronto.**
- Firmware (Task 1 e 1B): `vinheria001` e `vinheria002` publicam no FIWARE da EC2 pelo IP elástico.
- FIWARE na EC2 validado com o Postman (`postman/CP5-Vinheria.postman_collection.json`): service group, provisionamento, subscriptions para o STH-Comet e comandos.
- Documentação base (Task 0): `PRD.md`, `README.md`, `docs/arquitetura.md`.
- Ainda não existe a pasta `backend/`.

**O que depende desta task.**
- Task 3 usa `ConfigStore`, `FiwareClient.provision_service_group`, `provision_device`, `subscribe_attr`, `delete_device`, `delete_entity`, `delete_subscriptions`, `get_entity` e `query_history`.
- Task 4 usa `list_entities`, `send_command` e `update_attrs`, mais a tabela `alerts` e `triggers`.
- Task 5 (front) usa `GET/PUT /api/config` e `GET /api/config/health`.

## 2. Objetivo

Com o backend rodando (`uvicorn app.main:app --reload`) e a EC2 ligada, `GET /api/config/health` responde `ok: true` para Orion, IoT Agent e STH-Comet usando o IP do `.env`; depois de `PUT /api/config` com outro IP, a próxima chamada já usa o IP novo, sem reiniciar; e `pytest tests -v` passa inteiro sem acesso à rede.

## 3. Requisitos e critérios de aceite

Formato: **QUANDO** <situação>, o backend **DEVE** <comportamento>. Cada requisito aponta os testes que o provam (nomes no `plan.md`).

### R1 — Configuração inicial vem do `.env`
- **R1.1** QUANDO o backend inicia, DEVE ler do `.env` (ou do ambiente) `FIWARE_HOST`, portas, headers FIWARE, URL interna do STH, intervalos, timeout, caminho do banco e origens do CORS, usando os defaults da seção 4.2 para o que faltar.
  Testes: `test_load_settings_le_variaveis_de_ambiente`, `test_load_settings_usa_defaults`.
- **R1.2** QUANDO `FIWARE_HOST` vem com espaços, esquema (`http://`), barra, caminho ou porta, DEVE guardar só o host (`" http://3.3.3.3:1026/ "` → `"3.3.3.3"`).
  Teste: `test_load_settings_normaliza_host`.
- **R1.3** QUANDO `FIWARE_HOST` está vazio ou ausente, o backend DEVE subir mesmo assim, com `ec2_ip = ""`.
  Testes: `test_load_settings_usa_defaults`, `test_get_config_sem_ip`.

### R2 — Configuração de runtime trocável e persistida
- **R2.1** QUANDO o SQLite não tem valor salvo, `ConfigStore.get()` DEVE devolver os valores do `.env`.
  Teste: `test_config_store_usa_env_quando_banco_vazio`.
- **R2.2** QUANDO a config é atualizada, DEVE gravar só os campos enviados e manter os demais.
  Teste: `test_config_store_update_parcial`.
- **R2.3** QUANDO o backend reinicia, DEVE manter a config salva, que prevalece sobre o `.env`.
  Teste: `test_config_store_persiste_entre_conexoes`.
- **R2.4** QUANDO a atualização traz IP vazio (depois de normalizado), porta fora de 1–65535, `poll_seconds` fora de 1–300 ou `offline_seconds` fora de 5–3600, DEVE rejeitar sem gravar nada (HTTP 422 na API).
  Testes: `test_config_update_rejeita_ip_vazio`, `test_config_update_rejeita_valores_fora_da_faixa`, `test_put_config_invalido_devolve_422`.

### R3 — Banco local
- **R3.1** QUANDO o banco é aberto, DEVE criar (se não existirem) as tabelas `config`, `devices`, `triggers` e `alerts` com o schema da seção 4.4.
  Teste: `test_connect_cria_tabelas`.

### R4 — URLs montadas a partir da config atual
- **R4.1** O cliente FIWARE DEVE montar as URLs como `http://<ec2_ip>:<porta>` lendo a config **a cada chamada**; trocar o IP ou a porta muda a próxima URL sem recriar o cliente.
  Teste: `test_urls_usam_config_atual`.
- **R4.2** QUANDO não há IP configurado, qualquer chamada ao FIWARE DEVE falhar com `FiwareUnavailable` e mensagem que explica como configurar, sem tentar a rede.
  Teste: `test_sem_ip_configurado_levanta_unavailable`.

### R5 — Requisições e erros padronizados
- **R5.1** Toda requisição ao FIWARE DEVE levar `fiware-service: smart` e `fiware-servicepath: /` (valores vindos de Settings).
  Teste: `test_requests_levam_headers_fiware`.
- **R5.2** QUANDO o FIWARE não responde (timeout, conexão recusada, IP errado), DEVE levantar `FiwareUnavailable`; 404 vira `FiwareNotFound`; 409 vira `FiwareConflict`; outro status de erro vira `FiwareError` com o código.
  Testes: `test_timeout_vira_unavailable`, `test_conexao_recusada_vira_unavailable`, `test_status_500_vira_fiware_error`, `test_get_entity_inexistente_levanta_not_found`, `test_provision_device_duplicado_levanta_conflict`.
- **R5.3** QUANDO um `FiwareError` chega até uma rota, a API DEVE responder JSON `{ "detail", "service" }` com status 503 (indisponível), 404, 409 ou 502 (demais), nunca 500.
  Teste: `test_handler_traduz_erros_fiware`.

### R6 — IoT Agent
- **R6.1** `provision_service_group()` DEVE enviar o service group com `apikey TEF`, `cbroker` apontando para o Orion na config atual, `entity_type Thing`, `resource ""` e `timestamp: true`; 409 (já existe) conta como sucesso.
  Testes: `test_provision_service_group_envia_body`, `test_provision_service_group_aceita_409`.
- **R6.2** `provision_device(device)` DEVE enviar o device com `entity_type Vinheria`, protocolo `PDI-IoTA-UltraLight`, transporte `MQTT`, os 3 atributos (`t`→`temperature` Float, `h`→`humidity` Float, `l`→`luminosity` Integer) e os 5 comandos (`blink_temp`, `blink_hum`, `blink_lux`, `alert_off`, `set_limits`).
  Teste: `test_provision_device_envia_body`.
- **R6.3** `delete_device(device_id)` DEVE remover o device; 404 conta como sucesso (remoção idempotente).
  Teste: `test_delete_device_aceita_404`.

### R7 — Orion
- **R7.1** `subscribe_attr(entity_id, attr)` DEVE criar a subscription do atributo longo para `<STH_INTERNAL_URL>/notify` com `attrsFormat: legacy` e devolver o id da subscription (lido do header `Location`). Atributo fora de `temperature|humidity|luminosity` DEVE dar `ValueError` sem chamar a rede.
  Testes: `test_subscribe_attr_envia_body_e_devolve_id`, `test_subscribe_attr_rejeita_atributo_invalido`.
- **R7.2** `get_entity(entity_id)` DEVE devolver a entidade em `keyValues`.
  Teste: `test_get_entity_usa_key_values`.
- **R7.3** `list_entities("Vinheria")` DEVE fazer **uma** chamada `GET /v2/entities?type=Vinheria&options=keyValues&limit=1000` e devolver a lista (com `TimeInstant` quando o Orion manda).
  Teste: `test_list_entities_uma_chamada`.
- **R7.4** `send_command(entity_id, command, value="")` DEVE fazer `PATCH /v2/entities/<id>/attrs` com `{ command: { type: "command", value } }`. Comando fora da lista canônica DEVE dar `ValueError` sem chamar a rede.
  Testes: `test_send_command_envia_patch`, `test_send_command_set_limits_com_valor`, `test_send_command_rejeita_comando_invalido`.
- **R7.5** `update_attrs(entity_id, attrs)` DEVE fazer `POST /v2/entities/<id>/attrs` (cria ou atualiza) com cada valor como `{ type: "Number", value }`.
  > **Emenda de 07/10/2026 (Task 3, fato F4):** na EC2, esse `POST` responde 404 antes da primeira leitura do device. O `update_attrs` passa a usar `POST /v2/op/update` com `actionType: append` e o teste vira `test_update_attrs_usa_op_update_append` (subtarefa 3.7a do plano da Task 3).
  Teste: `test_update_attrs_envia_post`.
- **R7.6** `delete_entity(entity_id)` DEVE remover a entidade; 404 conta como sucesso.
  Teste: `test_delete_entity_aceita_404`.
- **R7.7** `delete_subscriptions(entity_id)` DEVE apagar só as subscriptions cuja `subject.entities` contém aquela entidade e devolver quantas apagou.
  Teste: `test_delete_subscriptions_apaga_so_as_da_entidade`.

### R8 — STH-Comet
- **R8.1** `query_history(entity_type, entity_id, attr, last_n=...)` DEVE consultar `GET /STH/v1/contextEntities/type/<type>/id/<id>/attributes/<attr>?lastN=<n>` e devolver a lista crua `values` (`[{ recvTime, attrValue }, ...]`).
  Teste: `test_query_history_last_n`.
- **R8.2** Com `date_from`/`date_to`, DEVE mandar `dateFrom`, `dateTo`, `hLimit=500` e `hOffset=0`.
  Teste: `test_query_history_por_datas`.
- **R8.3** Sem `last_n` nem datas, ou com os dois modos juntos, DEVE dar `ValueError` sem chamar a rede.
  Testes: `test_query_history_sem_janela_falha`, `test_query_history_dois_modos_falha`.
- **R8.4** QUANDO o STH não tem dados para o atributo, DEVE devolver `[]`.
  Teste: `test_query_history_sem_dados_devolve_lista_vazia`.

### R9 — Saúde do FIWARE
- **R9.1** `health()` DEVE testar em paralelo Orion (`/version`), IoT Agent (`/iot/about`) e STH (`/version`) e devolver, por serviço, `ok`, `status_code`, `latency_ms` e `error`, mais `ok` geral e o `ec2_ip` usado. **Nunca levanta exceção.**
  Testes: `test_health_tudo_ok`, `test_health_um_servico_fora`.
- **R9.2** Sem IP configurado, DEVE devolver os três serviços com `ok: false` e a mensagem de configuração, sem chamar a rede.
  Teste: `test_health_sem_ip`.

### R10 — API de configuração
- **R10.1** `GET /api/config` DEVE devolver `{ ec2_ip, orion_port, iota_port, sth_port, poll_seconds, offline_seconds }`.
  Testes: `test_get_config`, `test_get_config_sem_ip`.
- **R10.2** `PUT /api/config` DEVE aceitar qualquer subconjunto desses campos, normalizar o IP e devolver a config completa já atualizada.
  Teste: `test_put_config_atualiza_e_normaliza`.
- **R10.3** `GET /api/config/health` DEVE devolver o relatório da R9.
  Teste: `test_get_health`.
- **R10.4** O CORS DEVE liberar `http://localhost:5173` (configurável por `CORS_ORIGINS`).
  Teste: `test_cors_libera_front`.
- **R10.5** O Swagger DEVE abrir em `http://localhost:8000/docs`.
  Verificação manual no passo final do plano.

## 4. Detalhes técnicos (design)

### 4.1 Estrutura de arquivos

```
.gitignore                         # novo, na raiz (antecipado da Task 7A: o .env nasce nesta task)
backend/
├── requirements.txt
├── .env.example
├── pytest.ini
├── app/
│   ├── __init__.py
│   ├── main.py                    # create_app(): CORS, handlers, routers, lifespan; app = create_app()
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings, load_settings(), ConfigStore
│   │   └── db.py                  # connect(): SQLite + schema
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # normalize_host, RuntimeConfig, ConfigUpdate, Device, ServiceHealth, HealthReport
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fiware_errors.py       # FiwareError e subclasses
│   │   └── fiware_client.py       # FiwareClient: única porta HTTP para o FIWARE
│   └── api/
│       ├── __init__.py
│       ├── deps.py                # dependências FastAPI (store e cliente vindos de app.state)
│       ├── errors.py              # register_error_handlers(app)
│       └── routes_config.py       # GET/PUT /api/config, GET /api/config/health
└── tests/
    ├── __init__.py
    ├── conftest.py                # fixtures: settings, conn, store, fiware, anyio_backend
    ├── test_config.py             # R1, R2, R3
    ├── test_fiware_client.py      # R4, R5, R7.2, R7.3, R9 (leituras do Orion entram junto com a base)
    ├── test_fiware_iota.py        # R6
    ├── test_fiware_orion.py       # R7.1, R7.4 a R7.7
    ├── test_fiware_sth.py         # R8
    └── test_routes_config.py      # R5.3, R10
```

### 4.2 Variáveis de ambiente (`backend/.env.example`)

| Variável | Default | Uso |
|---|---|---|
| `FIWARE_HOST` | vazio | IP elástico da EC2 |
| `ORION_PORT` | `1026` | |
| `IOTA_PORT` | `4041` | |
| `STH_PORT` | `8666` | |
| `FIWARE_SERVICE` | `smart` | header `fiware-service` |
| `FIWARE_SERVICEPATH` | `/` | header `fiware-servicepath` |
| `FIWARE_APIKEY` | `TEF` | service group |
| `STH_INTERNAL_URL` | `http://sth-comet:8666` | destino das subscriptions (hostname da rede Docker, como na collection validada) |
| `POLL_SECONDS` | `5` | intervalo do poller (Task 4) |
| `OFFLINE_SECONDS` | `30` | limite de offline (Task 4) |
| `HTTP_TIMEOUT_SECONDS` | `5` | timeout de cada chamada ao FIWARE |
| `DATABASE_PATH` | `vinheria.db` | arquivo SQLite, relativo à pasta `backend/` |
| `CORS_ORIGINS` | `http://localhost:5173` | lista separada por vírgula |

`GEMINI_API_KEY` e `GEMINI_MODEL` entram no `.env.example` na Task 7A.

### 4.3 Contratos públicos (o que as próximas tasks importam)

```python
# app/models/schemas.py
def normalize_host(value: str) -> str
class RuntimeConfig(BaseModel):   # ec2_ip, orion_port, iota_port, sth_port, poll_seconds, offline_seconds
class ConfigUpdate(BaseModel):    # mesmos campos, todos opcionais e validados
class Device(BaseModel):          # device_id (^vinheria\d{3}$), entity_id, name, city
class ServiceHealth(BaseModel):   # ok, status_code, latency_ms, error
class HealthReport(BaseModel):    # ok, ec2_ip, orion, iota, sth

# app/core/config.py
@dataclass(frozen=True) class Settings
def load_settings(env_file: str | None = ".env") -> Settings
class ConfigStore:
    def __init__(self, conn: sqlite3.Connection, settings: Settings)
    def get(self) -> RuntimeConfig
    def update(self, changes: ConfigUpdate) -> RuntimeConfig

# app/core/db.py
def connect(path: str) -> sqlite3.Connection

# app/services/fiware_errors.py
class FiwareError(Exception):        # .service, .message, .status_code
class FiwareUnavailable(FiwareError)
class FiwareNotFound(FiwareError)
class FiwareConflict(FiwareError)

# app/services/fiware_client.py
SENSOR_ATTRS: tuple[tuple[str, str, str], ...]   # (object_id, nome longo, tipo)
COMMANDS: tuple[str, ...]
class FiwareClient:
    def __init__(self, config_store: ConfigStore, settings: Settings, http: httpx.AsyncClient | None = None)
    async def aclose(self) -> None
    def orion_url(self, path: str) -> str
    def iota_url(self, path: str) -> str
    def sth_url(self, path: str) -> str
    async def provision_service_group(self) -> None
    async def provision_device(self, device: Device) -> None
    async def delete_device(self, device_id: str) -> None
    async def subscribe_attr(self, entity_id: str, attr: str) -> str
    async def get_entity(self, entity_id: str) -> dict
    async def list_entities(self, entity_type: str = "Vinheria") -> list[dict]
    async def send_command(self, entity_id: str, command: str, value: str = "") -> None
    async def update_attrs(self, entity_id: str, attrs: dict[str, float]) -> None
    async def delete_entity(self, entity_id: str) -> None
    async def delete_subscriptions(self, entity_id: str) -> int
    async def query_history(self, entity_type: str, entity_id: str, attr: str,
                            last_n: int | None = None,
                            date_from: str | None = None, date_to: str | None = None) -> list[dict]
    async def health(self) -> HealthReport

# app/main.py
def create_app(settings: Settings | None = None) -> FastAPI
app = create_app()
```

### 4.4 Schema SQLite

```sql
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL              -- valor em JSON
);
CREATE TABLE IF NOT EXISTS devices (
    device_id  TEXT PRIMARY KEY,     -- vinheria00N
    entity_id  TEXT NOT NULL,        -- urn:ngsi-ld:Vinheria:00N
    name       TEXT NOT NULL,
    city       TEXT NOT NULL,
    created_at TEXT NOT NULL         -- ISO 8601 UTC
);
CREATE TABLE IF NOT EXISTS triggers (
    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    attr      TEXT NOT NULL,         -- temperature | humidity | luminosity
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    PRIMARY KEY (device_id, attr)
);
CREATE TABLE IF NOT EXISTS alerts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,         -- sem FK: o histórico sobrevive à remoção da vinheria
    attr      TEXT NOT NULL,         -- temperature | humidity | luminosity | offline
    value     REAL,
    opened_at TEXT NOT NULL,
    closed_at TEXT
);
```

### 4.5 Decisões de design desta spec

| # | Decisão | Motivo |
|---|---|---|
| D1 | Cliente **assíncrono** (`httpx.AsyncClient`). Testes assíncronos com o plugin `anyio` do pytest (já vem com o `anyio`, dependência do httpx), sem dependência nova. | O poller da Task 4 roda em `asyncio`, e o `health()` precisa testar os 3 serviços em paralelo para não somar 3 timeouts. |
| D2 | **`register_commands` sai do escopo.** | Achado do Passo 6b da Task 1, confirmado na collection validada: o IoT Agent cria a registration sozinho, e uma manual duplica e quebra o encaminhamento com 404. |
| D3 | `subscribe_attr` recebe `entity_id` (não o objeto `Device`). | A subscription só precisa do id; simplifica testes e uso. |
| D4 | Serviços levantam `FiwareError`; um handler central em `api/errors.py` traduz para HTTP. O plano original dizia "erros traduzidos em `HTTPException`" dentro do cliente. | Mantém o cliente independente do FastAPI (o poller da Task 4 também usa o cliente e não tem requisição HTTP). |
| D5 | Subscriptions notificam `STH_INTERNAL_URL` (`http://sth-comet:8666`), não o IP público. | É a forma validada na collection; a notificação sai de dentro da rede Docker. |
| D6 | Atributos `*_min`/`*_max` gravados com `POST /v2/entities/<id>/attrs` (upsert). | Um `PATCH` falha se o atributo ainda não existe. A confirmação contra a EC2 fica para a Task 4, como diz a revisão 3. |
| D7 | `.gitignore` criado nesta task (o plano o colocava na 7A). | O `.env` com o IP passa a existir aqui; ele não pode ir para o Git nem por acidente. |
| D8 | `requirements.txt` só com as dependências usadas até aqui; pandas, matplotlib, reportlab e google-genai entram nas tasks que os usam. | Evita instalar pacotes pesados sem uso; cada task adiciona o que precisa. |
| D9 | `normalize_host` não aceita IPv6 (tira tudo depois do primeiro `:`). | A EC2 usa IPv4 elástico. |

### 4.6 Fora de escopo

- Cadastro, listagem e remoção de vinherias pela API (Task 3).
- Normalização do histórico para `[{ ts, value }]` (Task 3).
- Poller, triggers, alertas e frota (Task 4).
- Qualquer chamada que altere o FIWARE real nesta task: o smoke contra a EC2 só usa leitura (`health`, `list_entities`).

## 5. Ferramentas e requisitos

- **Python 3.12** (instalado como `py -3.12`; o 3.14 da máquina também funciona, mas o 3.12 tem wheels garantidas para tudo). Ambiente virtual em `backend/.venv`.
- Dependências fixadas (versões estáveis em 05/10/2026): `fastapi==0.142.2`, `uvicorn[standard]==0.54.0`, `httpx==0.28.1`, `pydantic==2.13.5`, `python-dotenv==1.2.4`, `pytest==9.1.1`, `respx==0.23.1`.
- Para os testes: nada além disso. Sem rede.
- Para o smoke final: **EC2 ligada** com os containers `orion`, `iot-agent`, `sth-comet`, `mosquitto` e `mongo` de pé; IP elástico no `backend/.env` (`FIWARE_HOST`). Wokwi aberto é opcional (deixa o `list_entities` com `TimeInstant` recente).

## 6. Como verificar (aceite da task)

1. `cd backend && .venv/Scripts/python -m pytest tests -v` → 59 testes passam, sem acesso à rede.
2. `uvicorn app.main:app --reload` sobe sem erro; `http://localhost:8000/docs` mostra `GET /api/config`, `PUT /api/config` e `GET /api/config/health`.
3. Com a EC2 ligada: `curl http://localhost:8000/api/config/health` → `"ok": true` e os três serviços com `"ok": true`.
4. `curl -X PUT http://localhost:8000/api/config -H "Content-Type: application/json" -d "{\"ec2_ip\": \"10.255.255.1\"}"` e em seguida o health → `"ok": false` com erro de conexão em até ~5 s, **sem reiniciar**. Voltar o IP elástico pelo mesmo `PUT` → `"ok": true` de novo.
5. Smoke de leitura: `list_entities()` contra a EC2 devolve `urn:ngsi-ld:Vinheria:001` (e `002`, se provisionada) com `TimeInstant`.
6. `git status` não mostra `backend/.env` nem `*.db`.
