# Spec — Task 3: Cadastro de vinherias, histórico e score

> Método spec-driven: esta spec diz **o que** a Task 3 entrega e **como saber que está certo**. O passo a passo de execução fica em [`plan.md`](plan.md), que segue esta spec item por item. Se as duas divergirem, a spec manda e o executor para e devolve para planejamento.
>
> Fonte: Task 3 de [`PLANO-CP5-VINHERIA.md`](../../../PLANO-CP5-VINHERIA.md), PRD (RF01, RF02, RF04, RF05, RF11, RF15) e as decisões tomadas com o usuário em 07/10/2026. Formato do `CLAUDE.md` §3: Contexto → Objetivo → Detalhes técnicos → Ferramentas e requisitos → Passos (no plano) → Como verificar.

---

## 1. Contexto

**Por que existe.** A Task 2 entregou a infraestrutura: configuração, SQLite com as tabelas `devices`, `triggers` e `alerts` (ainda vazias) e o `FiwareClient`, a única porta HTTP para o FIWARE. Falta a primeira camada de negócio: saber quais vinherias existem, colocá-las no FIWARE, tirá-las de lá e ler o que elas medem. Sem isso, o motor de alertas, o painel e o chatbot não têm sobre o que trabalhar.

**O que já está pronto.**
- Backend da Task 2 (commits `91e19ff`..`5254c65`): `ConfigStore`, `connect()`, `FiwareClient` dividido em `fiware_base`, `fiware_iota`, `fiware_orion`, `fiware_sth` e `fiware_constants`, API `/api/config`, 63 testes passando.
- `vinheria001` e `vinheria002` existem no FIWARE, provisionadas à mão na Task 1, mas **não** estão no SQLite e foram provisionadas **sem** o comando `set_limits`.
- Firmware publicando `t|h|l` a cada 2 s. O `ID_DEVICE` é escrito à mão em cada firmware.

**Fatos verificados na EC2 em 07/10/2026** (IoT Agent 3.7.0, `iotagent-node-lib` 4.7.0, sonda com `vinheria099` descartável, já removida):
- F1 (**corrigido em 07/10/2026, ver F4**): logo após o `POST /iot/devices`, o `GET` da entidade responde 200, só com os atributos de comando. Isso **não** significa que a entidade está armazenada no Orion: o `GET` é atendido pela registration do IoT Agent. `temperature`, `humidity` e `luminosity` só aparecem na primeira leitura.
- F2: o `DELETE /iot/devices/{id}` **apaga também a entidade e a registration no Orion**. As subscriptions não são apagadas.
- F3: o `PUT /iot/devices/{id}` para acrescentar comandos **falha** (`404 ENTITY_GENERIC_ERROR`). Para um device ganhar `set_limits`, é preciso removê-lo e provisioná-lo de novo.
- F4 (primeira tentativa da 3.8, `vinheria077` descartável, já removida): antes da primeira leitura, `POST /v2/entities/{id}/attrs` responde **404** (3 de 3 rodadas, com e sem `?type=`). `POST /v2/op/update` com `actionType: append` responde **204**, cria a entidade, mantém os atributos de comando e aceita repetição.
- F5 (risco, **não verificado**): com o ESP32 ligado, uma leitura pode chegar entre a remoção e o provisionamento do device. Se o service group autoprovisiona (provável padrão do IoT Agent), o device é recriado sozinho e o `POST /iot/devices` responde 409.

**O que depende desta task.**
- Task 4: `DeviceRegistry.list/get`, `LimitsStore` (ganha `update`), `ReadingsService`, `quality_score`, e a faixa já publicada no Orion.
- Tasks 5 e 6 (front): as rotas `/api/devices` e `/api/devices/{id}/current|history|score`.
- Task 7A (chatbot): `resolve_vinheria`, `ReadingsService`, `quality_score`.

## 2. Objetivo

