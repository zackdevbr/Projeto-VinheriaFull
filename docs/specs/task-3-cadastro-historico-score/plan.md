# Task 3 — Cadastro de vinherias, histórico e score — Plano de execução

> **Para quem executa (Sonnet):** use `superpowers:executing-plans` (ou `superpowers:subagent-driven-development`). Os passos usam checkbox (`- [ ]`). Execute **uma subtarefa por vez**, informe o resultado de cada passo e **pare para revisão do usuário ao fim de cada subtarefa** (`CLAUDE.md` §2 e §4). Se algo não bater com a spec, pare e devolva para planejamento; não improvise.

**Objetivo:** cadastrar, listar e remover vinherias com provisionamento completo no FIWARE (re-provisionando as que já existem), e expor estado atual, histórico normalizado e score de qualidade por vinheria.

**Arquitetura:** `DeviceRegistry` orquestra o FIWARE (via `FiwareClient`) e grava no SQLite só no fim; `LimitsStore` guarda a faixa ideal; `quality_score` é puro; `ReadingsService` lê Orion e STH; `vinheria_resolver` é puro. As rotas só falam com `DeviceRegistry` e `ReadingsService`, injetados a partir de `app.state`.

**Stack:** Python 3.12, FastAPI 0.142.2, Pydantic 2.13.5, httpx 0.28.1, SQLite, pytest + respx + `anyio`. Nenhuma dependência nova.

**Spec:** [`spec.md`](spec.md) — requisitos R1 a R9, fatos F1 a F3 e decisões D1 a D11. Leia antes de começar.

> **Estado em 07/10/2026 (fim do dia):**
> - **Feitas:** subtarefas 3.1 a 3.7 (commits `568d33d`..`2426476`, 158 testes).
> - **Desvio registrado na 3.5:** a busca "rio" do `test_resolve_por_trecho` também casava "empório". O teste passou a usar "carioca", e entrou `test_resolve_trecho_em_varias_e_ambiguo`. O código ficou igual.
> - **Primeira tentativa da 3.8:** parou no fato F4 da spec (o `POST /attrs` responde 404 antes da primeira leitura).
> - **Retomar na 3.7a.** Depois vêm a 3.7b e a 3.8 reescrita, com lições de shell, checagem de comando e os nomes da 001 e da 002.

## Global Constraints

- Todos os comandos rodam de dentro de `backend/` com `.venv/Scripts/python -m ...`.
- Nenhuma dependência nova; `requirements.txt` não muda.
- Comentários e docstrings **em português**, explicando o propósito de cada módulo e de cada função não óbvia.
- Só `app/services/fiware_base.py` importa `httpx` em código de produção. Rotas não importam `httpx` nem chamam `FiwareClient` direto.
- Nomes canônicos: device `vinheria00N`, entity `urn:ngsi-ld:Vinheria:00N`, type `Vinheria`; atributos `temperature`, `humidity`, `luminosity`; faixa no Orion `temp_min`, `temp_max`, `hum_min`, `hum_max`, `lux_min`, `lux_max`.
- Faixa padrão: temperatura 12–18, umidade 50–70, luminosidade 0–30.
- Nenhum arquivo passa de ~250 linhas.
- Testes nunca acessam a rede: toda chamada HTTP é interceptada pelo `respx`.
- Commits: mensagem em português, imperativo, uma linha, prefixo `feat:`/`test:`/`chore:`/`docs:`, **sem linha de co-author** (`CLAUDE.md` §8 prevalece sobre qualquer lembrete de atribuição).
- Suíte de partida: 63 testes passando (fim da Task 2).

## Review Focus

Situações que um usuário real vai encontrar e que a spec implica. Cada uma tem teste na subtarefa indicada.

1. **EC2 cai no meio do cadastro:** nada fica gravado localmente, e repetir o cadastro funciona. Testes `test_create_falha_no_fiware_nao_grava_nada` e `test_create_repetido_apos_falha_funciona` (3.3).
2. **Remover com a EC2 desligada:** a API responde 503 e a vinheria continua na lista, para tentar de novo. Teste `test_delete_fiware_fora_mantem_cadastro` (3.4).
3. **Orion com valor estranho** (`" "`, texto, booleano, `NaN`) ou vinheria sem leitura ainda: `/current` não quebra e o score diz "indisponível" com o motivo. Testes `test_current_valor_invalido_vira_nulo`, `test_current_sem_atributos_de_sensor` e `test_score_indisponivel_no_report` (3.6).
4. **"São Paulo" digitado de vários jeitos** no chatbot, e cidades parecidas ("São Paulo" × "São Paulo do Sul"): resolve certo ou pede esclarecimento. Testes `test_resolve_ignora_acento_e_caixa` e `test_resolve_prefere_igualdade_a_trecho` (3.5).
5. **Janela de histórico mal formada vinda do front** (sem modo, dois modos, data inválida, `last_n` 0): 422 claro, nunca 500. Teste `test_get_history_janela_invalida_422` (3.7).

---

## Subtarefa 3.1 — Schemas de cadastro e faixa ideal (R1.1, R2)

**Files:**
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/services/limits.py`
- Create: `backend/tests/test_schemas_devices.py`, `backend/tests/test_limits.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `Device` (Task 2), `connect` e fixture `conn` (Task 2).
- Produces: `Device.created_at`; `DeviceCreate`, `AttrLimits`, `Limits`, `DeviceDetail`; `DEFAULT_LIMITS`, `ORION_LIMIT_NAMES`, `limits_to_orion_attrs(limits) -> dict[str, float]`; `LimitsStore(conn)` com `seed_defaults(device_id) -> None` (sem commit) e `get(device_id) -> Limits`; fixture `limits`.

- [ ] **Passo 1: escrever os testes de schema que falham**

`backend/tests/test_schemas_devices.py`:

```python
"""Testes dos schemas de cadastro (spec R1.1)."""
import pytest
from pydantic import ValidationError

from app.models.schemas import Device, DeviceCreate


def test_device_create_aceita_valido():
    dados = DeviceCreate(device_id="vinheria001", name="  Vinheria Paulista ", city=" São Paulo ")
    assert dados.device_id == "vinheria001"
    assert dados.name == "Vinheria Paulista"
    assert dados.city == "São Paulo"


@pytest.mark.parametrize("device_id", ["vinheria1", "Vinheria001", "vinheria0001", "adega001"])
def test_device_create_rejeita_id_fora_do_formato(device_id):
    with pytest.raises(ValidationError):
        DeviceCreate(device_id=device_id, name="Vinheria", city="Cidade")


@pytest.mark.parametrize("campos", [
    {"name": ""},
    {"name": "   "},
    {"name": "x" * 61},
    {"city": "x" * 61},
])
def test_device_create_rejeita_nome_ou_cidade_vazios_ou_longos(campos):
    dados = {"device_id": "vinheria001", "name": "Vinheria", "city": "Cidade", **campos}
    with pytest.raises(ValidationError):
        DeviceCreate(**dados)


def test_device_compativel_sem_created_at():
    device = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                    name="Vinheria", city="Cidade")
    assert device.created_at is None
```

- [ ] **Passo 2: escrever os testes de faixa que falham**

`backend/tests/test_limits.py`:

```python
"""Testes da faixa ideal: padrão, validação, SQLite e nomes no Orion (spec R2)."""
import pytest
from pydantic import ValidationError

from app.models.schemas import AttrLimits
from app.services.limits import DEFAULT_LIMITS, limits_to_orion_attrs


def _grava_device(conn, device_id="vinheria001"):
    """Cria a linha em devices (exigida pela chave estrangeira de triggers)."""
    with conn:
        conn.execute(
            "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
            "VALUES (?, ?, 'Vinheria', 'Cidade', '2026-10-07T21:00:00+00:00')",
            (device_id, "urn:ngsi-ld:Vinheria:" + device_id[-3:]),
        )


def test_default_limits_valores():
    assert (DEFAULT_LIMITS.temperature.min, DEFAULT_LIMITS.temperature.max) == (12, 18)
    assert (DEFAULT_LIMITS.humidity.min, DEFAULT_LIMITS.humidity.max) == (50, 70)
    assert (DEFAULT_LIMITS.luminosity.min, DEFAULT_LIMITS.luminosity.max) == (0, 30)


@pytest.mark.parametrize("minimo, maximo", [(18, 12), (15, 15)])
def test_attr_limits_rejeita_min_maior_ou_igual_max(minimo, maximo):
    with pytest.raises(ValidationError):
        AttrLimits(min=minimo, max=maximo)


def test_limits_seed_e_get(conn, limits):
    _grava_device(conn)
    with conn:
        limits.seed_defaults("vinheria001")
    assert conn.execute("SELECT COUNT(*) FROM triggers").fetchone()[0] == 3
    assert limits.get("vinheria001") == DEFAULT_LIMITS


def test_limits_get_sem_linhas_usa_padrao(conn, limits):
    _grava_device(conn)
    with conn:
        conn.execute("INSERT INTO triggers (device_id, attr, min_value, max_value) "
                     "VALUES ('vinheria001', 'temperature', 10, 20)")
    faixa = limits.get("vinheria001")
    assert (faixa.temperature.min, faixa.temperature.max) == (10, 20)
    assert faixa.humidity == DEFAULT_LIMITS.humidity
    assert faixa.luminosity == DEFAULT_LIMITS.luminosity


def test_limits_to_orion_attrs():
    assert limits_to_orion_attrs(DEFAULT_LIMITS) == {
        "temp_min": 12, "temp_max": 18,
        "hum_min": 50, "hum_max": 70,
        "lux_min": 0, "lux_max": 30,
    }
```

- [ ] **Passo 3: acrescentar a fixture `limits` ao `conftest.py`**

Em `backend/tests/conftest.py`, acrescentar o import junto dos demais:

```python
from app.services.limits import LimitsStore
```

E, ao fim do arquivo:

```python
@pytest.fixture
def limits(conn):
    """LimitsStore sobre o banco de teste."""
    return LimitsStore(conn)
```

- [ ] **Passo 4: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_schemas_devices.py tests/test_limits.py -v`
Expected: erro de coleta com `ModuleNotFoundError: No module named 'app.services.limits'` (ou `ImportError` de `DeviceCreate`).

- [ ] **Passo 5: ampliar `backend/app/models/schemas.py`**

Trocar o import do topo:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
```

Atualizar a docstring do módulo (segundo parágrafo) para:

```python
"""
Modelos de dados (Pydantic) compartilhados pelo backend.

Aqui ficam os contratos de entrada e saída da API e dos services:
configuração e saúde do FIWARE (Task 2), cadastro, faixa ideal, leituras,
histórico e score (Task 3). As próximas tasks acrescentam os seus.
"""
```

Acrescentar `created_at` ao `Device` (o resto da classe fica igual):

```python
class Device(BaseModel):
    """Uma vinheria cadastrada: device no IoT Agent e entidade no Orion."""
    device_id: str = Field(pattern=r"^vinheria\d{3}$")
    entity_id: str
    name: str
    city: str
    # Opcional para manter compatível o uso da Task 2 (provision_device)
    created_at: str | None = None
```

E acrescentar, logo depois da classe `Device`:

```python
class DeviceCreate(BaseModel):
    """Entrada do cadastro de uma vinheria (o id precisa bater com o ID_DEVICE do firmware)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: str = Field(pattern=r"^vinheria\d{3}$")
    name: str = Field(min_length=1, max_length=60)
    city: str = Field(min_length=1, max_length=60)


class AttrLimits(BaseModel):
    """Faixa ideal de um atributo: serve de limite de alerta e de referência do score."""
    min: float
    max: float

    @model_validator(mode="after")
    def _min_menor_que_max(self) -> "AttrLimits":
        """Recusa faixa vazia ou invertida."""
        if self.min >= self.max:
            raise ValueError("min deve ser menor que max")
        return self


class Limits(BaseModel):
    """Faixa ideal dos três atributos de uma vinheria."""
    temperature: AttrLimits
    humidity: AttrLimits
    luminosity: AttrLimits


class DeviceDetail(Device):
    """Vinheria com a faixa ideal configurada."""
    limits: Limits
```