Com o backend rodando e a EC2 ligada, `POST /api/devices` com `vinheria001`, nome e cidade deixa a vinheria provisionada de ponta a ponta. Isso significa o device com os 5 comandos (incluindo `set_limits`), 3 subscriptions para o STH e a faixa padrão publicada no Orion. Com o Wokwi rodando, `GET /api/devices/vinheria001/current`, `/history?attr=temperature&last_n=20` e `/score` devolvem dados reais. `DELETE` de uma vinheria remove tudo dela do FIWARE e do SQLite, mantendo o histórico do STH. `pytest` passa inteiro sem rede.

## 3. Requisitos e critérios de aceite

Formato: **QUANDO** <situação>, o backend **DEVE** <comportamento>. Cada requisito aponta os testes que o provam (código no `plan.md`).

### R1 — Entrada do cadastro
- **R1.1** `DeviceCreate` DEVE aceitar `device_id` só no formato `^vinheria\d{3}$` e `name` e `city` com 1 a 60 caracteres depois de tirar os espaços das pontas.
  Testes: `test_device_create_aceita_valido`, `test_device_create_rejeita_id_fora_do_formato`, `test_device_create_rejeita_nome_ou_cidade_vazios_ou_longos`.
- **R1.2** O `entity_id` DEVE ser derivado do `device_id`: `vinheria001` → `urn:ngsi-ld:Vinheria:001`.
  Teste: `test_entity_id_for_deriva_urn`.

### R2 — Faixa ideal (limites)
- **R2.1** A faixa padrão DEVE ser temperatura 12–18, umidade 50–70 e luminosidade 0–30.
  Teste: `test_default_limits_valores`.
- **R2.2** `AttrLimits` DEVE recusar `min >= max`.
  Teste: `test_attr_limits_rejeita_min_maior_ou_igual_max`.
- **R2.3** `LimitsStore.seed_defaults(device_id)` DEVE gravar as 3 linhas da faixa padrão em `triggers`, e `get(device_id)` DEVE devolvê-las. Atributo sem linha DEVE vir com o valor padrão.
  Testes: `test_limits_seed_e_get`, `test_limits_get_sem_linhas_usa_padrao`.
- **R2.4** `limits_to_orion_attrs(limits)` DEVE devolver `temp_min`, `temp_max`, `hum_min`, `hum_max`, `lux_min` e `lux_max` com os valores da faixa.
  Teste: `test_limits_to_orion_attrs`.

### R3 — Score de qualidade (RF11)
- **R3.1** `attr_score(value, lo, hi)` DEVE dar 100 dentro da faixa, bordas incluídas. Fora dela, DEVE dar `100 − 100 × distância ÷ (hi − lo)`, nunca abaixo de 0. Com `value` nulo, DEVE dar `None`.
  Testes: `test_attr_score_dentro_da_faixa`, `test_attr_score_acima_do_maximo`, `test_attr_score_abaixo_do_minimo`, `test_attr_score_nao_fica_negativo`, `test_attr_score_valor_nulo`.
- **R3.2** `quality_score(reading, limits)` DEVE devolver a média das 3 notas, arredondada a 1 casa, e as notas por atributo também arredondadas. Exemplo: 20 °C na faixa 12–18, com umidade e luz dentro da faixa, dá 88,9. Se **qualquer** atributo for nulo, o score geral DEVE ser `None`.
  Testes: `test_quality_score_tudo_ok`, `test_quality_score_exemplo_do_prd`, `test_quality_score_nulo_se_faltar_atributo`.
- **R3.3** QUANDO o score geral é `None`, o `ScoreReport` DEVE trazer `available: false` e `message` explicando o motivo, com os atributos sem leitura em português na ordem temperatura, umidade, luminosidade. Exemplo: `"Score indisponível: aguardando leitura de umidade e luminosidade"`. Com score calculado, DEVE trazer `available: true` e `message: null`. O painel (Tasks 5 e 6) exibe essa mensagem no lugar do número, e nunca mostra 0 ou um campo vazio.
  Testes: `test_score_indisponivel_traz_mensagem`, `test_score_disponivel_sem_mensagem`.

### R4 — Cadastro com provisionamento (RF01)
- **R4.1** QUANDO o `device_id` já está no SQLite, `create` DEVE levantar `DeviceAlreadyExists` **sem chamar o FIWARE**.
  Teste: `test_create_id_ja_cadastrado_levanta_conflito_sem_rede`.
- **R4.2** `create` DEVE chamar o FIWARE nesta ordem exata:
  1. service group (409 aceito);
  2. `delete_device` (404 aceito), que re-provisiona quem já existe;
  3. `provision_device` (5 comandos, 3 atributos);
  4. `delete_subscriptions` da entidade;
  5. `subscribe_attr` de `temperature`, `humidity` e `luminosity`;
  6. `update_attrs` com a faixa padrão, que é um upsert por `POST /v2/op/update` (`append`), conforme F4.

  Teste: `test_create_sequencia_completa_no_fiware`.
- **R4.3** Só depois do FIWARE, `create` DEVE gravar numa única transação a linha em `devices` (com `created_at` em ISO 8601 UTC) e a faixa padrão em `triggers`. Também DEVE devolver o `Device`.
  Teste: `test_create_grava_device_e_faixa_padrao`.
- **R4.4** QUANDO qualquer etapa do FIWARE falha, `create` DEVE propagar o `FiwareError` e **não gravar nada** no SQLite. Repetir o cadastro depois DEVE funcionar.
  Testes: `test_create_falha_no_fiware_nao_grava_nada`, `test_create_repetido_apos_falha_funciona`.
- **R4.5** Device que já existe no IoT Agent (a adoção da 001 e da 002) DEVE passar pela mesma sequência. Ele é removido e provisionado de novo com a configuração completa.
  Teste: `test_create_reprovisiona_device_existente`.
- **R4.6** Dois cadastros DEVEM gerar duas sequências completas e independentes.
  Teste: `test_create_dois_devices_duas_sequencias`.
- **R4.7** QUANDO o `POST /iot/devices` responde 409 durante o cadastro (F5), `create` DEVE remover o device e provisioná-lo de novo **uma vez**. Um segundo 409 DEVE propagar `FiwareConflict` sem gravar nada.
  Testes: `test_create_device_autoprovisionado_no_meio_tenta_de_novo`, `test_create_conflito_persistente_propaga`.

### R5 — Listagem e consulta
- **R5.1** `list()` DEVE devolver os devices do SQLite ordenados por `device_id`.
  Teste: `test_list_ordenado_por_id`.
- **R5.2** `get(device_id)` DEVE devolver o `Device`. Se o id não estiver cadastrado, DEVE levantar `DeviceNotFound`. `detail(device_id)` DEVE devolver o `Device` com a faixa.
  Testes: `test_get_inexistente_levanta_not_found`, `test_detail_inclui_faixa`.

### R6 — Remoção (RF02)
- **R6.1** `delete(device_id)` DEVE chamar o FIWARE nesta ordem: `delete_subscriptions`, `delete_device`, `delete_entity` (404 aceito em device e entidade). Depois DEVE apagar o device do SQLite, e os `triggers` dele saem em cascata.
  Teste: `test_delete_sequencia_e_remove_local`.
- **R6.2** As linhas de `alerts` da vinheria DEVEM permanecer.
  Teste: `test_delete_mantem_alertas`.
- **R6.3** QUANDO o FIWARE falha, `delete` DEVE propagar o erro e **manter** o cadastro local, para nova tentativa.
  Teste: `test_delete_fiware_fora_mantem_cadastro`.
- **R6.4** Id não cadastrado DEVE levantar `DeviceNotFound` sem chamar o FIWARE.
  Teste: `test_delete_inexistente_levanta_not_found_sem_rede`.

### R7 — Resolver de vinheria (RF15, consumido pela Task 7A)
- **R7.1** `resolve_vinheria(texto, devices)` DEVE comparar sem acento, sem diferença de caixa e com espaços colapsados.
  Teste: `test_resolve_ignora_acento_e_caixa`.