- [ ] **Passo 6: criar `backend/app/services/limits.py`**

```python
"""
Faixa ideal de cada vinheria (tabela triggers do SQLite).

A faixa é única por atributo e serve a dois usos: limite dos alertas
(Task 4) e referência do score de qualidade. Vinheria recém-cadastrada
recebe a faixa padrão. A Task 4 acrescenta aqui a edição da faixa.
"""
import sqlite3

from app.models.schemas import AttrLimits, Limits

# Faixa padrão do PRD (RF11): 12–18 °C, 50–70 % de umidade, luz de 0 a 30 %
DEFAULT_LIMITS = Limits(
    temperature=AttrLimits(min=12, max=18),
    humidity=AttrLimits(min=50, max=70),
    luminosity=AttrLimits(min=0, max=30),
)

# Nomes canônicos da faixa como atributos da entidade no Orion
ORION_LIMIT_NAMES = {
    "temperature": ("temp_min", "temp_max"),
    "humidity": ("hum_min", "hum_max"),
    "luminosity": ("lux_min", "lux_max"),
}


def limits_to_orion_attrs(limits: Limits) -> dict[str, float]:
    """Converte a faixa para os atributos temp_min…lux_max publicados no Orion."""
    attrs: dict[str, float] = {}
    for attr, (nome_min, nome_max) in ORION_LIMIT_NAMES.items():
        faixa = getattr(limits, attr)
        attrs[nome_min] = faixa.min
        attrs[nome_max] = faixa.max
    return attrs


class LimitsStore:
    """Leitura e gravação da faixa ideal no SQLite."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def seed_defaults(self, device_id: str) -> None:
        """Grava a faixa padrão para uma vinheria nova.

        Não faz commit: quem chama controla a transação, para gravar o device
        e a faixa juntos (ou nada).
        """
        for attr in ORION_LIMIT_NAMES:
            faixa = getattr(DEFAULT_LIMITS, attr)
            self._conn.execute(
                "INSERT INTO triggers (device_id, attr, min_value, max_value) "
                "VALUES (?, ?, ?, ?)",
                (device_id, attr, faixa.min, faixa.max),
            )

    def get(self, device_id: str) -> Limits:
        """Faixa da vinheria; atributo sem linha no banco usa o padrão."""
        valores = {attr: getattr(DEFAULT_LIMITS, attr) for attr in ORION_LIMIT_NAMES}
        for linha in self._conn.execute(
            "SELECT attr, min_value, max_value FROM triggers WHERE device_id = ?",
            (device_id,),
        ):
            if linha["attr"] in valores:
                valores[linha["attr"]] = AttrLimits(min=linha["min_value"],
                                                    max=linha["max_value"])
        return Limits(**valores)
```

- [ ] **Passo 7: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_schemas_devices.py tests/test_limits.py -v`
Expected: 16 testes `PASSED` (10 de schema, 6 de faixa).

- [ ] **Passo 8: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q`
Expected: `79 passed`.

- [ ] **Passo 9: commit**

```bash
git add backend/app/models/schemas.py backend/app/services/limits.py backend/tests/conftest.py backend/tests/test_schemas_devices.py backend/tests/test_limits.py
git commit -m "feat: adiciona schemas de cadastro e faixa ideal padrao das vinherias"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.2 — Score de qualidade (R3)

**Files:**
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/services/quality_score.py`
- Create: `backend/tests/test_quality_score.py`

**Interfaces:**
- Consumes: `Limits`, `AttrLimits` (3.1); `DEFAULT_LIMITS` (3.1).
- Produces: `CurrentReading`, `AttrScores`; `ATTR_LABELS`; `attr_score(value, lo, hi) -> float | None`; `quality_score(reading, limits) -> tuple[float | None, AttrScores]`; `unavailable_message(attrs: AttrScores) -> str | None`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_quality_score.py`:

```python
"""Testes do score de qualidade do ambiente (spec R3)."""
import pytest

from app.models.schemas import AttrScores, CurrentReading
from app.services.limits import DEFAULT_LIMITS
from app.services.quality_score import attr_score, quality_score, unavailable_message


def _leitura(temperature=15.0, humidity=60.0, luminosity=10.0):
    """Leitura sintética; por padrão, tudo dentro da faixa padrão."""
    return CurrentReading(device_id="vinheria001", temperature=temperature,
                          humidity=humidity, luminosity=luminosity)


@pytest.mark.parametrize("valor", [12, 15, 18])
def test_attr_score_dentro_da_faixa(valor):
    assert attr_score(valor, 12, 18) == 100


def test_attr_score_acima_do_maximo():
    assert attr_score(20, 12, 18) == pytest.approx(66.6667, abs=1e-3)


def test_attr_score_abaixo_do_minimo():
    assert attr_score(9, 12, 18) == pytest.approx(50.0)


def test_attr_score_nao_fica_negativo():
    assert attr_score(40, 12, 18) == 0


def test_attr_score_valor_nulo():
    assert attr_score(None, 12, 18) is None


def test_quality_score_tudo_ok():
    nota, notas = quality_score(_leitura(), DEFAULT_LIMITS)
    assert nota == 100
    assert notas == AttrScores(temperature=100, humidity=100, luminosity=100)


def test_quality_score_exemplo_do_prd():
    nota, notas = quality_score(_leitura(temperature=20.0), DEFAULT_LIMITS)
    assert nota == 88.9
    assert notas.temperature == 66.7


def test_quality_score_nulo_se_faltar_atributo():
    nota, notas = quality_score(_leitura(humidity=None), DEFAULT_LIMITS)
    assert nota is None
    assert notas.humidity is None
    assert notas.temperature == 100


@pytest.mark.parametrize("notas, esperado", [
    (AttrScores(temperature=100, humidity=None, luminosity=None),
     "Score indisponível: aguardando leitura de umidade e luminosidade"),
    (AttrScores(),
     "Score indisponível: aguardando leitura de temperatura, umidade e luminosidade"),
])
def test_score_indisponivel_traz_mensagem(notas, esperado):
    assert unavailable_message(notas) == esperado


def test_score_disponivel_sem_mensagem():
    assert unavailable_message(AttrScores(temperature=100, humidity=80, luminosity=100)) is None
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_quality_score.py -v`
Expected: erro de coleta com `ImportError` (`AttrScores`/`CurrentReading`) ou `ModuleNotFoundError: No module named 'app.services.quality_score'`.

- [ ] **Passo 3: acrescentar os schemas de leitura a `backend/app/models/schemas.py`**

Ao fim do arquivo:

```python
class CurrentReading(BaseModel):
    """Estado atual de uma vinheria; None quando ainda não há leitura válida."""
    device_id: str
    temperature: float | None = None
    humidity: float | None = None
    luminosity: float | None = None
    time_instant: str | None = None


class AttrScores(BaseModel):
    """Nota de 0 a 100 de cada atributo; None quando falta a leitura."""
    temperature: float | None = None
    humidity: float | None = None
    luminosity: float | None = None
```

- [ ] **Passo 4: criar `backend/app/services/quality_score.py`**

```python
"""
Score de qualidade do ambiente de uma vinheria (RF11).

Cada atributo vale 100 dentro da faixa ideal da vinheria; fora dela, perde
pontos na proporção da distância em relação à largura da faixa, sem ficar
negativo. O score geral é a média dos três. Funções puras: não acessam
banco nem rede.
"""
from app.models.schemas import AttrScores, CurrentReading, Limits

# Ordem e nomes em português usados nas mensagens ao usuário
ATTR_LABELS = {
    "temperature": "temperatura",
    "humidity": "umidade",
    "luminosity": "luminosidade",
}


def attr_score(value: float | None, lo: float, hi: float) -> float | None:
    """Nota de um atributo: 100 na faixa [lo, hi]; fora, cai proporcionalmente.

    Ex.: faixa 12–18 (largura 6) e valor 20 (2 acima) → 100 − 100·2/6 = 66,7.
    """
    if value is None:
        return None
    if lo <= value <= hi:
        return 100.0
    distancia = lo - value if value < lo else value - hi
    return max(0.0, 100.0 - 100.0 * distancia / (hi - lo))


def quality_score(reading: CurrentReading, limits: Limits) -> tuple[float | None, AttrScores]:
    """Score geral (média, 1 casa) e notas por atributo.

    Se qualquer atributo não tiver leitura, o score geral é None: não se
    calcula nota a partir de dado incompleto.
    """
    notas: dict[str, float | None] = {}
    for attr in ATTR_LABELS:
        faixa = getattr(limits, attr)
        notas[attr] = attr_score(getattr(reading, attr), faixa.min, faixa.max)
    arredondadas = AttrScores(**{
        attr: None if nota is None else round(nota, 1) for attr, nota in notas.items()
    })
    if any(nota is None for nota in notas.values()):
        return None, arredondadas
    return round(sum(notas.values()) / len(notas), 1), arredondadas


def unavailable_message(attrs: AttrScores) -> str | None:
    """Mensagem para o painel quando o score não pode ser calculado; None se pode."""
    faltando = [rotulo for attr, rotulo in ATTR_LABELS.items() if getattr(attrs, attr) is None]
    if not faltando:
        return None
    if len(faltando) == 1:
        lista = faltando[0]
    else:
        lista = ", ".join(faltando[:-1]) + " e " + faltando[-1]
    return f"Score indisponível: aguardando leitura de {lista}"
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_quality_score.py -v`
Expected: 13 testes `PASSED`.

- [ ] **Passo 6: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q`
Expected: `92 passed`.

- [ ] **Passo 7: commit**

```bash
git add backend/app/models/schemas.py backend/app/services/quality_score.py backend/tests/test_quality_score.py
git commit -m "feat: adiciona score de qualidade do ambiente por media proporcional"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.3 — Cadastro com provisionamento, listagem e consulta (R1.2, R4, R5)

**Files:**
- Create: `backend/app/services/registry_errors.py`, `backend/app/services/device_registry.py`
- Create: `backend/tests/test_device_registry.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `FiwareClient` (`provision_service_group`, `delete_device`, `provision_device`, `delete_subscriptions`, `subscribe_attr`, `update_attrs`) e `ATRIBUTOS_LONGOS` de `fiware_constants` (Task 2); `Device`, `DeviceCreate`, `DeviceDetail`, `LimitsStore`, `DEFAULT_LIMITS`, `limits_to_orion_attrs` (3.1).
- Produces: `RegistryError` (`.message`, `.service = "registry"`), `DeviceNotFound`, `DeviceAlreadyExists`, `VinheriaNotFound`, `AmbiguousVinheria(message, options)` (`.options`); `entity_id_for(device_id) -> str`; `DeviceRegistry(conn, fiware, limits)` com `async create(data) -> Device`, `list() -> list[Device]`, `get(device_id) -> Device`, `detail(device_id) -> DeviceDetail`; fixtures `registry` e `cadastrar`.

- [ ] **Passo 1: acrescentar as fixtures ao `conftest.py`**

Em `backend/tests/conftest.py`, acrescentar os imports junto dos demais:

```python
from app.models.schemas import Device
from app.services.device_registry import DeviceRegistry
```

E, ao fim do arquivo:

```python
@pytest.fixture
def registry(conn, fiware, limits):
    """DeviceRegistry com FIWARE interceptado pelo respx e banco de teste."""
    return DeviceRegistry(conn, fiware, limits)


@pytest.fixture
def cadastrar(conn, limits):
    """Grava vinherias direto no SQLite, sem FIWARE (para testes de leitura e remoção)."""
    def _cadastrar(numero="001", name="Vinheria Paulista", city="São Paulo"):
        device = Device(device_id=f"vinheria{numero}",
                        entity_id=f"urn:ngsi-ld:Vinheria:{numero}",
                        name=name, city=city, created_at="2026-10-07T21:00:00+00:00")
        with conn:
            conn.execute(
                "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (device.device_id, device.entity_id, device.name, device.city,
                 device.created_at),
            )
            limits.seed_defaults(device.device_id)
        return device
    return _cadastrar
```

- [ ] **Passo 2: escrever os testes que falham**

`backend/tests/test_device_registry.py`:

```python
"""Testes do cadastro com provisionamento, listagem e consulta (spec R1.2, R4, R5)."""
import json
from datetime import datetime

import httpx
import pytest
import respx

from app.models.schemas import DeviceCreate
from app.services.device_registry import entity_id_for
from app.services.fiware_errors import FiwareError
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import DeviceAlreadyExists, DeviceNotFound

pytestmark = pytest.mark.anyio

IOTA = "http://10.0.0.1:4041"
ORION = "http://10.0.0.1:1026"
E1 = "urn:ngsi-ld:Vinheria:001"
NOVA = DeviceCreate(device_id="vinheria001", name="Vinheria Paulista", city="São Paulo")
CRIADA = httpx.Response(201, headers={"Location": "/v2/subscriptions/abc"})


def _mock_cadastro(numero="001", device_existente=False, subscricao=None, faixa=None):
    """Registra no respx todas as rotas do cadastro de uma vinheria.

    `subscricao` e `faixa` permitem trocar a resposta (ou side_effect) do
    POST de subscriptions e do POST da faixa no Orion.
    """
    entidade = f"urn:ngsi-ld:Vinheria:{numero}"
    respx.post(f"{IOTA}/iot/services").mock(return_value=httpx.Response(201))
    respx.delete(f"{IOTA}/iot/devices/vinheria{numero}").mock(
        return_value=httpx.Response(204 if device_existente else 404))
    respx.post(f"{IOTA}/iot/devices").mock(return_value=httpx.Response(201))
    respx.get(f"{ORION}/v2/subscriptions").mock(return_value=httpx.Response(200, json=[]))
    rota_sub = respx.post(f"{ORION}/v2/subscriptions")
    if subscricao is None:
        rota_sub.mock(return_value=CRIADA)
    else:
        rota_sub.mock(side_effect=subscricao)
    rota_faixa = respx.post(f"{ORION}/v2/entities/{entidade}/attrs")
    if faixa is None:
        rota_faixa.mock(return_value=httpx.Response(204))
    else:
        rota_faixa.mock(side_effect=faixa)


def _chamadas():
    """(método, caminho) de todas as chamadas interceptadas, em ordem."""
    return [(c.request.method, c.request.url.path) for c in respx.calls]


def _conta(conn, tabela):
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_entity_id_for_deriva_urn():
    assert entity_id_for("vinheria001") == "urn:ngsi-ld:Vinheria:001"
    assert entity_id_for("vinheria042") == "urn:ngsi-ld:Vinheria:042"


async def test_create_id_ja_cadastrado_levanta_conflito_sem_rede(registry, cadastrar):
    cadastrar("001")
    with respx.mock() as mock:
        with pytest.raises(DeviceAlreadyExists):
            await registry.create(NOVA)
    assert mock.calls.call_count == 0


@respx.mock
async def test_create_sequencia_completa_no_fiware(registry):
    _mock_cadastro()
    await registry.create(NOVA)
    assert _chamadas() == [
        ("POST", "/iot/services"),
        ("DELETE", "/iot/devices/vinheria001"),
        ("POST", "/iot/devices"),
        ("GET", "/v2/subscriptions"),
        ("POST", "/v2/subscriptions"),
        ("POST", "/v2/subscriptions"),
        ("POST", "/v2/subscriptions"),
        ("POST", f"/v2/entities/{E1}/attrs"),
    ]
    assinados = [
        json.loads(c.request.content)["subject"]["condition"]["attrs"][0]
        for c in respx.calls
        if c.request.method == "POST" and c.request.url.path == "/v2/subscriptions"
    ]
    assert assinados == ["temperature", "humidity", "luminosity"]
    faixa = json.loads(respx.calls[-1].request.content)
    assert faixa == {
        "temp_min": {"type": "Number", "value": 12},
        "temp_max": {"type": "Number", "value": 18},
        "hum_min": {"type": "Number", "value": 50},
        "hum_max": {"type": "Number", "value": 70},
        "lux_min": {"type": "Number", "value": 0},
        "lux_max": {"type": "Number", "value": 30},
    }


@respx.mock
async def test_create_grava_device_e_faixa_padrao(registry, conn, limits):
    _mock_cadastro()
    device = await registry.create(NOVA)
    assert device.entity_id == E1
    assert registry.list() == [device]
    assert datetime.fromisoformat(device.created_at).tzinfo is not None
    assert _conta(conn, "triggers") == 3
    assert limits.get("vinheria001") == DEFAULT_LIMITS


@respx.mock
async def test_create_falha_no_fiware_nao_grava_nada(registry, conn):
    _mock_cadastro(subscricao=[httpx.Response(500, text="falhou")])
    with pytest.raises(FiwareError):
        await registry.create(NOVA)
    assert registry.list() == []
    assert _conta(conn, "triggers") == 0


@respx.mock
async def test_create_repetido_apos_falha_funciona(registry):
    _mock_cadastro(subscricao=[httpx.Response(500, text="falhou"), CRIADA, CRIADA, CRIADA])
    with pytest.raises(FiwareError):
        await registry.create(NOVA)
    device = await registry.create(NOVA)
    assert registry.list() == [device]


@respx.mock
async def test_create_reprovisiona_device_existente(registry):
    _mock_cadastro(device_existente=True)
    await registry.create(NOVA)
    chamadas = _chamadas()
    remocao = chamadas.index(("DELETE", "/iot/devices/vinheria001"))
    provisionamento = chamadas.index(("POST", "/iot/devices"))
    assert remocao < provisionamento
    comandos = [
        c["name"]
        for c in json.loads(respx.calls[provisionamento].request.content)["devices"][0]["commands"]
    ]
    assert "set_limits" in comandos


@respx.mock
async def test_create_dois_devices_duas_sequencias(registry):
    _mock_cadastro("001")
    _mock_cadastro("002")
    await registry.create(NOVA)
    await registry.create(DeviceCreate(device_id="vinheria002", name="Adega Carioca",
                                       city="Rio de Janeiro"))
    assert _chamadas().count(("POST", "/iot/devices")) == 2
    assert _chamadas().count(("POST", "/v2/subscriptions")) == 6
    assert [d.device_id for d in registry.list()] == ["vinheria001", "vinheria002"]


@respx.mock
async def test_create_corrida_vira_conflito(registry, conn):
    def _outro_cadastro_chega_antes(request):
        """Simula outro cadastro do mesmo id gravando no SQLite no meio do nosso."""
        with conn:
            conn.execute(
                "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
                "VALUES ('vinheria001', ?, 'Outra', 'Outra', '2026-10-07T21:00:00+00:00')",
                (E1,),
            )
        return httpx.Response(204)

    _mock_cadastro(faixa=_outro_cadastro_chega_antes)
    with pytest.raises(DeviceAlreadyExists):
        await registry.create(NOVA)


def test_list_ordenado_por_id(registry, cadastrar):
    cadastrar("003", "Cave Campinas", "Campinas")
    cadastrar("001")
    assert [d.device_id for d in registry.list()] == ["vinheria001", "vinheria003"]


def test_get_inexistente_levanta_not_found(registry):
    with pytest.raises(DeviceNotFound):
        registry.get("vinheria009")


def test_detail_inclui_faixa(registry, cadastrar):
    cadastrar("001")
    detalhe = registry.detail("vinheria001")
    assert detalhe.name == "Vinheria Paulista"
    assert detalhe.limits == DEFAULT_LIMITS
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_device_registry.py -v`
Expected: erro de coleta com `ModuleNotFoundError: No module named 'app.services.device_registry'`.

- [ ] **Passo 4: criar `backend/app/services/registry_errors.py`**

```python
"""
Exceções do cadastro de vinherias.

Como as do FIWARE, não dependem do FastAPI; a tradução para resposta HTTP
fica em app/api/errors.py (404 para "não encontrada", 409 para conflito).
"""


class RegistryError(Exception):
    """Falha de regra do cadastro de vinherias."""
    service = "registry"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DeviceNotFound(RegistryError):
    """O device_id não está cadastrado."""


class DeviceAlreadyExists(RegistryError):
    """O device_id já está cadastrado."""


class VinheriaNotFound(RegistryError):
    """Nenhuma vinheria corresponde ao texto informado (resolver)."""


class AmbiguousVinheria(RegistryError):
    """O texto corresponde a mais de uma vinheria; `options` lista as candidatas."""

    def __init__(self, message: str, options: list):
        super().__init__(message)
        self.options = options
```

- [ ] **Passo 5: criar `backend/app/services/device_registry.py`**

```python
"""
Cadastro de vinherias: SQLite local + provisionamento no FIWARE.

O FIWARE vem primeiro e o SQLite por último. Cada etapa no FIWARE pode ser
repetida sem efeito colateral (409/404 aceitos, subscriptions recriadas),
então, se algo falha no meio, nada fica gravado localmente e basta tentar
de novo. Device que já existe no IoT Agent é removido e provisionado de
novo, para ganhar a configuração completa (inclusive set_limits): o IoT
Agent não deixa acrescentar comandos a um device existente.
"""
import sqlite3
from datetime import datetime, timezone

from app.models.schemas import Device, DeviceCreate, DeviceDetail
from app.services.fiware_client import FiwareClient
from app.services.fiware_constants import ATRIBUTOS_LONGOS
from app.services.limits import DEFAULT_LIMITS, LimitsStore, limits_to_orion_attrs
from app.services.registry_errors import DeviceAlreadyExists, DeviceNotFound

ENTITY_PREFIX = "urn:ngsi-ld:Vinheria:"


def entity_id_for(device_id: str) -> str:
    """Deriva o id da entidade no Orion: vinheria001 -> urn:ngsi-ld:Vinheria:001."""
    return ENTITY_PREFIX + device_id.removeprefix("vinheria")


def _linha_para_device(linha: sqlite3.Row) -> Device:
    """Converte uma linha da tabela devices no modelo Device."""
    return Device(device_id=linha["device_id"], entity_id=linha["entity_id"],
                  name=linha["name"], city=linha["city"], created_at=linha["created_at"])


class DeviceRegistry:
    """Cadastro, consulta e remoção das vinherias."""

    def __init__(self, conn: sqlite3.Connection, fiware: FiwareClient, limits: LimitsStore):
        self._conn = conn
        self._fiware = fiware
        self._limits = limits

    async def create(self, data: DeviceCreate) -> Device:
        """Provisiona a vinheria no FIWARE e só então grava device e faixa no SQLite."""
        if self._exists(data.device_id):
            raise DeviceAlreadyExists(f"{data.device_id} já está cadastrada")
        device = Device(
            device_id=data.device_id,
            entity_id=entity_id_for(data.device_id),
            name=data.name,
            city=data.city,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        await self._fiware.provision_service_group()
        # Remove antes de provisionar: re-provisiona quem já existe (adoção)
        await self._fiware.delete_device(device.device_id)
        await self._fiware.provision_device(device)
        # Recria as subscriptions do STH sem deixar duplicatas
        await self._fiware.delete_subscriptions(device.entity_id)
        for attr in ATRIBUTOS_LONGOS:
            await self._fiware.subscribe_attr(device.entity_id, attr)
        # A entidade já existe logo após o provisionamento (fato F1 da spec)
        await self._fiware.update_attrs(device.entity_id, limits_to_orion_attrs(DEFAULT_LIMITS))
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (device.device_id, device.entity_id, device.name, device.city,
                     device.created_at),
                )
                self._limits.seed_defaults(device.device_id)
        except sqlite3.IntegrityError as exc:
            # Outro cadastro do mesmo id gravou entre a checagem e o INSERT
            raise DeviceAlreadyExists(f"{data.device_id} já está cadastrada") from exc
        return device

    def list(self) -> list[Device]:
        """Todas as vinherias cadastradas, ordenadas pelo id."""
        linhas = self._conn.execute("SELECT * FROM devices ORDER BY device_id")
        return [_linha_para_device(linha) for linha in linhas]

    def get(self, device_id: str) -> Device:
        """Uma vinheria pelo id; DeviceNotFound se não estiver cadastrada."""
        linha = self._conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if linha is None:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        return _linha_para_device(linha)

    def detail(self, device_id: str) -> DeviceDetail:
        """Vinheria com a faixa ideal configurada."""
        device = self.get(device_id)
        return DeviceDetail(**device.model_dump(), limits=self._limits.get(device_id))

    def _exists(self, device_id: str) -> bool:
        """True se o id já está no SQLite."""
        return self._conn.execute(
            "SELECT 1 FROM devices WHERE device_id = ?", (device_id,)).fetchone() is not None
```