- **R7.2** A ordem de busca DEVE ser esta: (a) igualdade com o `device_id`; (b) igualdade com o nome ou a cidade; (c) trecho contido no id, no nome ou na cidade. A primeira etapa com exatamente 1 resultado decide. Uma etapa com 2 ou mais resultados DEVE levantar `AmbiguousVinheria(options)`, com as opções ordenadas por id. Sem resultado em nenhuma etapa, ou com texto vazio, DEVE levantar `VinheriaNotFound`.
  Testes: `test_resolve_por_id`, `test_resolve_por_cidade_exata`, `test_resolve_prefere_igualdade_a_trecho`, `test_resolve_ambiguo`, `test_resolve_nao_encontrado`, `test_resolve_texto_vazio`.

### R8 — Leituras (RF04, RF05, RF11)
- **R8.1** `current(device_id)` DEVE ler a entidade no Orion e devolver `temperature`, `humidity` e `luminosity` como `float`, mais o `time_instant`.
  Teste: `test_current_converte_valores`.
- **R8.2** Valor ausente, vazio, em branco, booleano, não numérico ou NaN DEVE virar `None`. Entidade inexistente no Orion (404) DEVE dar todos os valores `None`, não erro.
  Testes: `test_current_sem_atributos_de_sensor`, `test_current_valor_invalido_vira_nulo`, `test_current_entidade_inexistente_devolve_nulos`.
- **R8.3** `history(...)` DEVE repassar `last_n` ou `date_from`/`date_to` ao STH e normalizar cada ponto para `{ts: recvTime, value: float}`, descartando os pontos não numéricos.
  Testes: `test_history_normaliza_pontos`, `test_history_descarta_nao_numericos`, `test_history_repassa_janela_de_datas`.
- **R8.4** `score(device_id)` DEVE combinar `current` com a faixa **daquela** vinheria.
  Teste: `test_score_usa_faixa_da_vinheria`.
- **R8.5** Device não cadastrado DEVE levantar `DeviceNotFound` sem chamar o FIWARE.
  Teste: `test_readings_device_inexistente_sem_rede`.

### R9 — API
- **R9.1** As rotas da seção 4.4 DEVEM responder com os status indicados lá.
  Testes: `test_post_device_201`, `test_post_device_invalido_422`, `test_get_devices_lista`, `test_get_device_detalhe`, `test_delete_device_204`, `test_get_current`, `test_get_history_last_n`, `test_get_history_por_datas`, `test_get_history_janela_invalida_422`, `test_get_score`.
- **R9.2** Os erros de domínio DEVEM sair no mesmo formato da Task 2, `{detail, service: "registry"}`:
  - `DeviceNotFound` e `VinheriaNotFound` → 404;
  - `DeviceAlreadyExists` e `AmbiguousVinheria` → 409.

  Teste: `test_handler_traduz_erros_de_dominio`.
- **R9.3** `FiwareError` numa rota de device DEVE continuar no tradutor da Task 2 (ex.: 503 com a EC2 fora).
  Teste: `test_post_device_fiware_fora_503`.

## 4. Detalhes técnicos (design)

### 4.1 Estrutura de arquivos