- [ ] **Passo 6: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_device_registry.py -v`
Expected: 12 testes `PASSED`.

- [ ] **Passo 7: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q`
Expected: `104 passed`.

- [ ] **Passo 8: commit**

```bash
git add backend/app/services/registry_errors.py backend/app/services/device_registry.py backend/tests/conftest.py backend/tests/test_device_registry.py
git commit -m "feat: adiciona cadastro de vinherias com provisionamento completo no FIWARE"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.4 — Remoção de vinheria (R6)

**Files:**
- Modify: `backend/app/services/device_registry.py` (novo método `delete`)
- Create: `backend/tests/test_device_delete.py`

**Interfaces:**
- Consumes: `DeviceRegistry.get` (3.3); `FiwareClient.delete_subscriptions`, `delete_device`, `delete_entity` (Task 2); fixtures `registry`, `cadastrar`, `conn` (3.3).
- Produces: `DeviceRegistry.delete(device_id) -> None` (async).

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_device_delete.py`:

```python
"""Testes da remoção de vinheria (spec R6)."""
import httpx
import pytest
import respx

from app.services.fiware_errors import FiwareUnavailable
from app.services.registry_errors import DeviceNotFound

pytestmark = pytest.mark.anyio

IOTA = "http://10.0.0.1:4041"
ORION = "http://10.0.0.1:1026"
E1 = "urn:ngsi-ld:Vinheria:001"


def _mock_remocao(device_status=204, entity_status=404):
    """Rotas da remoção da vinheria001, com uma subscription dela (s1) e uma de outra (s2)."""
    assinaturas = [
        {"id": "s1", "subject": {"entities": [{"id": E1, "type": "Vinheria"}]}},
        {"id": "s2", "subject": {"entities": [{"id": "urn:ngsi-ld:Vinheria:002",
                                               "type": "Vinheria"}]}},
    ]
    respx.get(f"{ORION}/v2/subscriptions").mock(return_value=httpx.Response(200, json=assinaturas))
    respx.delete(f"{ORION}/v2/subscriptions/s1").mock(return_value=httpx.Response(204))
    respx.delete(f"{IOTA}/iot/devices/vinheria001").mock(
        return_value=httpx.Response(device_status))
    respx.delete(f"{ORION}/v2/entities/{E1}").mock(return_value=httpx.Response(entity_status))


def _conta(conn, tabela):
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


@respx.mock
async def test_delete_sequencia_e_remove_local(registry, cadastrar, conn):
    cadastrar("001")
    _mock_remocao()
    await registry.delete("vinheria001")
    assert [(c.request.method, c.request.url.path) for c in respx.calls] == [
        ("GET", "/v2/subscriptions"),
        ("DELETE", "/v2/subscriptions/s1"),
        ("DELETE", "/iot/devices/vinheria001"),
        ("DELETE", f"/v2/entities/{E1}"),
    ]
    assert registry.list() == []
    assert _conta(conn, "triggers") == 0


@respx.mock
async def test_delete_aceita_404_no_fiware(registry, cadastrar):
    cadastrar("001")
    _mock_remocao(device_status=404, entity_status=404)
    await registry.delete("vinheria001")
    assert registry.list() == []


@respx.mock
async def test_delete_mantem_alertas(registry, cadastrar, conn):
    cadastrar("001")
    with conn:
        conn.execute("INSERT INTO alerts (device_id, attr, value, opened_at) "
                     "VALUES ('vinheria001', 'temperature', 25.0, '2026-10-07T21:00:00+00:00')")
    _mock_remocao()
    await registry.delete("vinheria001")
    assert _conta(conn, "alerts") == 1


@respx.mock
async def test_delete_fiware_fora_mantem_cadastro(registry, cadastrar):
    device = cadastrar("001")
    respx.get(f"{ORION}/v2/subscriptions").mock(side_effect=httpx.ConnectError("recusada"))
    with pytest.raises(FiwareUnavailable):
        await registry.delete("vinheria001")
    assert registry.list() == [device]


async def test_delete_inexistente_levanta_not_found_sem_rede(registry):
    with respx.mock() as mock:
        with pytest.raises(DeviceNotFound):
            await registry.delete("vinheria009")
    assert mock.calls.call_count == 0
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_device_delete.py -v`
Expected: 5 falhas com `AttributeError: 'DeviceRegistry' object has no attribute 'delete'`.

- [ ] **Passo 3: implementar `delete`**

Em `backend/app/services/device_registry.py`, inserir este método logo depois de `detail` (antes de `_exists`):

```python
    async def delete(self, device_id: str) -> None:
        """Remove a vinheria do FIWARE e depois do SQLite.

        Ordem: subscriptions, device no IoT Agent e entidade no Orion (404
        aceito; remover o device já costuma apagar a entidade). Os triggers
        saem em cascata; os alertas ficam, pois o histórico sobrevive. Se o
        FIWARE falhar, o cadastro local fica para uma nova tentativa.
        """
        device = self.get(device_id)
        await self._fiware.delete_subscriptions(device.entity_id)
        await self._fiware.delete_device(device.device_id)
        await self._fiware.delete_entity(device.entity_id)
        with self._conn:
            self._conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_device_delete.py -v`
Expected: 5 testes `PASSED`.

- [ ] **Passo 5: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q`
Expected: `109 passed`.

- [ ] **Passo 6: commit**

```bash
git add backend/app/services/device_registry.py backend/tests/test_device_delete.py
git commit -m "feat: adiciona remocao de vinheria do FIWARE e do cadastro local"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.5 — Resolver de vinheria por texto (R7)

**Files:**
- Create: `backend/app/services/vinheria_resolver.py`
- Create: `backend/tests/test_vinheria_resolver.py`

**Interfaces:**
- Consumes: `Device` (3.1); `AmbiguousVinheria`, `VinheriaNotFound` (3.3).
- Produces: `normalize_text(texto) -> str`; `resolve_vinheria(texto, devices) -> Device` (consumido pela Task 7A).

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_vinheria_resolver.py`:

```python
"""Testes do resolver de vinheria por id, nome ou cidade (spec R7)."""
import pytest

from app.models.schemas import Device
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound
from app.services.vinheria_resolver import resolve_vinheria


def _device(numero, name, city):
    return Device(device_id=f"vinheria{numero}", entity_id=f"urn:ngsi-ld:Vinheria:{numero}",
                  name=name, city=city)


FROTA = [
    _device("001", "Vinheria Paulista", "São Paulo"),
    _device("002", "Adega Carioca", "Rio de Janeiro"),
    _device("003", "Cave Campinas", "Campinas"),
    _device("004", "Empório do Sul", "São Paulo do Sul"),
]


@pytest.mark.parametrize("texto", ["sao paulo", "SÃO  PAULO", "  são paulo "])
def test_resolve_ignora_acento_e_caixa(texto):
    assert resolve_vinheria(texto, FROTA).device_id == "vinheria001"


def test_resolve_por_id():
    assert resolve_vinheria("Vinheria002", FROTA).device_id == "vinheria002"


def test_resolve_por_cidade_exata():
    assert resolve_vinheria("Campinas", FROTA).device_id == "vinheria003"


def test_resolve_prefere_igualdade_a_trecho():
    # "são paulo do sul" contém "são paulo", mas a igualdade com a cidade da 001 vence
    assert resolve_vinheria("São Paulo", FROTA).device_id == "vinheria001"
    assert resolve_vinheria("são paulo do sul", FROTA).device_id == "vinheria004"


def test_resolve_por_trecho():
    assert resolve_vinheria("rio", FROTA).device_id == "vinheria002"


def test_resolve_ambiguo():
    with pytest.raises(AmbiguousVinheria) as erro:
        resolve_vinheria("vinheria", FROTA)
    assert [d.device_id for d in erro.value.options] == [
        "vinheria001", "vinheria002", "vinheria003", "vinheria004"]


def test_resolve_nao_encontrado():
    with pytest.raises(VinheriaNotFound):
        resolve_vinheria("Recife", FROTA)


@pytest.mark.parametrize("texto", ["", "   "])
def test_resolve_texto_vazio(texto):
    with pytest.raises(VinheriaNotFound):
        resolve_vinheria(texto, FROTA)
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_vinheria_resolver.py -v`
Expected: erro de coleta com `ModuleNotFoundError: No module named 'app.services.vinheria_resolver'`.

- [ ] **Passo 3: criar `backend/app/services/vinheria_resolver.py`**

```python
"""
Resolve uma referência em texto livre ("vinheria de São Paulo", "002") para
a vinheria cadastrada certa. Usado pelo chatbot (Task 7A).

A comparação ignora acentos, caixa e espaços repetidos. A busca vai do mais
preciso ao menos preciso: id exato, nome ou cidade exatos, e por fim trecho
contido no id, nome ou cidade. A primeira etapa com um único resultado
decide; uma etapa com vários resultados é ambígua e pede esclarecimento.
"""
import unicodedata

from app.models.schemas import Device
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound


def normalize_text(texto: str) -> str:
    """Tira acentos, passa para minúsculas e colapsa os espaços."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def _decide(candidatos: list[Device], texto: str) -> Device | None:
    """Um candidato: devolve. Vários: AmbiguousVinheria. Nenhum: None."""
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        opcoes = sorted(candidatos, key=lambda d: d.device_id)
        nomes = ", ".join(f"{d.device_id} ({d.name}, {d.city})" for d in opcoes)
        raise AmbiguousVinheria(f"'{texto}' corresponde a mais de uma vinheria: {nomes}", opcoes)
    return None


def resolve_vinheria(texto: str, devices: list[Device]) -> Device:
    """Encontra a vinheria referida por `texto` entre as cadastradas."""
    alvo = normalize_text(texto)
    if not alvo:
        raise VinheriaNotFound("informe o id, o nome ou a cidade da vinheria")

    def _nome(d: Device) -> str:
        return normalize_text(d.name)

    def _cidade(d: Device) -> str:
        return normalize_text(d.city)

    etapas = (
        lambda d: d.device_id == alvo,
        lambda d: alvo in (_nome(d), _cidade(d)),
        lambda d: alvo in d.device_id or alvo in _nome(d) or alvo in _cidade(d),
    )
    for corresponde in etapas:
        escolhido = _decide([d for d in devices if corresponde(d)], texto)
        if escolhido is not None:
            return escolhido
    raise VinheriaNotFound(f"nenhuma vinheria corresponde a '{texto}'")
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_vinheria_resolver.py -v`
Expected: 11 testes `PASSED`.

- [ ] **Passo 5: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q`
Expected: `120 passed`.

- [ ] **Passo 6: commit**

```bash
git add backend/app/services/vinheria_resolver.py backend/tests/test_vinheria_resolver.py
git commit -m "feat: adiciona resolver de vinheria por id, nome ou cidade"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.6 — Leituras: estado atual, histórico e score (R3.3, R8)

**Files:**
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/services/readings.py`
- Create: `backend/tests/test_readings.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `DeviceRegistry.get` (3.3); `FiwareClient.get_entity`, `query_history` (Task 2); `FiwareNotFound` (Task 2); `ENTITY_TYPE` de `fiware_constants`; `LimitsStore.get` (3.1); `quality_score`, `unavailable_message` (3.2); `CurrentReading`, `AttrScores`, `Limits`.
- Produces: `SensorAttr`, `HistoryPoint`, `HistoryQuery`, `ScoreReport`; `to_float(valor) -> float | None`; `ReadingsService(registry, fiware, limits)` com `async current(device_id) -> CurrentReading`, `async history(device_id, query) -> list[HistoryPoint]`, `async score(device_id) -> ScoreReport`; fixture `readings`.

- [ ] **Passo 1: acrescentar a fixture `readings` ao `conftest.py`**

Import junto dos demais:

```python
from app.services.readings import ReadingsService
```

Ao fim do arquivo:

```python
@pytest.fixture
def readings(registry, fiware, limits):
    """ReadingsService com FIWARE interceptado pelo respx."""
    return ReadingsService(registry, fiware, limits)
```

- [ ] **Passo 2: escrever os testes que falham**

`backend/tests/test_readings.py`:

```python
"""Testes das leituras: estado atual, histórico normalizado e score (spec R3.3, R8)."""
import httpx
import pytest
import respx
from pydantic import ValidationError

from app.models.schemas import HistoryQuery
from app.services.registry_errors import DeviceNotFound

pytestmark = pytest.mark.anyio

ORION = "http://10.0.0.1:1026"
STH = "http://10.0.0.1:8666"
E1 = "urn:ngsi-ld:Vinheria:001"
ENTIDADE_URL = f"{ORION}/v2/entities/{E1}"


def _sth_url(attr="temperature"):
    return f"{STH}/STH/v1/contextEntities/type/Vinheria/id/{E1}/attributes/{attr}"


def _resposta_sth(valores, attr="temperature"):
    """Resposta no formato do STH-Comet com os valores dados."""
    return {"contextResponses": [{
        "contextElement": {"attributes": [{"name": attr, "values": valores}],
                           "id": E1, "isPattern": False, "type": "Vinheria"},
        "statusCode": {"code": "200", "reasonPhrase": "OK"},
    }]}


def _entidade(**attrs):
    """Entidade em keyValues como o Orion devolve, com atributos de comando junto."""
    return {"id": E1, "type": "Vinheria", "blink_temp": "", "set_limits": "", **attrs}


@respx.mock
async def test_current_converte_valores(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(
        temperature=14.2, humidity="55.5", luminosity=12,
        TimeInstant="2026-10-07T21:00:00.000Z")))
    leitura = await readings.current("vinheria001")
    assert (leitura.temperature, leitura.humidity, leitura.luminosity) == (14.2, 55.5, 12.0)
    assert leitura.time_instant == "2026-10-07T21:00:00.000Z"


@respx.mock
async def test_current_sem_atributos_de_sensor(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade()))
    leitura = await readings.current("vinheria001")
    assert (leitura.temperature, leitura.humidity, leitura.luminosity) == (None, None, None)
    assert leitura.time_instant is None


@pytest.mark.parametrize("valor", ["", " ", True, "abc", "NaN"])
@respx.mock
async def test_current_valor_invalido_vira_nulo(readings, cadastrar, valor):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(
        temperature=valor, humidity=60, luminosity=10)))
    leitura = await readings.current("vinheria001")
    assert leitura.temperature is None
    assert leitura.humidity == 60


@respx.mock
async def test_current_entidade_inexistente_devolve_nulos(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(404, json={"error": "NotFound"}))
    leitura = await readings.current("vinheria001")
    assert leitura.device_id == "vinheria001"
    assert (leitura.temperature, leitura.humidity, leitura.luminosity) == (None, None, None)


@respx.mock
async def test_history_normaliza_pontos(readings, cadastrar):
    cadastrar("001")
    rota = respx.get(_sth_url()).mock(return_value=httpx.Response(200, json=_resposta_sth([
        {"recvTime": "2026-10-07T21:00:00.000Z", "attrType": "Float", "attrValue": "14.2"},
        {"recvTime": "2026-10-07T21:00:02.000Z", "attrType": "Float", "attrValue": 14.3},
    ])))
    pontos = await readings.history("vinheria001", HistoryQuery(attr="temperature", last_n=20))
    assert [p.model_dump() for p in pontos] == [
        {"ts": "2026-10-07T21:00:00.000Z", "value": 14.2},
        {"ts": "2026-10-07T21:00:02.000Z", "value": 14.3},
    ]
    assert rota.calls.last.request.url.params["lastN"] == "20"


@respx.mock
async def test_history_descarta_nao_numericos(readings, cadastrar):
    cadastrar("001")
    respx.get(_sth_url()).mock(return_value=httpx.Response(200, json=_resposta_sth([
        {"recvTime": "2026-10-07T21:00:00.000Z", "attrValue": " "},
        {"recvTime": "2026-10-07T21:00:02.000Z", "attrValue": "14.3"},
    ])))
    pontos = await readings.history("vinheria001", HistoryQuery(attr="temperature", last_n=20))
    assert [p.value for p in pontos] == [14.3]


@respx.mock
async def test_history_repassa_janela_de_datas(readings, cadastrar):
    cadastrar("001")
    rota = respx.get(_sth_url("humidity")).mock(
        return_value=httpx.Response(200, json=_resposta_sth([], "humidity")))
    consulta = HistoryQuery(attr="humidity", date_from="2026-10-07T00:00:00",
                            date_to="2026-10-07T23:59:59")
    assert await readings.history("vinheria001", consulta) == []
    params = rota.calls.last.request.url.params
    assert params["dateFrom"] == "2026-10-07T00:00:00"
    assert params["dateTo"] == "2026-10-07T23:59:59"


@respx.mock
async def test_score_usa_faixa_da_vinheria(readings, cadastrar, conn):
    cadastrar("001")
    with conn:
        conn.execute("UPDATE triggers SET min_value = 18, max_value = 25 "
                     "WHERE device_id = 'vinheria001' AND attr = 'temperature'")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(
        temperature=20, humidity=60, luminosity=10)))
    relatorio = await readings.score("vinheria001")
    assert relatorio.score == 100
    assert relatorio.available is True
    assert relatorio.message is None
    assert (relatorio.limits.temperature.min, relatorio.limits.temperature.max) == (18, 25)


@respx.mock
async def test_score_indisponivel_no_report(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(temperature=15)))
    relatorio = await readings.score("vinheria001")
    assert relatorio.score is None
    assert relatorio.available is False
    assert relatorio.message == "Score indisponível: aguardando leitura de umidade e luminosidade"
    assert relatorio.attrs.temperature == 100


async def test_readings_device_inexistente_sem_rede(readings):
    with respx.mock() as mock:
        with pytest.raises(DeviceNotFound):
            await readings.current("vinheria009")
        with pytest.raises(DeviceNotFound):
            await readings.history("vinheria009", HistoryQuery(attr="temperature", last_n=5))
        with pytest.raises(DeviceNotFound):
            await readings.score("vinheria009")
    assert mock.calls.call_count == 0


@pytest.mark.parametrize("campos", [
    {"attr": "temperature"},
    {"attr": "temperature", "last_n": 10, "date_from": "2026-10-07T00:00:00"},
])
def test_history_query_exige_um_modo(campos):
    with pytest.raises(ValidationError):
        HistoryQuery(**campos)


def test_history_query_valida_data():
    with pytest.raises(ValidationError):
        HistoryQuery(attr="temperature", date_from="ontem")
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_readings.py -v`
Expected: erro de coleta com `ModuleNotFoundError: No module named 'app.services.readings'` (ou `ImportError` de `HistoryQuery`).

- [ ] **Passo 4: acrescentar os schemas a `backend/app/models/schemas.py`**

No topo, junto dos imports:

```python
from datetime import datetime
from typing import Literal
```

Logo abaixo das constantes `_PORTA`, `_POLL`, `_OFFLINE`:

```python
# Atributos de sensor aceitos no histórico e no score (nomes longos do Orion/STH)
SensorAttr = Literal["temperature", "humidity", "luminosity"]
```

Ao fim do arquivo:

```python
class HistoryPoint(BaseModel):
    """Um ponto do histórico, já normalizado a partir do STH-Comet."""
    ts: str
    value: float


class HistoryQuery(BaseModel):
    """Janela de consulta do histórico: OU last_n OU intervalo de datas (ISO 8601)."""
    attr: SensorAttr
    last_n: int | None = Field(default=None, ge=1, le=500)
    date_from: str | None = None
    date_to: str | None = None

    @field_validator("date_from", "date_to")
    @classmethod
    def _data_iso(cls, valor: str | None) -> str | None:
        """Aceita só datas ISO 8601 (ex.: 2026-10-07T00:00:00)."""
        if valor is None:
            return None
        try:
            datetime.fromisoformat(valor)
        except ValueError as exc:
            raise ValueError("data deve estar em ISO 8601, ex.: 2026-10-07T00:00:00") from exc
        return valor

    @model_validator(mode="after")
    def _um_modo(self) -> "HistoryQuery":
        """Exige exatamente um modo de janela."""
        por_datas = self.date_from is not None or self.date_to is not None
        if self.last_n is None and not por_datas:
            raise ValueError("informe last_n ou date_from/date_to")
        if self.last_n is not None and por_datas:
            raise ValueError("use last_n ou date_from/date_to, não os dois")
        return self


class ScoreReport(BaseModel):
    """Score de qualidade de uma vinheria; com score None, `message` explica o motivo."""
    device_id: str
    score: float | None
    available: bool
    message: str | None = None
    attrs: AttrScores
    limits: Limits
```

- [ ] **Passo 5: criar `backend/app/services/readings.py`**

```python
"""
Leituras de uma vinheria: estado atual (Orion), histórico (STH-Comet) e score.

Normaliza o que vem do FIWARE: valores viram float (ou None quando ausentes
ou inválidos) e o histórico vira [{ts, value}]. Vinheria recém-cadastrada
ainda não tem atributos de sensor no Orion; isso aparece como None, não
como erro.
"""
import math

from app.models.schemas import CurrentReading, HistoryPoint, HistoryQuery, ScoreReport
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fiware_constants import ENTITY_TYPE
from app.services.fiware_errors import FiwareNotFound
from app.services.limits import LimitsStore
from app.services.quality_score import quality_score, unavailable_message


def to_float(valor) -> float | None:
    """Converte um valor do FIWARE para float; None se ausente ou inválido.

    O Orion pode mandar número, texto ("14.2"), vazio (" ") ou outro tipo;
    booleanos, NaN e infinito também viram None.
    """
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if math.isnan(numero) or math.isinf(numero):
        return None
    return numero


class ReadingsService:
    """Consulta de estado atual, histórico e score por vinheria."""

    def __init__(self, registry: DeviceRegistry, fiware: FiwareClient, limits: LimitsStore):
        self._registry = registry
        self._fiware = fiware
        self._limits = limits

    async def current(self, device_id: str) -> CurrentReading:
        """Estado atual no Orion; sem entidade ou sem leitura, valores None."""
        device = self._registry.get(device_id)
        try:
            entidade = await self._fiware.get_entity(device.entity_id)
        except FiwareNotFound:
            entidade = {}
        instante = entidade.get("TimeInstant")
        return CurrentReading(
            device_id=device.device_id,
            temperature=to_float(entidade.get("temperature")),
            humidity=to_float(entidade.get("humidity")),
            luminosity=to_float(entidade.get("luminosity")),
            time_instant=instante if isinstance(instante, str) and instante.strip() else None,
        )

    async def history(self, device_id: str, query: HistoryQuery) -> list[HistoryPoint]:
        """Histórico de um atributo, normalizado e sem pontos inválidos."""
        device = self._registry.get(device_id)
        brutos = await self._fiware.query_history(
            ENTITY_TYPE, device.entity_id, query.attr,
            last_n=query.last_n, date_from=query.date_from, date_to=query.date_to,
        )
        pontos = []
        for ponto in brutos:
            valor = to_float(ponto.get("attrValue"))
            instante = ponto.get("recvTime")
            if valor is not None and isinstance(instante, str):
                pontos.append(HistoryPoint(ts=instante, value=valor))
        return pontos

    async def score(self, device_id: str) -> ScoreReport:
        """Score atual com a faixa daquela vinheria e, se indisponível, o motivo."""
        leitura = await self.current(device_id)
        limites = self._limits.get(device_id)
        nota, notas = quality_score(leitura, limites)
        return ScoreReport(
            device_id=device_id,
            score=nota,
            available=nota is not None,
            message=unavailable_message(notas),
            attrs=notas,
            limits=limites,
        )
```

- [ ] **Passo 6: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_readings.py -v`
Expected: 17 testes `PASSED`.

- [ ] **Passo 7: rodar a suíte inteira e conferir tamanhos**

Run: `.venv/Scripts/python -m pytest -q` e depois `wc -l app/models/schemas.py app/services/*.py`
Expected: `137 passed`; nenhum arquivo acima de ~250 linhas (o `schemas.py` deve ficar perto de 200). Se passar, **não divida por conta própria**: reporte.

- [ ] **Passo 8: commit**

```bash
git add backend/app/models/schemas.py backend/app/services/readings.py backend/tests/conftest.py backend/tests/test_readings.py
git commit -m "feat: adiciona leitura de estado atual, historico normalizado e score"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.7 — Rotas de vinherias e de dados (R9)

**Files:**
- Modify: `backend/app/api/deps.py`, `backend/app/api/errors.py`, `backend/app/main.py`
- Create: `backend/app/api/routes_devices.py`, `backend/app/api/routes_data.py`
- Create: `backend/tests/test_routes_devices.py`

**Interfaces:**
- Consumes: `DeviceRegistry` (3.3, 3.4); `ReadingsService` (3.6); `LimitsStore` (3.1); erros de `registry_errors` (3.3); schemas de 3.1, 3.2 e 3.6; `create_app` (Task 2).
- Produces: `get_registry(request)`, `get_readings(request)`; `app.state.limits`, `app.state.registry`, `app.state.readings`; as 7 rotas da spec §4.4.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_routes_devices.py`:

```python
"""Testes das rotas de vinherias e de dados (spec R9).

As rotas são testadas com services falsos: aqui importa o contrato HTTP
(status, formato, tradução de erros). A lógica está coberta nos testes
de cada service.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.schemas import (
    AttrScores,
    CurrentReading,
    Device,
    DeviceDetail,
    HistoryPoint,
    ScoreReport,
)
from app.services.fiware_errors import FiwareUnavailable
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import (
    AmbiguousVinheria,
    DeviceAlreadyExists,
    DeviceNotFound,
    VinheriaNotFound,
)

DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria Paulista", city="São Paulo",
                created_at="2026-10-07T21:00:00+00:00")
INSTANTE = "2026-10-07T21:00:00.000Z"


class RegistryFalso:
    """Substitui o DeviceRegistry nos testes de rota."""

    def __init__(self):
        self.criados = []
        self.removidos = []
        self.erro = None

    async def create(self, data):
        if self.erro:
            raise self.erro
        self.criados.append(data)
        return DEVICE.model_copy(update={"device_id": data.device_id, "name": data.name,
                                         "city": data.city})

    def list(self):
        return [DEVICE]

    def detail(self, device_id):
        if device_id != DEVICE.device_id:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        return DeviceDetail(**DEVICE.model_dump(), limits=DEFAULT_LIMITS)

    async def delete(self, device_id):
        if device_id != DEVICE.device_id:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        self.removidos.append(device_id)


class ReadingsFalso:
    """Substitui o ReadingsService nos testes de rota."""

    def __init__(self):
        self.consultas = []

    async def current(self, device_id):
        return CurrentReading(device_id=device_id, temperature=14.5, humidity=60.0,
                              luminosity=10.0, time_instant=INSTANTE)

    async def history(self, device_id, query):
        self.consultas.append(query)
        return [HistoryPoint(ts=INSTANTE, value=14.5)]

    async def score(self, device_id):
        return ScoreReport(device_id=device_id, score=100.0, available=True, message=None,
                           attrs=AttrScores(temperature=100, humidity=100, luminosity=100),
                           limits=DEFAULT_LIMITS)


@pytest.fixture
def app(tmp_path):
    aplicacao = create_app(Settings(fiware_host="10.0.0.1",
                                    database_path=str(tmp_path / "rotas.db")))
    aplicacao.state.registry = RegistryFalso()
    aplicacao.state.readings = ReadingsFalso()
    return aplicacao


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


def test_post_device_201(client, app):
    resposta = client.post("/api/devices", json={
        "device_id": "vinheria003", "name": " Cave Campinas ", "city": "Campinas"})
    assert resposta.status_code == 201
    assert resposta.json()["device_id"] == "vinheria003"
    assert app.state.registry.criados[0].name == "Cave Campinas"


def test_post_device_invalido_422(client, app):
    assert client.post("/api/devices", json={
        "device_id": "vinheria1", "name": "X", "city": "Y"}).status_code == 422
    assert client.post("/api/devices", json={
        "device_id": "vinheria003", "name": "", "city": "Y"}).status_code == 422
    assert app.state.registry.criados == []


def test_post_device_fiware_fora_503(client, app):
    app.state.registry.erro = FiwareUnavailable("iota", "sem conexão")
    resposta = client.post("/api/devices", json={
        "device_id": "vinheria003", "name": "Cave", "city": "Campinas"})
    assert resposta.status_code == 503
    assert resposta.json() == {"detail": "sem conexão", "service": "iota"}


def test_get_devices_lista(client):
    resposta = client.get("/api/devices")
    assert resposta.status_code == 200
    assert [d["device_id"] for d in resposta.json()] == ["vinheria001"]


def test_get_device_detalhe(client):
    resposta = client.get("/api/devices/vinheria001")
    assert resposta.status_code == 200
    assert resposta.json()["limits"]["temperature"] == {"min": 12.0, "max": 18.0}
    inexistente = client.get("/api/devices/vinheria009")
    assert inexistente.status_code == 404
    assert inexistente.json()["service"] == "registry"


def test_delete_device_204(client, app):
    resposta = client.delete("/api/devices/vinheria001")
    assert resposta.status_code == 204
    assert app.state.registry.removidos == ["vinheria001"]
    assert client.delete("/api/devices/vinheria009").status_code == 404


def test_get_current(client):
    resposta = client.get("/api/devices/vinheria001/current")
    assert resposta.status_code == 200
    assert resposta.json()["temperature"] == 14.5
    assert resposta.json()["time_instant"] == INSTANTE


def test_get_history_last_n(client, app):
    resposta = client.get("/api/devices/vinheria001/history?attr=temperature&last_n=20")
    assert resposta.status_code == 200
    assert resposta.json() == [{"ts": INSTANTE, "value": 14.5}]
    consulta = app.state.readings.consultas[0]
    assert (consulta.attr, consulta.last_n) == ("temperature", 20)


def test_get_history_por_datas(client, app):
    resposta = client.get("/api/devices/vinheria001/history?attr=humidity"
                          "&date_from=2026-10-07T00:00:00&date_to=2026-10-07T23:59:59")
    assert resposta.status_code == 200
    consulta = app.state.readings.consultas[0]
    assert (consulta.date_from, consulta.date_to) == ("2026-10-07T00:00:00", "2026-10-07T23:59:59")


@pytest.mark.parametrize("query", [
    "attr=temperature",
    "attr=temperature&last_n=10&date_from=2026-10-07T00:00:00",
    "attr=pressure&last_n=10",
    "attr=temperature&last_n=0",
    "attr=temperature&last_n=501",
    "attr=temperature&date_from=ontem",
])
def test_get_history_janela_invalida_422(client, query):
    assert client.get(f"/api/devices/vinheria001/history?{query}").status_code == 422


def test_get_score(client):
    resposta = client.get("/api/devices/vinheria001/score")
    assert resposta.status_code == 200
    assert resposta.json()["available"] is True
    assert resposta.json()["score"] == 100.0


@pytest.mark.parametrize("erro, status", [
    (DeviceNotFound("não existe"), 404),
    (VinheriaNotFound("ninguém"), 404),
    (DeviceAlreadyExists("já existe"), 409),
    (AmbiguousVinheria("várias", []), 409),
])
def test_handler_traduz_erros_de_dominio(app, erro, status):
    async def rota_que_falha():
        raise erro

    app.add_api_route("/teste-erro-registry", rota_que_falha)
    with TestClient(app) as cliente:
        resposta = cliente.get("/teste-erro-registry")
    assert resposta.status_code == status
    assert resposta.json() == {"detail": erro.message, "service": "registry"}
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_routes_devices.py -v`
Expected: falhas com status 404 nas rotas (ainda não existem) e, nos 4 casos de `test_handler_traduz_erros_de_dominio`, a própria exceção de domínio propagada pelo `TestClient` (ainda não há tradutor). Nenhum erro de coleta.

- [ ] **Passo 3: ampliar `backend/app/api/deps.py`**

Acrescentar aos imports:

```python
from app.services.device_registry import DeviceRegistry
from app.services.readings import ReadingsService
```

E ao fim do arquivo:

```python
def get_registry(request: Request) -> DeviceRegistry:
    """Cadastro de vinherias da aplicação."""
    return request.app.state.registry


def get_readings(request: Request) -> ReadingsService:
    """Serviço de leituras da aplicação."""
    return request.app.state.readings
```

- [ ] **Passo 4: ampliar `backend/app/api/errors.py`**

Atualizar a docstring do módulo:

```python
"""
Tradução das exceções dos services em respostas HTTP.

FiwareError (falhas do FIWARE) e RegistryError (regras do cadastro) viram
JSON { "detail", "service" } com um status coerente, para o front-end
mostrar uma mensagem clara em vez de um erro 500 genérico.
"""
```

Acrescentar aos imports:

```python
from app.services.registry_errors import (
    AmbiguousVinheria,
    DeviceAlreadyExists,
    RegistryError,
)
```

Acrescentar, depois de `_status_para`:

```python
def _status_registry(erro: RegistryError) -> int:
    """Conflito de cadastro ou referência ambígua dão 409; o resto é 'não encontrado'."""
    if isinstance(erro, (DeviceAlreadyExists, AmbiguousVinheria)):
        return 409
    return 404
```

E, dentro de `register_error_handlers`, depois do handler de `FiwareError`:

```python
    @app.exception_handler(RegistryError)
    async def _trata_registry(request: Request, erro: RegistryError) -> JSONResponse:
        return JSONResponse(status_code=_status_registry(erro),
                            content={"detail": erro.message, "service": erro.service})