```
backend/app/
├── models/schemas.py            # + DeviceCreate, AttrLimits, Limits, DeviceDetail, CurrentReading,
│                                #   HistoryPoint, HistoryQuery, AttrScores, ScoreReport; Device ganha created_at
├── services/
│   ├── registry_errors.py       # novo: RegistryError e subclasses
│   ├── limits.py                # novo: DEFAULT_LIMITS, limits_to_orion_attrs, LimitsStore
│   ├── quality_score.py         # novo: attr_score, quality_score (funções puras)
│   ├── device_registry.py       # novo: entity_id_for, DeviceRegistry
│   ├── vinheria_resolver.py     # novo: normalize_text, resolve_vinheria
│   └── readings.py              # novo: ReadingsService
├── api/
│   ├── deps.py                  # + get_registry, get_readings
│   ├── errors.py                # + tradutor de RegistryError
│   ├── routes_devices.py        # novo
│   └── routes_data.py           # novo
└── main.py                      # monta LimitsStore, DeviceRegistry, ReadingsService; inclui os 2 routers
backend/tests/
├── conftest.py                  # + fixtures limits, registry, readings
├── test_schemas_devices.py      # R1, R2.1, R2.2
├── test_limits.py               # R2.3, R2.4
├── test_quality_score.py        # R3
├── test_device_registry.py      # R4, R5
├── test_device_delete.py        # R6
├── test_vinheria_resolver.py    # R7
├── test_readings.py             # R8
└── test_routes_devices.py       # R9
```

Nenhum arquivo passa de ~250 linhas (`CLAUDE.md` §6).

### 4.2 Contratos públicos

```python
# app/models/schemas.py  (acréscimos)
SensorAttr = Literal["temperature", "humidity", "luminosity"]
class Device(BaseModel):          # + created_at: str | None = None (compatível com a Task 2)
class DeviceCreate(BaseModel):    # device_id ^vinheria\d{3}$; name, city 1..60 (strip)
class AttrLimits(BaseModel):      # min: float, max: float; min < max
class Limits(BaseModel):          # temperature, humidity, luminosity: AttrLimits
class DeviceDetail(Device):       # + limits: Limits
class CurrentReading(BaseModel):  # device_id, temperature, humidity, luminosity: float | None, time_instant: str | None
class HistoryPoint(BaseModel):    # ts: str, value: float
class HistoryQuery(BaseModel):    # attr: SensorAttr; last_n: int 1..500 | None; date_from, date_to: str | None (ISO 8601)
                                  # exige exatamente um modo: last_n OU datas
class AttrScores(BaseModel):      # temperature, humidity, luminosity: float | None
class ScoreReport(BaseModel):     # device_id, score: float | None, available: bool, message: str | None,
                                  # attrs: AttrScores, limits: Limits

# app/services/registry_errors.py
class RegistryError(Exception):           # .message; .service = "registry"
class DeviceNotFound(RegistryError)
class DeviceAlreadyExists(RegistryError)
class VinheriaNotFound(RegistryError)
class AmbiguousVinheria(RegistryError):   # .options: list[Device]

# app/services/limits.py
DEFAULT_LIMITS: Limits
def limits_to_orion_attrs(limits: Limits) -> dict[str, float]
class LimitsStore:
    def __init__(self, conn: sqlite3.Connection)
    def seed_defaults(self, device_id: str) -> None   # não faz commit: quem chama controla a transação
    def get(self, device_id: str) -> Limits

# app/services/quality_score.py
def attr_score(value: float | None, lo: float, hi: float) -> float | None
def quality_score(reading: CurrentReading, limits: Limits) -> tuple[float | None, AttrScores]

# app/services/device_registry.py
def entity_id_for(device_id: str) -> str
class DeviceRegistry:
    def __init__(self, conn: sqlite3.Connection, fiware: FiwareClient, limits: LimitsStore)
    async def create(self, data: DeviceCreate) -> Device
    def list(self) -> list[Device]
    def get(self, device_id: str) -> Device
    def detail(self, device_id: str) -> DeviceDetail
    async def delete(self, device_id: str) -> None

# app/services/vinheria_resolver.py
def normalize_text(texto: str) -> str
def resolve_vinheria(texto: str, devices: list[Device]) -> Device

# app/services/readings.py
class ReadingsService:
    def __init__(self, registry: DeviceRegistry, fiware: FiwareClient, limits: LimitsStore)
    async def current(self, device_id: str) -> CurrentReading
    async def history(self, device_id: str, query: HistoryQuery) -> list[HistoryPoint]
    async def score(self, device_id: str) -> ScoreReport
```

### 4.3 Sequências no FIWARE

**Cadastro** (`create`). Cada etapa aceita repetição, então uma falha no meio se resolve tentando de novo:

| # | Chamada | Status aceitos além de 2xx |
|---|---|---|
| 1 | `POST /iot/services` | 409 |
| 2 | `DELETE /iot/devices/{device_id}` | 404 |
| 3 | `POST /iot/devices` | 409 → remove o device e provisiona de novo uma vez (R4.7); o segundo 409 propaga |
| 4 | `GET /v2/subscriptions` e `DELETE` das subscriptions da entidade | 404 no DELETE |
| 5 | `POST /v2/subscriptions` × 3 (temperature, humidity, luminosity) | — |
| 6 | `POST /v2/op/update` (`append`) com `temp_min`…`lux_max` (F4) | — |
| 7 | SQLite: `INSERT devices` + 3 × `INSERT triggers`, numa transação | — |

**Remoção** (`delete`): `delete_subscriptions` → `DELETE /iot/devices/{id}` (404 ok) → `DELETE /v2/entities/{entity_id}` (404 ok; pela F2 já costuma ter sumido) → `DELETE FROM devices` (os `triggers` saem em cascata; os `alerts` ficam).

### 4.4 API

| Rota | Entrada | Sucesso | Erros |
|---|---|---|---|
| `POST /api/devices` | JSON `DeviceCreate` | 201 `Device` | 422 · 409 (já cadastrado) · 503/502 (FIWARE) |
| `GET /api/devices` | — | 200 `[Device]` | — |
| `GET /api/devices/{device_id}` | — | 200 `DeviceDetail` | 404 |
| `DELETE /api/devices/{device_id}` | — | 204 | 404 · 503/502 |
| `GET /api/devices/{device_id}/current` | — | 200 `CurrentReading` | 404 · 503 |
| `GET /api/devices/{device_id}/history` | query `HistoryQuery` | 200 `[HistoryPoint]` | 422 (attr inválido, nenhum modo, dois modos, `last_n` fora de 1–500, data inválida) · 404 · 503 |
| `GET /api/devices/{device_id}/score` | — | 200 `ScoreReport` | 404 · 503 |

As rotas só chamam `DeviceRegistry` e `ReadingsService`, que chegam por injeção a partir de `app.state` (`get_registry`, `get_readings`).

### 4.5 Decisões de design

| # | Decisão | Motivo |
|---|---|---|
| D1 | FIWARE primeiro, SQLite por último, com todas as etapas aceitando repetição. Sem rollback compensatório. | Se o FIWARE falha, nada fica gravado localmente, e repetir o cadastro conserta. É mais simples que um estado `pendente` (decisão do usuário: abordagem A). |
| D2 | **Re-provisionar sempre**: o cadastro remove o device no IoT Agent antes de provisionar. | A F3 mostra que não dá para acrescentar `set_limits` com `PUT`. A 001 e a 002 precisam ganhá-lo (decisão do usuário). A entidade é recriada e os valores voltam na próxima leitura, cerca de 2 s depois. O histórico do STH não é afetado. |
| D3 | As subscriptions são apagadas e recriadas a cada cadastro. | Evita duplicar subscriptions ao adotar um device que já as tinha, e uma subscription duplicada grava o histórico em dobro. |
| D4 | A faixa padrão é publicada no Orion já no cadastro, por `POST /v2/op/update` (`append`). | O `POST /attrs` falha antes da primeira leitura (F4); o upsert cria a entidade e funciona sempre. Assim o Orion fica coerente com o SQLite desde o início (RF06). A Task 4 herda o mesmo `update_attrs`. |
| D5 | O usuário digita o `device_id`, que precisa bater com o `ID_DEVICE` do firmware. | Decisão do usuário. A atribuição automática vira tarefa opcional futura (seção 4.6). |
| D6 | Score pela média proporcional; `None` se qualquer atributo faltar, com `available: false` e uma mensagem de motivo. | Decisão do usuário. Não dá score bom a partir de dado incompleto, e o painel mostra "indisponível" com o motivo em vez de um número enganoso. |
| D7 | `/current` devolve `null` em vez de erro quando não há leitura. | Uma vinheria recém-cadastrada não tem sensores no Orion (F1). O painel mostra "aguardando primeira leitura". |
| D8 | `register_commands` sai do plano. | O IoT Agent registra os comandos sozinho (achado da Task 1, confirmado na F1). |
| D9 | O resolver fica só como serviço, sem rota. | Quem consome é o chatbot (7A). Expor a rota agora seria escopo sem uso. |
| D10 | O `HistoryQuery` é validado pelo Pydantic na query string. | Erro de janela vira 422 automático, sem lógica de validação dentro da rota. |
| D11 | Corrida entre dois cadastros do mesmo id: o `IntegrityError` do SQLite vira `DeviceAlreadyExists`. | Fecha a janela entre a checagem inicial e o `INSERT`. |
| D12 | Falha no meio do cadastro deixa resíduo no FIWARE (device, subscriptions) sem linha no SQLite. Não há limpeza compensatória. | Visto na primeira tentativa da 3.8. Repetir o cadastro do mesmo id re-provisiona e recria as subscriptions sem duplicar (D2, D3). Uma limpeza compensatória falharia pelo mesmo motivo da falha original (EC2 instável). |