```

- [ ] **Passo 5: criar `backend/app/api/routes_devices.py`**

```python
"""
Rotas do cadastro de vinherias: cadastrar (com provisionamento no FIWARE),
listar, consultar com a faixa ideal e remover.
"""
from fastapi import APIRouter, Depends, Response

from app.api.deps import get_registry
from app.models.schemas import Device, DeviceCreate, DeviceDetail
from app.services.device_registry import DeviceRegistry

router = APIRouter(prefix="/api/devices", tags=["vinherias"])


@router.post("", response_model=Device, status_code=201)
async def create_device(data: DeviceCreate,
                        registry: DeviceRegistry = Depends(get_registry)) -> Device:
    """Cadastra a vinheria e a provisiona no FIWARE (re-provisiona se já existir lá)."""
    return await registry.create(data)


@router.get("", response_model=list[Device])
def list_devices(registry: DeviceRegistry = Depends(get_registry)) -> list[Device]:
    """Vinherias cadastradas, ordenadas pelo id."""
    return registry.list()


@router.get("/{device_id}", response_model=DeviceDetail)
def read_device(device_id: str,
                registry: DeviceRegistry = Depends(get_registry)) -> DeviceDetail:
    """Uma vinheria com a faixa ideal configurada."""
    return registry.detail(device_id)


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: str,
                        registry: DeviceRegistry = Depends(get_registry)) -> Response:
    """Remove a vinheria do FIWARE e do cadastro local (o histórico do STH fica)."""
    await registry.delete(device_id)
    return Response(status_code=204)
```

- [ ] **Passo 6: criar `backend/app/api/routes_data.py`**

```python
"""
Rotas de dados de uma vinheria: estado atual, histórico e score de qualidade.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_readings
from app.models.schemas import CurrentReading, HistoryPoint, HistoryQuery, ScoreReport
from app.services.readings import ReadingsService

router = APIRouter(prefix="/api/devices", tags=["dados"])


@router.get("/{device_id}/current", response_model=CurrentReading)
async def read_current(device_id: str,
                       readings: ReadingsService = Depends(get_readings)) -> CurrentReading:
    """Valores atuais; null quando a vinheria ainda não mandou leitura."""
    return await readings.current(device_id)


@router.get("/{device_id}/history", response_model=list[HistoryPoint])
async def read_history(device_id: str, query: Annotated[HistoryQuery, Query()],
                       readings: ReadingsService = Depends(get_readings)) -> list[HistoryPoint]:
    """Histórico de um atributo: last_n (1–500) ou date_from/date_to."""
    return await readings.history(device_id, query)


@router.get("/{device_id}/score", response_model=ScoreReport)
async def read_score(device_id: str,
                     readings: ReadingsService = Depends(get_readings)) -> ScoreReport:
    """Score de qualidade (0–100); se indisponível, traz o motivo em `message`."""
    return await readings.score(device_id)
```

- [ ] **Passo 7: ligar os services e as rotas em `backend/app/main.py`**

Trocar o import das rotas:

```python
from app.api import routes_config, routes_data, routes_devices
```

Acrescentar aos imports:

```python
from app.services.device_registry import DeviceRegistry
from app.services.limits import LimitsStore
from app.services.readings import ReadingsService
```

Atualizar a primeira frase da docstring do módulo para: `create_app() monta a aplicação: lê a configuração, abre o SQLite, cria o cliente FIWARE e os services de cadastro e leituras, e registra CORS, tradução de erros e rotas.`

Em `create_app`, trocar a linha `app.state.fiware = FiwareClient(store, settings)` por:

```python
    fiware = FiwareClient(store, settings)
    limits = LimitsStore(conn)
    registry = DeviceRegistry(conn, fiware, limits)
    app.state.fiware = fiware
    app.state.limits = limits
    app.state.registry = registry
    app.state.readings = ReadingsService(registry, fiware, limits)
```

E, depois de `app.include_router(routes_config.router)`:

```python
    app.include_router(routes_devices.router)
    app.include_router(routes_data.router)
```

- [ ] **Passo 8: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_routes_devices.py -v`
Expected: 20 testes `PASSED`. Se algum caso de `test_get_history_janela_invalida_422` der 500 em vez de 422, **pare e reporte** a resposta (o modelo de query do FastAPI é o ponto sensível; não troque a abordagem por conta própria).

- [ ] **Passo 9: rodar a suíte inteira e conferir camadas**

Run: `.venv/Scripts/python -m pytest -q` e depois `grep -n "import httpx\|FiwareClient" app/api/routes_devices.py app/api/routes_data.py`
Expected: `157 passed`; o `grep` não encontra nada (rotas não falam com o FIWARE direto).

- [ ] **Passo 10: commit**

```bash
git add backend/app/api backend/app/main.py backend/tests/test_routes_devices.py
git commit -m "feat: adiciona rotas de cadastro, historico e score das vinherias"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.7a — Faixa publicada com upsert real no Orion (correção; F4, R4.2, Task 2 R7.5)

> **Correção de 07/10/2026**, nascida da primeira tentativa da 3.8. Na EC2, logo após o provisionamento, `POST /v2/entities/<id>/attrs` respondeu **404** (3 de 3 rodadas, com e sem `?type=`), embora o `GET` da entidade respondesse 200. A entidade só fica armazenada no Orion depois da primeira leitura; antes disso o `GET` é atendido pela registration do IoT Agent. Já `POST /v2/op/update` com `actionType: append` respondeu 204, criou a entidade mantendo os atributos de comando e aceitou repetição (spec F4). O `update_attrs` da Task 2 passa a usar esse upsert.

**Files:**
- Modify: `backend/app/services/fiware_orion.py` (método `update_attrs`)
- Modify: `backend/tests/test_fiware_orion.py` (troca `test_update_attrs_envia_post`)
- Modify: `backend/tests/test_device_registry.py` (rota e corpo da faixa)

**Interfaces:**
- Consumes: `FiwareBase._request`, `orion_url`; `ENTITY_TYPE` (já importado em `fiware_orion.py`).
- Produces: `update_attrs(entity_id, attrs) -> None` com a **mesma assinatura**, agora via `POST /v2/op/update` (`append`). Nenhum chamador muda.

- [ ] **Passo 1: trocar o teste do cliente (vermelho)**

Em `backend/tests/test_fiware_orion.py`, substituir a função `test_update_attrs_envia_post` inteira por:

```python
@respx.mock
async def test_update_attrs_usa_op_update_append(fiware):
    rota = respx.post(f"{ORION}/v2/op/update").mock(return_value=httpx.Response(204))
    await fiware.update_attrs(E1, {"temp_min": 12, "temp_max": 18.5})
    assert _corpo(rota) == {"actionType": "append", "entities": [{
        "id": E1, "type": "Vinheria",
        "temp_min": {"type": "Number", "value": 12},
        "temp_max": {"type": "Number", "value": 18.5},
    }]}
```

- [ ] **Passo 2: ajustar os testes do cadastro (vermelho)**

Em `backend/tests/test_device_registry.py`:

(a) Em `_mock_cadastro`, apagar a linha `entidade = f"urn:ngsi-ld:Vinheria:{numero}"` e trocar a linha da rota da faixa por:

```python
    rota_faixa = respx.post(f"{ORION}/v2/op/update")
```

(b) Em `test_create_sequencia_completa_no_fiware`, trocar o último item da lista esperada `("POST", f"/v2/entities/{E1}/attrs"),` por:

```python
        ("POST", "/v2/op/update"),
```

e trocar o bloco final `faixa = json.loads(...)` / `assert faixa == {...}` por:

```python
    faixa = json.loads(respx.calls[-1].request.content)
    assert faixa == {"actionType": "append", "entities": [{
        "id": E1, "type": "Vinheria",
        "temp_min": {"type": "Number", "value": 12},
        "temp_max": {"type": "Number", "value": 18},
        "hum_min": {"type": "Number", "value": 50},
        "hum_max": {"type": "Number", "value": 70},
        "lux_min": {"type": "Number", "value": 0},
        "lux_max": {"type": "Number", "value": 30},
    }]}
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_orion.py tests/test_device_registry.py -q`
Expected: falhas em `test_update_attrs_usa_op_update_append` e nos testes de cadastro que passam pela faixa (o código ainda chama `/v2/entities/<id>/attrs`, rota não registrada no respx). Nenhum erro de coleta.

- [ ] **Passo 4: implementar o upsert em `backend/app/services/fiware_orion.py`**

Substituir o método `update_attrs` inteiro por:

```python
    async def update_attrs(self, entity_id: str, attrs: dict[str, float]) -> None:
        """Cria ou atualiza atributos numéricos na entidade (ex.: faixa ideal).

        Usa POST /v2/op/update com actionType append, que cria a entidade se
        ela ainda não estiver armazenada. Logo após o provisionamento, a
        entidade só existe pela registration do IoT Agent até a primeira
        leitura, e POST /v2/entities/<id>/attrs responde 404 (verificado na
        EC2 em 07/10/2026). Repetir a chamada é seguro.
        """
        entidade = {"id": entity_id, "type": ENTITY_TYPE}
        entidade.update(
            {nome: {"type": "Number", "value": valor} for nome, valor in attrs.items()})
        await self._request("orion", "POST", self.orion_url("/v2/op/update"),
                            json={"actionType": "append", "entities": [entidade]})
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_orion.py tests/test_device_registry.py -q`
Expected: `21 passed` (9 do Orion + 12 do cadastro).

- [ ] **Passo 6: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q`
Expected: `158 passed`.

- [ ] **Passo 7: commit**

```bash
git add backend/app/services/fiware_orion.py backend/tests/test_fiware_orion.py backend/tests/test_device_registry.py
git commit -m "fix: publica faixa no Orion por op/update append antes da primeira leitura"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.7b — Re-provisionamento resistente ao ESP32 ligado (correção; F5, R4.7)

> **Correção de 07/10/2026.** Ao adotar a 001 e a 002 com o Wokwi publicando a cada 2 s, uma leitura pode chegar entre o `DELETE` e o `POST` do device. Se o service group autoprovisiona (padrão provável do IoT Agent, **não verificado**), o IoT Agent recria o device sozinho e o `POST /iot/devices` responde 409. O cadastro passa a remover e provisionar de novo **uma vez**; um segundo 409 propaga. A entidade lixo do autoprovisionamento some junto com o device (fato F2).

**Files:**
- Modify: `backend/app/services/device_registry.py` (novo `_provisionar`; `create` passa a usá-lo)
- Modify: `backend/tests/test_device_registry.py` (helper ganha `provisionamento`; 2 testes novos)

**Interfaces:**
- Consumes: `FiwareClient.delete_device`, `provision_device`; `FiwareConflict` (Task 2).
- Produces: `DeviceRegistry._provisionar(device) -> None` (interno). Nenhum contrato público muda.

- [ ] **Passo 1: dar ao helper de testes a opção de trocar a resposta do provisionamento**

Em `backend/tests/test_device_registry.py`, trocar a assinatura e a docstring de `_mock_cadastro` por:

```python
def _mock_cadastro(numero="001", device_existente=False, subscricao=None, faixa=None,
                   provisionamento=None):
    """Registra no respx todas as rotas do cadastro de uma vinheria.

    `subscricao`, `faixa` e `provisionamento` permitem trocar a resposta (ou
    side_effect) do POST de subscriptions, do upsert da faixa no Orion e do
    POST do device no IoT Agent.
    """
```

e trocar a linha `respx.post(f"{IOTA}/iot/devices").mock(return_value=httpx.Response(201))` por:

```python
    rota_device = respx.post(f"{IOTA}/iot/devices")
    if provisionamento is None:
        rota_device.mock(return_value=httpx.Response(201))
    else:
        rota_device.mock(side_effect=provisionamento)
```

- [ ] **Passo 2: escrever os testes que falham**

No import de erros do topo de `backend/tests/test_device_registry.py`, trocar `from app.services.fiware_errors import FiwareError` por:

```python
from app.services.fiware_errors import FiwareConflict, FiwareError
```

E acrescentar, logo depois de `test_create_reprovisiona_device_existente`:

```python
DUPLICADO = httpx.Response(409, json={"name": "DUPLICATE_DEVICE_ID"})


@respx.mock
async def test_create_device_autoprovisionado_no_meio_tenta_de_novo(registry):
    _mock_cadastro(device_existente=True, provisionamento=[DUPLICADO, httpx.Response(201)])
    await registry.create(NOVA)
    assert _chamadas()[1:5] == [
        ("DELETE", "/iot/devices/vinheria001"),
        ("POST", "/iot/devices"),
        ("DELETE", "/iot/devices/vinheria001"),
        ("POST", "/iot/devices"),
    ]
    assert [d.device_id for d in registry.list()] == ["vinheria001"]


@respx.mock
async def test_create_conflito_persistente_propaga(registry):
    _mock_cadastro(device_existente=True, provisionamento=[DUPLICADO, DUPLICADO])
    with pytest.raises(FiwareConflict):
        await registry.create(NOVA)
    assert registry.list() == []
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_device_registry.py -q`
Expected: os 2 testes novos falham com `FiwareConflict` (o código ainda não tenta de novo); os outros 12 passam.

- [ ] **Passo 4: implementar em `backend/app/services/device_registry.py`**

(a) No import de erros do FIWARE, acrescentar (o arquivo ainda não importa nada de `fiware_errors`):

```python
from app.services.fiware_errors import FiwareConflict
```

(b) Em `create`, trocar a linha `await self._fiware.provision_device(device)` por:

```python
        await self._provisionar(device)
```

(c) Inserir este método logo antes de `_exists`:

```python
    async def _provisionar(self, device: Device) -> None:
        """Provisiona o device; se o IoT Agent já o recriou sozinho, tenta de novo uma vez.

        Com o ESP32 ligado, uma leitura pode chegar entre a remoção e o
        provisionamento, e o IoT Agent autoprovisiona o device (409). Remover
        de novo e provisionar resolve; um segundo 409 propaga.
        """
        try:
            await self._fiware.provision_device(device)
        except FiwareConflict:
            await self._fiware.delete_device(device.device_id)
            await self._fiware.provision_device(device)
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_device_registry.py -q`
Expected: `14 passed`.

- [ ] **Passo 6: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q`
Expected: `160 passed`.

- [ ] **Passo 7: commit**

```bash
git add backend/app/services/device_registry.py backend/tests/test_device_registry.py
git commit -m "fix: refaz provisionamento quando o IoT Agent recria o device no meio do cadastro"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 3.8 — Verificação real contra a EC2 e fechamento

**Requisitos:** EC2 ligada com os containers de pé; `backend/.env` com `FIWARE_HOST`; Wokwi da `vinheria001` e da `vinheria002` rodando. Nomes informados pelo usuário em 07/10/2026:
- `vinheria001`: **Vinheria Paulista**, **São Paulo**;
- `vinheria002`: **Vinheria Mineira**, **Minas Gerais**.

**Files:**
- Modify: `PLANO-CP5-VINHERIA.md` (marcar a Task 3), `README.md` (roadmap)

**Lições da primeira tentativa (valem para todos os passos):**
- **Nunca** passar JSON inline com `curl -d '...'` no Git Bash do Windows: deu `400 There was an error parsing the body`. Gravar o corpo num arquivo do scratchpad com Python (`json.dump(..., ensure_ascii=True)`, que escreve `São` como `São`) e enviar com `--data-binary @arquivo`.
- Em scripts próprios, **não** mandar `Content-Type` em `GET` nem em `DELETE` sem corpo: o Orion responde 400.
- `H` abaixo resume `-H "fiware-service: smart" -H "fiware-servicepath: /"`, e `IP` é o `FIWARE_HOST` do `.env`.

- [ ] **Passo 1: estado de partida**

Run:
```bash
curl -s $H "http://IP:1026/v2/entities?type=Vinheria&options=keyValues&attrs=temperature,TimeInstant"
curl -s $H "http://IP:1026/v2/entities?type=Thing&options=keyValues"
```
Expected: 001 e 002 com `TimeInstant` de segundos atrás (Wokwi publicando); nenhuma entidade `Thing` (se houver, anotar os ids antes de seguir, para comparar no Passo 4).

- [ ] **Passo 2: subir o backend e conferir saúde**

Run (de dentro de `backend/`, em segundo plano): `.venv/Scripts/python -m uvicorn app.main:app --reload`; depois `curl -s http://localhost:8000/api/config/health`.
Expected: `Application startup complete`; health `"ok":true`. Swagger (`/docs`) com as 7 rotas novas. Se o health der `false`, **pare** e reporte.

- [ ] **Passo 3: gravar os corpos dos cadastros**

Run (de dentro de `backend/`; `<SCRATCH>` é o diretório de scratchpad da sessão):
```bash
.venv/Scripts/python -c "import json; d='<SCRATCH>'; [json.dump(c, open(f'{d}/{c[\"device_id\"]}.json','w'), ensure_ascii=True) for c in ({'device_id':'vinheria001','name':'Vinheria Paulista','city':'São Paulo'}, {'device_id':'vinheria002','name':'Vinheria Mineira','city':'Minas Gerais'}, {'device_id':'vinheria099','name':'Teste','city':'Teste'})]"
```
Expected: três arquivos `.json` no scratchpad; o da 001 contém `São Paulo`.

- [ ] **Passo 4: adotar a `vinheria001`**

Run:
```bash
curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/api/devices -H "Content-Type: application/json" --data-binary @<SCRATCH>/vinheria001.json
curl -s $H http://IP:4041/iot/devices/vinheria001
curl -s $H "http://IP:1026/v2/entities/urn:ngsi-ld:Vinheria:001?options=keyValues&attrs=temp_min,temp_max,hum_min,hum_max,lux_min,lux_max"
curl -s $H "http://IP:1026/v2/subscriptions?limit=1000"
curl -s $H "http://IP:1026/v2/entities?type=Thing&options=keyValues"
```
Expected: `HTTP 201` com `"city":"São Paulo"`; o device lista os 5 comandos, `set_limits` incluído; a entidade traz `temp_min 12`, `temp_max 18`, `hum_min 50`, `hum_max 70`, `lux_min 0`, `lux_max 30`; exatamente **3** subscriptions com `urn:ngsi-ld:Vinheria:001` (temperature, humidity, luminosity); nenhuma entidade `Thing` nova. Se der 409 do IoT Agent mesmo com a 3.7b, **pare** e reporte (o autoprovisionamento está mais rápido que o previsto).

- [ ] **Passo 5: leitura atual avançando**

Run: `curl -s http://localhost:8000/api/devices/vinheria001/current`, esperar 5 s e rodar de novo.
Expected: valores reais (não `null`) e `time_instant` diferente entre as duas chamadas. Se ficar `null` por mais de 10 s com o Wokwi rodando, **pare** e reporte (o offline da Task 4 depende disso).

- [ ] **Passo 6: comando ainda chega ao ESP32**

A entidade agora é criada pelo upsert da faixa antes da primeira leitura; é preciso provar que os comandos continuam encaminhados. `alert_off` é inofensivo (desliga alertas).

Run:
```bash
.venv/Scripts/python -c "import json; json.dump({'alert_off': {'type': 'command', 'value': ''}}, open('<SCRATCH>/cmd.json', 'w'))"
curl -s -o /dev/null -w "%{http_code}\n" $H -H "Content-Type: application/json" -X PATCH --data-binary @<SCRATCH>/cmd.json "http://IP:1026/v2/entities/urn:ngsi-ld:Vinheria:001/attrs"
```
Esperar 10 s e rodar: `curl -s $H "http://IP:1026/v2/entities/urn:ngsi-ld:Vinheria:001?options=keyValues&attrs=alert_off_status,alert_off_info"`
Expected: `204` no PATCH; depois `alert_off_status` `OK` e `alert_off_info` `ok` (o Wokwi respondeu no `cmdexe`). `PENDING` por mais de 30 s: **pare** e reporte.

- [ ] **Passo 7: histórico e score**

Run:
```bash
curl -s "http://localhost:8000/api/devices/vinheria001/history?attr=temperature&last_n=20"
curl -s http://localhost:8000/api/devices/vinheria001/score
```
Expected: lista de `{ts, value}` com pontos reais (pode incluir pontos de antes da adoção, já que o histórico do STH não é apagado); score com `available: true` e número coerente com os valores atuais e a faixa padrão.

- [ ] **Passo 8: adotar a `vinheria002`**

Repetir os Passos 4 e 5 com `vinheria002.json` e `urn:ngsi-ld:Vinheria:002`.
Expected: os mesmos resultados, com `"name":"Vinheria Mineira"` e `"city":"Minas Gerais"`; `GET http://localhost:8000/api/devices` lista as duas, ordenadas.

- [ ] **Passo 9: ciclo descartável com a `vinheria099`**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/devices -H "Content-Type: application/json" --data-binary @<SCRATCH>/vinheria099.json
curl -s http://localhost:8000/api/devices/vinheria099/score
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE http://localhost:8000/api/devices/vinheria099
curl -s -o /dev/null -w "%{http_code}\n" $H http://IP:4041/iot/devices/vinheria099
curl -s -o /dev/null -w "%{http_code}\n" $H "http://IP:1026/v2/entities/urn:ngsi-ld:Vinheria:099"
curl -s $H "http://IP:1026/v2/subscriptions?limit=1000" | grep -c "Vinheria:099"
```
Expected, na ordem: `201`; score com `"available":false` e `"message":"Score indisponível: aguardando leitura de temperatura, umidade e luminosidade"`; `204`; `404`; `404`; `0`.

- [ ] **Passo 10: parar o backend, limpar e conferir segredos fora do Git**

Parar o uvicorn; apagar os `.json` do scratchpad. **Não apagar `backend/vinheria.db`:** ele é o único registro local de nome e cidade das vinherias (apagá-lo na primeira execução deixou o cadastro vazio, e foi preciso readotar a 001 e a 002). Na raiz: `git status --short`.
Expected: nenhum `backend/.env` nem `*.db` listado.

- [ ] **Passo 11: marcar a Task 3 como feita**

Em `PLANO-CP5-VINHERIA.md`, na seção `### Task 3`, marcar os passos com `[x]` e trocar a nota de planejamento por: `> **FEITA em <data>** — executada pelo plano docs/specs/task-3-cadastro-historico-score/plan.md (commits <primeiro>..<último>). <resumo de 1 linha da verificação real, citando a correção do upsert (F4)>`. Em `README.md`, na seção Roadmap, marcar `[x] Backend: cadastro de vinherias, histórico e score`.

- [ ] **Passo 12: commit**

```bash
git add PLANO-CP5-VINHERIA.md README.md
git commit -m "docs: fecha task 3 com cadastro, historico e score das vinherias"
```

**Fim da Task 3. Pare para revisão do usuário.**

---

## Como verificar (aceite final)

Os itens da seção 6 da [`spec.md`](spec.md), todos com evidência colada no chat:

1. `pytest -q` → 160 testes passando, sem rede.
2. Swagger com as 7 rotas novas.
3. `vinheria001` adotada: `set_limits` no IoT Agent, faixa padrão no Orion, 3 subscriptions, `/current` com `time_instant` avançando e `alert_off` respondido pelo Wokwi.
4. `vinheria002` adotada da mesma forma.
5. Histórico real em `{ts, value}` e score coerente.
6. Ciclo da `vinheria099`: 201, score indisponível com mensagem, 204, e nada sobrando no FIWARE.
7. `.env` e `*.db` fora do Git.