### 4.6 Fora de escopo

- Editar a faixa ideal (`PUT /api/devices/{id}/triggers`, `update_attrs` com valores novos, comando `set_limits`): Task 4.
- Motor de alertas, offline, `/api/fleet` e log de alertas: Task 4.
- Firmware recebendo e exibindo `set_limits`: Task 4B.
- **Tarefa opcional futura: atribuição automática do id.** O ESP32 sem id mostra um código no LCD. O usuário informa esse código no cadastro, e o backend envia o id pelo comando `assign` de um device fixo `bootstrap`. Primeiro passo: verificar se as abas do Wokwi têm MAC diferente. Limitação conhecida: o Wokwi não guarda a flash entre execuções, então o id precisaria ser reatribuído a cada reinício da simulação.

## 5. Ferramentas e requisitos

- Nenhuma dependência nova. Usa o que já está em `backend/requirements.txt`.
- Testes sem rede (`respx` + SQLite em `tmp_path`).
- Para a verificação real (última subtarefa):
  - EC2 ligada com os containers de pé.
  - Wokwi da `vinheria001` e da `vinheria002` rodando.
  - **Nome e cidade da 001 e da 002**, informados pelo usuário.

## 6. Como verificar (aceite da task)

1. `cd backend && .venv/Scripts/python -m pytest -q` passa inteiro, sem rede.
2. O Swagger (`/docs`) mostra as 7 rotas da seção 4.4.
3. Com a EC2 e o Wokwi ligados, `POST /api/devices` da `vinheria001` responde 201. Depois disso:
   - `GET :4041/iot/devices/vinheria001` lista os 5 comandos, `set_limits` incluído;
   - a entidade no Orion tem `temp_min`…`lux_max` com a faixa padrão;
   - há exatamente 3 subscriptions da entidade;
   - o `GET /current` mostra valores reais e um `time_instant` que avança entre duas chamadas;
   - um `alert_off` enviado pelo Orion é respondido pelo Wokwi (`alert_off_status: OK`), provando que o upsert não quebrou o encaminhamento de comandos.
4. O mesmo vale para a `vinheria002`.
5. `GET /history?attr=temperature&last_n=20` devolve pontos `{ts, value}` reais, e `GET /score` devolve um número coerente com os valores atuais.
6. Ciclo descartável com a `vinheria099`:
   - `POST` dela responde 201, e `DELETE` responde 204;
   - depois, o device e a entidade dão 404 no FIWARE, e não sobra subscription com `Vinheria:099`.
7. `git status` não mostra `.env` nem `*.db`.
