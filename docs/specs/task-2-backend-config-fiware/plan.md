# Task 2 — Backend: configuração, banco e cliente FIWARE — Plano de execução

> **Para quem executa (Sonnet):** use `superpowers:executing-plans` (ou `superpowers:subagent-driven-development`). Os passos usam checkbox (`- [ ]`). Execute **uma subtarefa por vez**, informe o resultado de cada passo e **pare para revisão do usuário ao fim de cada subtarefa** (`CLAUDE.md` §2 e §4). Se algo não bater com a spec, pare e devolva para planejamento; não improvise.

**Objetivo:** criar a base do backend FastAPI: configuração vinda do `.env` e trocável em runtime, SQLite com o schema do projeto, o `FiwareClient` assíncrono (a única porta HTTP para o FIWARE) e a API `/api/config`.

**Arquitetura:** `Settings` lê o `.env`; o `ConfigStore` guarda no SQLite o que o usuário muda pelo painel e se sobrepõe ao `.env`. O `FiwareClient` monta as URLs a partir do `ConfigStore` a cada chamada e transforma falhas em `FiwareError`; um handler central traduz essas exceções em respostas HTTP. As rotas só falam com `ConfigStore` e `FiwareClient`.

**Stack:** Python 3.12, FastAPI, Uvicorn, httpx (async), Pydantic v2, python-dotenv, SQLite (`sqlite3`), pytest + respx + plugin `anyio`.

**Spec:** [`spec.md`](spec.md) — requisitos R1 a R10 e decisões D1 a D9. Leia antes de começar.

## Global Constraints

- Python 3.12 em `backend/.venv`; todos os comandos rodam de dentro de `backend/` com `.venv/Scripts/python -m ...` (Windows, Git Bash ou PowerShell).
- Versões fixadas: `fastapi==0.142.2`, `uvicorn[standard]==0.54.0`, `httpx==0.28.1`, `pydantic==2.13.5`, `python-dotenv==1.2.4`, `pytest==9.1.1`, `respx==0.23.1`. Nenhuma outra dependência.
- Comentários e docstrings **em português**, explicando o propósito de cada módulo e de cada função não óbvia.
- Só `app/services/fiware_client.py` importa `httpx` em código de produção. Rotas não importam `httpx`.
- Nada hardcoded de IP, porta, chave ou header: tudo sai de `Settings`/`ConfigStore`.
- Nomes canônicos: type `Vinheria`; headers `fiware-service: smart`, `fiware-servicepath: /`; apikey `TEF`; atributos `t/h/l` → `temperature/humidity/luminosity`; comandos `blink_temp`, `blink_hum`, `blink_lux`, `alert_off`, `set_limits`.
- `backend/.env` e `*.db` nunca são commitados.
- Commits: mensagem em português, imperativo, uma linha, prefixo `feat:`/`test:`/`chore:`/`docs:`, **sem linha de co-author**.
- Testes nunca acessam a rede: toda chamada HTTP é interceptada pelo `respx`.

## Review Focus

Situações que um usuário real vai encontrar e que a spec implica. Cada uma tem teste na subtarefa indicada.

1. **IP digitado "sujo" no painel** (`" http://3.215.3.216:1026/ "`): deve virar `3.215.3.216`, e não montar `http://http://...`. Testes `test_load_settings_normaliza_host` (2.2) e `test_put_config_atualiza_e_normaliza` (2.7).
2. **EC2 desligada ou IP errado:** o health responde `ok: false` com o erro, em até ~5 s, sem exceção; qualquer outra rota responde 503 em JSON, nunca 500. Testes `test_health_um_servico_fora` (2.3) e `test_handler_traduz_erros_fiware` (2.7).
3. **IP trocado com o backend rodando:** a próxima chamada usa o IP novo, sem reiniciar. Teste `test_urls_usam_config_atual` (2.3).
4. **Backend iniciado sem `FIWARE_HOST`:** o app sobe, `GET /api/config` mostra `ec2_ip: ""`, e o health explica o que configurar, sem tentar a rede. Testes `test_health_sem_ip` (2.3) e `test_get_config_sem_ip` (2.7).
5. **Recriar ou remover algo que já existe ou já sumiu:** service group repetido (409) e remoção de device ou entidade inexistente (404) não são erro. Testes `test_provision_service_group_aceita_409` (2.4), `test_delete_device_aceita_404` (2.4) e `test_delete_entity_aceita_404` (2.5).

---

## Subtarefa 2.1 — Esqueleto do backend e ambiente

**Files:**
- Create: `.gitignore` (raiz do repositório)
- Create: `backend/requirements.txt`, `backend/.env.example`, `backend/pytest.ini`
- Create: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/models/__init__.py`, `backend/app/services/__init__.py`, `backend/app/api/__init__.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`

**Interfaces:**
- Consumes: nada.
- Produces: pacote `app` importável a partir de `backend/`; fixture `anyio_backend`.

- [ ] **Passo 1: criar o `.gitignore` na raiz**

```gitignore
# Segredos e configuração local
.env

# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/

# Banco local do backend
*.db

# Front-end
node_modules/
dist/
```

- [ ] **Passo 2: criar `backend/requirements.txt`**

```text
fastapi==0.142.2
uvicorn[standard]==0.54.0
httpx==0.28.1
pydantic==2.13.5
python-dotenv==1.2.4
pytest==9.1.1
respx==0.23.1
```

- [ ] **Passo 3: criar `backend/.env.example`**

```dotenv
# Configuração do backend Smart Solutions.
# Copie para .env e preencha. O .env nunca vai para o Git.

# IP elástico da EC2 onde roda o FIWARE. Pode ser trocado em runtime no painel Avançado.
FIWARE_HOST=

# Portas dos componentes FIWARE
ORION_PORT=1026
IOTA_PORT=4041
STH_PORT=8666

# Headers e chave do FIWARE (nomes canônicos do projeto)
FIWARE_SERVICE=smart
FIWARE_SERVICEPATH=/
FIWARE_APIKEY=TEF

# Endereço do STH-Comet visto de dentro da rede Docker (destino das subscriptions)
STH_INTERNAL_URL=http://sth-comet:8666

# Intervalo do poller e limite para considerar uma vinheria offline (segundos)
POLL_SECONDS=5
OFFLINE_SECONDS=30

# Tempo máximo de espera de cada chamada ao FIWARE (segundos)
HTTP_TIMEOUT_SECONDS=5

# Arquivo SQLite (relativo à pasta backend/)
DATABASE_PATH=vinheria.db

# Origens liberadas no CORS, separadas por vírgula
CORS_ORIGINS=http://localhost:5173
```

- [ ] **Passo 4: criar `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Passo 5: criar os `__init__.py` vazios e o `conftest.py` inicial**

Os seis `__init__.py` listados em **Files** ficam vazios. `backend/tests/conftest.py`:

```python
"""Fixtures compartilhadas pelos testes do backend."""
import pytest


@pytest.fixture
def anyio_backend():
    """Roda os testes assíncronos (marcados com anyio) no asyncio."""
    return "asyncio"
```

- [ ] **Passo 6: criar o ambiente virtual e instalar as dependências**

Run (de dentro de `backend/`):
```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -c "import fastapi, httpx, respx, dotenv, anyio; print('ok')"
```
Expected: a última linha imprime `ok`.

- [ ] **Passo 7: confirmar que o pytest roda sem testes**

Run: `.venv/Scripts/python -m pytest -v`
Expected: `no tests ran` (código de saída 5). Qualquer erro de importação aqui é problema de esqueleto: pare e reporte.

- [ ] **Passo 8: criar o `.env` local (não commitado) e conferir o `.gitignore`**

Copiar `backend/.env.example` para `backend/.env` e preencher `FIWARE_HOST` com o IP elástico (o mesmo do `BROKER_MQTT` do firmware). Depois, na raiz:

Run: `git status --short`
Expected: aparecem `.gitignore` e `backend/` com seus arquivos, **mas não** `backend/.env` nem `backend/.venv/`.

- [ ] **Passo 9: commit**

```bash
git add .gitignore backend/requirements.txt backend/.env.example backend/pytest.ini backend/app backend/tests
git commit -m "chore: cria esqueleto do backend com dependencias e gitignore"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 2.2 — Schemas, banco SQLite e configuração (R1, R2, R3)

**Files:**
- Create: `backend/app/models/schemas.py`, `backend/app/core/db.py`, `backend/app/core/config.py`
- Create: `backend/tests/test_config.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: nada.
- Produces: `normalize_host(value: str) -> str`; modelos `RuntimeConfig`, `ConfigUpdate`, `Device`, `ServiceHealth`, `HealthReport`; `connect(path: str) -> sqlite3.Connection`; `Settings` (dataclass frozen); `load_settings(env_file: str | None = ".env") -> Settings`; `ConfigStore(conn, settings)` com `get() -> RuntimeConfig` e `update(changes: ConfigUpdate) -> RuntimeConfig`.

- [ ] **Passo 1: adicionar as fixtures de config ao `conftest.py`**

Substituir o conteúdo de `backend/tests/conftest.py` por:

```python
"""Fixtures compartilhadas pelos testes do backend."""
import pytest

from app.core.config import ConfigStore, Settings
from app.core.db import connect


@pytest.fixture
def anyio_backend():
    """Roda os testes assíncronos (marcados com anyio) no asyncio."""
    return "asyncio"


@pytest.fixture
def settings(tmp_path):
    """Settings de teste: IP fictício e banco num diretório temporário."""
    return Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "teste.db"))


@pytest.fixture
def conn(settings):
    """Conexão SQLite já com o schema criado."""
    conexao = connect(settings.database_path)
    yield conexao
    conexao.close()


@pytest.fixture
def store(conn, settings):
    """ConfigStore sobre o banco de teste."""
    return ConfigStore(conn, settings)
```

- [ ] **Passo 2: escrever os testes que falham**

`backend/tests/test_config.py`:

```python
"""Testes de Settings, ConfigStore e banco (spec R1, R2 e R3)."""
import pytest
from pydantic import ValidationError

from app.core.config import ConfigStore, Settings, load_settings
from app.core.db import connect
from app.models.schemas import ConfigUpdate

VARIAVEIS = (
    "FIWARE_HOST", "ORION_PORT", "IOTA_PORT", "STH_PORT",
    "FIWARE_SERVICE", "FIWARE_SERVICEPATH", "FIWARE_APIKEY", "STH_INTERNAL_URL",
    "POLL_SECONDS", "OFFLINE_SECONDS", "HTTP_TIMEOUT_SECONDS",
    "DATABASE_PATH", "CORS_ORIGINS",
)


@pytest.fixture
def ambiente_limpo(monkeypatch):
    """Remove do ambiente as variáveis do backend para o teste controlar tudo."""
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    return monkeypatch


def test_load_settings_usa_defaults(ambiente_limpo):
    s = load_settings(env_file=None)
    assert s == Settings()
    assert s.fiware_host == ""
    assert (s.orion_port, s.iota_port, s.sth_port) == (1026, 4041, 8666)
    assert (s.fiware_service, s.fiware_servicepath, s.fiware_apikey) == ("smart", "/", "TEF")
    assert s.sth_internal_url == "http://sth-comet:8666"
    assert (s.poll_seconds, s.offline_seconds) == (5, 30)
    assert s.cors_origins == ("http://localhost:5173",)


def test_load_settings_le_variaveis_de_ambiente(ambiente_limpo):
    ambiente_limpo.setenv("FIWARE_HOST", "3.3.3.3")
    ambiente_limpo.setenv("ORION_PORT", "2026")
    ambiente_limpo.setenv("POLL_SECONDS", "10")
    ambiente_limpo.setenv("HTTP_TIMEOUT_SECONDS", "2.5")
    ambiente_limpo.setenv("CORS_ORIGINS", "http://a:1, http://b:2")
    s = load_settings(env_file=None)
    assert s.fiware_host == "3.3.3.3"
    assert s.orion_port == 2026
    assert s.poll_seconds == 10
    assert s.http_timeout_seconds == 2.5
    assert s.cors_origins == ("http://a:1", "http://b:2")


def test_load_settings_normaliza_host(ambiente_limpo):
    ambiente_limpo.setenv("FIWARE_HOST", " http://3.3.3.3:1026/ ")
    assert load_settings(env_file=None).fiware_host == "3.3.3.3"


def test_load_settings_ignora_variavel_vazia(ambiente_limpo):
    ambiente_limpo.setenv("ORION_PORT", "")
    assert load_settings(env_file=None).orion_port == 1026


def test_connect_cria_tabelas(tmp_path):
    conexao = connect(str(tmp_path / "t.db"))
    nomes = {linha["name"] for linha in conexao.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    conexao.close()
    assert {"config", "devices", "triggers", "alerts"} <= nomes


def test_config_store_usa_env_quando_banco_vazio(store):
    cfg = store.get()
    assert cfg.ec2_ip == "10.0.0.1"
    assert (cfg.orion_port, cfg.iota_port, cfg.sth_port) == (1026, 4041, 8666)
    assert (cfg.poll_seconds, cfg.offline_seconds) == (5, 30)


def test_config_store_update_parcial(store):
    cfg = store.update(ConfigUpdate(ec2_ip="20.0.0.2"))
    assert cfg.ec2_ip == "20.0.0.2"
    assert cfg.orion_port == 1026
    cfg = store.update(ConfigUpdate(poll_seconds=10))
    assert cfg.ec2_ip == "20.0.0.2"
    assert cfg.poll_seconds == 10


def test_config_store_persiste_entre_conexoes(settings):
    primeira = connect(settings.database_path)
    ConfigStore(primeira, settings).update(ConfigUpdate(ec2_ip="20.0.0.2"))
    primeira.close()
    segunda = connect(settings.database_path)
    assert ConfigStore(segunda, settings).get().ec2_ip == "20.0.0.2"
    segunda.close()


def test_config_update_rejeita_ip_vazio():
    with pytest.raises(ValidationError):
        ConfigUpdate(ec2_ip="   ")
    with pytest.raises(ValidationError):
        ConfigUpdate(ec2_ip="http://")


def test_config_update_normaliza_ip():
    assert ConfigUpdate(ec2_ip=" https://20.0.0.2:4041/iot ").ec2_ip == "20.0.0.2"


@pytest.mark.parametrize("campos", [
    {"orion_port": 0},
    {"iota_port": 70000},
    {"poll_seconds": 0},
    {"poll_seconds": 301},
    {"offline_seconds": 4},
    {"offline_seconds": 3601},
])
def test_config_update_rejeita_valores_fora_da_faixa(campos):
    with pytest.raises(ValidationError):
        ConfigUpdate(**campos)
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: erro de coleta com `ModuleNotFoundError: No module named 'app.core.config'` (ou `app.models.schemas`).

- [ ] **Passo 4: implementar `backend/app/models/schemas.py`**

```python
"""
Modelos de dados (Pydantic) compartilhados pelo backend.

Aqui ficam os contratos de entrada e saída da API e dos services. Esta task
cria os modelos de configuração, de saúde do FIWARE e o Device; as próximas
tasks acrescentam os seus (triggers, leituras, alertas, chat).
"""
from pydantic import BaseModel, Field, field_validator

_PORTA = {"ge": 1, "le": 65535}
_POLL = {"ge": 1, "le": 300}
_OFFLINE = {"ge": 5, "le": 3600}


def normalize_host(value: str) -> str:
    """Limpa um endereço digitado pelo usuário e devolve só o host.

    Tira espaços, o esquema (http:// ou https://), qualquer caminho e a porta.
    Ex.: " http://3.3.3.3:1026/ " -> "3.3.3.3". IPv6 não é suportado.
    """
    host = value.strip()
    for prefixo in ("http://", "https://"):
        if host.lower().startswith(prefixo):
            host = host[len(prefixo):]
    host = host.split("/")[0]
    host = host.split(":")[0]
    return host.strip()


class RuntimeConfig(BaseModel):
    """Configuração em uso agora (o .env com o que o usuário mudou por cima)."""
    ec2_ip: str
    orion_port: int = Field(**_PORTA)
    iota_port: int = Field(**_PORTA)
    sth_port: int = Field(**_PORTA)
    poll_seconds: int = Field(**_POLL)
    offline_seconds: int = Field(**_OFFLINE)


class ConfigUpdate(BaseModel):
    """Alteração parcial da configuração: só os campos enviados mudam."""
    ec2_ip: str | None = None
    orion_port: int | None = Field(default=None, **_PORTA)
    iota_port: int | None = Field(default=None, **_PORTA)
    sth_port: int | None = Field(default=None, **_PORTA)
    poll_seconds: int | None = Field(default=None, **_POLL)
    offline_seconds: int | None = Field(default=None, **_OFFLINE)

    @field_validator("ec2_ip")
    @classmethod
    def _limpa_ip(cls, valor: str | None) -> str | None:
        """Normaliza o IP e recusa endereço vazio."""
        if valor is None:
            return None
        host = normalize_host(valor)
        if not host:
            raise ValueError("ec2_ip não pode ser vazio")
        return host


class Device(BaseModel):
    """Uma vinheria cadastrada: device no IoT Agent e entidade no Orion."""
    device_id: str = Field(pattern=r"^vinheria\d{3}$")
    entity_id: str
    name: str
    city: str


class ServiceHealth(BaseModel):
    """Resultado do teste de um componente do FIWARE."""
    ok: bool
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None


class HealthReport(BaseModel):
    """Saúde dos três componentes do FIWARE no IP configurado."""
    ok: bool
    ec2_ip: str
    orion: ServiceHealth
    iota: ServiceHealth
    sth: ServiceHealth
```

- [ ] **Passo 5: implementar `backend/app/core/db.py`**

```python
"""
Banco local SQLite do backend.

Guarda o que não mora no FIWARE: configuração de runtime, cadastro das
vinherias (nome e cidade), faixas ideais (triggers) e histórico de alertas.
O schema é criado na abertura, então um banco novo já nasce pronto.
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
    device_id  TEXT PRIMARY KEY,
    entity_id  TEXT NOT NULL,
    name       TEXT NOT NULL,
    city       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS triggers (
    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    attr      TEXT NOT NULL,
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    PRIMARY KEY (device_id, attr)
);
-- alerts não tem chave estrangeira: o histórico sobrevive à remoção da vinheria
CREATE TABLE IF NOT EXISTS alerts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    attr      TEXT NOT NULL,
    value     REAL,
    opened_at TEXT NOT NULL,
    closed_at TEXT
);
"""


def connect(path: str) -> sqlite3.Connection:
    """Abre (ou cria) o banco em `path` e garante o schema.

    check_same_thread=False porque o FastAPI atende rotas síncronas em threads
    diferentes; as operações são curtas e o SQLite serializa as escritas.
    """
    conexao = sqlite3.connect(path, check_same_thread=False)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.executescript(SCHEMA)
    conexao.commit()
    return conexao
```

- [ ] **Passo 6: implementar `backend/app/core/config.py`**

```python
"""
Configuração do backend em dois níveis.

- Settings: valores lidos do .env (ou do ambiente) na partida. São os defaults
  do projeto e incluem o IP elástico da EC2 (FIWARE_HOST).
- ConfigStore: configuração de runtime que o usuário troca pelo painel
  (IP, portas, intervalos). Fica salva no SQLite e prevalece sobre o .env,
  inclusive depois de reiniciar o backend.
"""
import json
import os
import sqlite3
from dataclasses import dataclass

from dotenv import load_dotenv

from app.models.schemas import ConfigUpdate, RuntimeConfig, normalize_host


@dataclass(frozen=True)
class Settings:
    """Configuração fixa da partida. Os defaults valem quando o .env não informa."""
    fiware_host: str = ""
    orion_port: int = 1026
    iota_port: int = 4041
    sth_port: int = 8666
    fiware_service: str = "smart"
    fiware_servicepath: str = "/"
    fiware_apikey: str = "TEF"
    sth_internal_url: str = "http://sth-comet:8666"
    poll_seconds: int = 5
    offline_seconds: int = 30
    http_timeout_seconds: float = 5.0
    database_path: str = "vinheria.db"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)


def _env(nome: str, padrao):
    """Lê uma variável de ambiente; ausente ou em branco devolve o padrão."""
    valor = os.environ.get(nome, "").strip()
    return valor if valor else padrao


def load_settings(env_file: str | None = ".env") -> Settings:
    """Monta o Settings a partir do .env e do ambiente.

    Variáveis já definidas no ambiente têm prioridade sobre o arquivo.
    `env_file=None` ignora o arquivo (usado nos testes).
    """
    if env_file:
        load_dotenv(env_file, override=False)
    p = Settings()
    origens = _env("CORS_ORIGINS", ",".join(p.cors_origins))
    return Settings(
        fiware_host=normalize_host(_env("FIWARE_HOST", p.fiware_host)),
        orion_port=int(_env("ORION_PORT", p.orion_port)),
        iota_port=int(_env("IOTA_PORT", p.iota_port)),
        sth_port=int(_env("STH_PORT", p.sth_port)),
        fiware_service=_env("FIWARE_SERVICE", p.fiware_service),
        fiware_servicepath=_env("FIWARE_SERVICEPATH", p.fiware_servicepath),
        fiware_apikey=_env("FIWARE_APIKEY", p.fiware_apikey),
        sth_internal_url=_env("STH_INTERNAL_URL", p.sth_internal_url).rstrip("/"),
        poll_seconds=int(_env("POLL_SECONDS", p.poll_seconds)),
        offline_seconds=int(_env("OFFLINE_SECONDS", p.offline_seconds)),
        http_timeout_seconds=float(_env("HTTP_TIMEOUT_SECONDS", p.http_timeout_seconds)),
        database_path=_env("DATABASE_PATH", p.database_path),
        cors_origins=tuple(o.strip() for o in origens.split(",") if o.strip()),
    )


class ConfigStore:
    """Configuração de runtime: defaults do Settings + alterações salvas no SQLite."""

    def __init__(self, conn: sqlite3.Connection, settings: Settings):
        self._conn = conn
        self._settings = settings

    def _defaults(self) -> dict:
        """Valores de partida, vindos do .env."""
        s = self._settings
        return {
            "ec2_ip": s.fiware_host,
            "orion_port": s.orion_port,
            "iota_port": s.iota_port,
            "sth_port": s.sth_port,
            "poll_seconds": s.poll_seconds,
            "offline_seconds": s.offline_seconds,
        }

    def get(self) -> RuntimeConfig:
        """Devolve a configuração atual: defaults com os valores salvos por cima."""
        valores = self._defaults()
        for linha in self._conn.execute("SELECT key, value FROM config"):
            if linha["key"] in valores:
                valores[linha["key"]] = json.loads(linha["value"])
        return RuntimeConfig(**valores)

    def update(self, changes: ConfigUpdate) -> RuntimeConfig:
        """Grava só os campos enviados e devolve a configuração completa."""
        dados = changes.model_dump(exclude_none=True)
        with self._conn:
            for chave, valor in dados.items():
                self._conn.execute(
                    "INSERT INTO config (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (chave, json.dumps(valor)),
                )
        return self.get()
```

- [ ] **Passo 7: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: 16 testes `PASSED` (11 funções, uma delas parametrizada com 6 casos).

- [ ] **Passo 8: commit**

```bash
git add backend/app/models/schemas.py backend/app/core/db.py backend/app/core/config.py backend/tests/conftest.py backend/tests/test_config.py
git commit -m "feat: adiciona configuracao do backend com ConfigStore e schema SQLite"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 2.3 — Base do FiwareClient: URLs, erros, leituras do Orion e saúde (R4, R5, R7.2, R7.3, R9)

**Files:**
- Create: `backend/app/services/fiware_errors.py`, `backend/app/services/fiware_client.py`
- Create: `backend/tests/test_fiware_client.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `ConfigStore`, `Settings`, `ConfigUpdate`, `ServiceHealth`, `HealthReport` (2.2).
- Produces: `FiwareError(service, message, status_code=None)` com `.service`, `.message`, `.status_code`; subclasses `FiwareUnavailable`, `FiwareNotFound`, `FiwareConflict`. `FiwareClient(config_store, settings, http=None)` com `aclose()`, `orion_url(path)`, `iota_url(path)`, `sth_url(path)`, `get_entity(entity_id) -> dict`, `list_entities(entity_type="Vinheria") -> list[dict]`, `health() -> HealthReport`. Constantes `SENSOR_ATTRS`, `COMMANDS`, `ENTITY_TYPE`.

- [ ] **Passo 1: adicionar as fixtures do cliente ao `conftest.py`**

Acrescentar ao fim de `backend/tests/conftest.py` (e o import no topo):

```python
from app.services.fiware_client import FiwareClient
```

```python
@pytest.fixture
def fiware(store, settings):
    """FiwareClient apontando para o IP fictício 10.0.0.1 (respx intercepta)."""
    return FiwareClient(store, settings)


@pytest.fixture
def fiware_sem_ip(tmp_path):
    """FiwareClient de um backend iniciado sem FIWARE_HOST."""
    settings = Settings(fiware_host="", database_path=str(tmp_path / "sem_ip.db"))
    conexao = connect(settings.database_path)
    yield FiwareClient(ConfigStore(conexao, settings), settings)
    conexao.close()
```

- [ ] **Passo 2: escrever os testes que falham**

`backend/tests/test_fiware_client.py`:

```python
"""Testes da base do FiwareClient: URLs, headers, erros, leituras e saúde.

Cobre a spec R4, R5.1, R5.2, R7.2, R7.3 e R9. Nenhum teste acessa a rede:
o respx intercepta as requisições do httpx.
"""
import httpx
import pytest
import respx

from app.models.schemas import ConfigUpdate
from app.services.fiware_errors import FiwareError, FiwareNotFound, FiwareUnavailable

pytestmark = pytest.mark.anyio

ORION = "http://10.0.0.1:1026"
IOTA = "http://10.0.0.1:4041"
STH = "http://10.0.0.1:8666"
ENTIDADE = "urn:ngsi-ld:Vinheria:001"


def test_urls_usam_config_atual(fiware, store):
    assert fiware.orion_url("/v2/entities") == f"{ORION}/v2/entities"
    assert fiware.iota_url("/iot/devices") == f"{IOTA}/iot/devices"
    assert fiware.sth_url("/version") == f"{STH}/version"
    store.update(ConfigUpdate(ec2_ip="20.0.0.2", orion_port=2026))
    assert fiware.orion_url("/v2/entities") == "http://20.0.0.2:2026/v2/entities"
    assert fiware.iota_url("/iot/devices") == "http://20.0.0.2:4041/iot/devices"


def test_sem_ip_configurado_levanta_unavailable(fiware_sem_ip):
    with pytest.raises(FiwareUnavailable) as erro:
        fiware_sem_ip.orion_url("/version")
    assert "FIWARE_HOST" in erro.value.message


@respx.mock
async def test_requests_levam_headers_fiware(fiware):
    rota = respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(
        return_value=httpx.Response(200, json={"id": ENTIDADE}))
    await fiware.get_entity(ENTIDADE)
    headers = rota.calls.last.request.headers
    assert headers["fiware-service"] == "smart"
    assert headers["fiware-servicepath"] == "/"


@respx.mock
async def test_get_entity_usa_key_values(fiware):
    entidade = {"id": ENTIDADE, "type": "Vinheria", "temperature": 14.2}
    rota = respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(
        return_value=httpx.Response(200, json=entidade))
    assert await fiware.get_entity(ENTIDADE) == entidade
    assert rota.calls.last.request.url.params["options"] == "keyValues"


@respx.mock
async def test_get_entity_inexistente_levanta_not_found(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(
        return_value=httpx.Response(404, json={"error": "NotFound"}))
    with pytest.raises(FiwareNotFound) as erro:
        await fiware.get_entity(ENTIDADE)
    assert erro.value.status_code == 404
    assert erro.value.service == "orion"


@respx.mock
async def test_list_entities_uma_chamada(fiware):
    frota = [
        {"id": ENTIDADE, "type": "Vinheria", "TimeInstant": "2026-10-05T22:00:00.000Z"},
        {"id": "urn:ngsi-ld:Vinheria:002", "type": "Vinheria"},
    ]
    rota = respx.get(f"{ORION}/v2/entities").mock(return_value=httpx.Response(200, json=frota))
    resultado = await fiware.list_entities()
    assert [e["id"] for e in resultado] == [ENTIDADE, "urn:ngsi-ld:Vinheria:002"]
    assert resultado[0]["TimeInstant"] == "2026-10-05T22:00:00.000Z"
    assert rota.call_count == 1
    params = rota.calls.last.request.url.params
    assert params["type"] == "Vinheria"
    assert params["options"] == "keyValues"
    assert params["limit"] == "1000"


@respx.mock
async def test_timeout_vira_unavailable(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(side_effect=httpx.ConnectTimeout("tempo"))
    with pytest.raises(FiwareUnavailable) as erro:
        await fiware.get_entity(ENTIDADE)
    assert erro.value.service == "orion"


@respx.mock
async def test_conexao_recusada_vira_unavailable(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(side_effect=httpx.ConnectError("recusada"))
    with pytest.raises(FiwareUnavailable):
        await fiware.get_entity(ENTIDADE)


@respx.mock
async def test_status_500_vira_fiware_error(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(return_value=httpx.Response(500, text="falhou"))
    with pytest.raises(FiwareError) as erro:
        await fiware.get_entity(ENTIDADE)
    assert erro.value.status_code == 500
    assert not isinstance(erro.value, FiwareUnavailable)


def _mock_saude(iota=None):
    """Registra no respx as três rotas de saúde; `iota` pode trocar a do IoT Agent."""
    respx.get(f"{ORION}/version").mock(return_value=httpx.Response(200, json={}))
    rota_iota = respx.get(f"{IOTA}/iot/about")
    if iota is None:
        rota_iota.mock(return_value=httpx.Response(200, json={}))
    else:
        rota_iota.mock(side_effect=iota)
    respx.get(f"{STH}/version").mock(return_value=httpx.Response(200, json={}))


@respx.mock
async def test_health_tudo_ok(fiware):
    _mock_saude()
    relatorio = await fiware.health()
    assert relatorio.ok is True
    assert relatorio.ec2_ip == "10.0.0.1"
    assert relatorio.orion.ok and relatorio.iota.ok and relatorio.sth.ok
    assert relatorio.orion.status_code == 200
    assert relatorio.orion.latency_ms is not None


@respx.mock
async def test_health_um_servico_fora(fiware):
    _mock_saude(iota=httpx.ConnectError("recusada"))
    relatorio = await fiware.health()
    assert relatorio.ok is False
    assert relatorio.orion.ok and relatorio.sth.ok
    assert relatorio.iota.ok is False
    assert relatorio.iota.error


async def test_health_sem_ip(fiware_sem_ip):
    with respx.mock() as mock:
        relatorio = await fiware_sem_ip.health()
    assert mock.calls.call_count == 0
    assert relatorio.ok is False
    assert relatorio.ec2_ip == ""
    for servico in (relatorio.orion, relatorio.iota, relatorio.sth):
        assert servico.ok is False
        assert "FIWARE_HOST" in servico.error
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_client.py -v`
Expected: erro de coleta com `ModuleNotFoundError: No module named 'app.services.fiware_client'`.

- [ ] **Passo 4: implementar `backend/app/services/fiware_errors.py`**

```python
"""
Exceções do cliente FIWARE.

Os services levantam estas exceções em vez de HTTPException, para não
depender do FastAPI (o poller da Task 4 também usa o cliente). A tradução
para resposta HTTP fica em app/api/errors.py.
"""


class FiwareError(Exception):
    """Falha ao falar com um componente do FIWARE (orion, iota, sth ou config)."""

    def __init__(self, service: str, message: str, status_code: int | None = None):
        super().__init__(f"{service}: {message}")
        self.service = service
        self.message = message
        self.status_code = status_code


class FiwareUnavailable(FiwareError):
    """Sem resposta: EC2 desligada, IP errado, timeout ou IP não configurado."""


class FiwareNotFound(FiwareError):
    """O recurso pedido não existe (HTTP 404)."""


class FiwareConflict(FiwareError):
    """O recurso já existe (HTTP 409)."""
```

- [ ] **Passo 5: implementar `backend/app/services/fiware_client.py` (base)**

```python
"""
Cliente HTTP do FIWARE — a única peça do backend que fala com a EC2.

Cobre os três componentes usados no projeto:
- IoT Agent MQTT (4041): service group e devices;
- Orion Context Broker (1026): entidades, comandos e subscriptions;
- STH-Comet (8666): histórico das leituras.

As URLs são montadas a cada chamada a partir do ConfigStore, então trocar o
IP pelo painel vale na hora, sem reiniciar o backend. Falhas de rede e status
de erro viram exceções de app.services.fiware_errors.
"""
import asyncio
import time

import httpx

from app.core.config import ConfigStore, Settings
from app.models.schemas import HealthReport, ServiceHealth
from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)

# Atributos de sensor: (nome curto no UltraLight, nome longo no Orion/STH, tipo)
SENSOR_ATTRS = (
    ("t", "temperature", "Float"),
    ("h", "humidity", "Float"),
    ("l", "luminosity", "Integer"),
)
# Comandos que o firmware entende
COMMANDS = ("blink_temp", "blink_hum", "blink_lux", "alert_off", "set_limits")
ENTITY_TYPE = "Vinheria"
# Máximo de itens por listagem no Orion (frota e subscriptions)
ORION_LIST_LIMIT = 1000


class FiwareClient:
    """Fachada assíncrona sobre as APIs REST do FIWARE."""

    def __init__(self, config_store: ConfigStore, settings: Settings,
                 http: httpx.AsyncClient | None = None):
        self._config = config_store
        self._settings = settings
        # Um único AsyncClient reaproveita conexões entre chamadas;
        # nos testes o respx intercepta as requisições dele.
        self._http = http or httpx.AsyncClient(timeout=settings.http_timeout_seconds)

    async def aclose(self) -> None:
        """Fecha o pool de conexões (chamado no desligamento do app)."""
        await self._http.aclose()

    # ----- URLs e requisição -------------------------------------------------

    def _base(self, campo_porta: str) -> str:
        """Monta http://<ip>:<porta> com a configuração deste instante."""
        cfg = self._config.get()
        if not cfg.ec2_ip:
            raise FiwareUnavailable(
                "config",
                "IP do FIWARE não configurado: defina FIWARE_HOST no .env "
                "ou informe o IP no painel Avançado",
            )
        return f"http://{cfg.ec2_ip}:{getattr(cfg, campo_porta)}"

    def orion_url(self, path: str) -> str:
        """URL completa de um caminho do Orion."""
        return self._base("orion_port") + path

    def iota_url(self, path: str) -> str:
        """URL completa de um caminho do IoT Agent."""
        return self._base("iota_port") + path

    def sth_url(self, path: str) -> str:
        """URL completa de um caminho do STH-Comet."""
        return self._base("sth_port") + path

    def _headers(self) -> dict[str, str]:
        """Headers de multi-tenancy exigidos por todos os componentes."""
        return {
            "fiware-service": self._settings.fiware_service,
            "fiware-servicepath": self._settings.fiware_servicepath,
        }

    async def _request(self, service: str, method: str, url: str, *,
                       aceitar: tuple[int, ...] = (), **kwargs) -> httpx.Response:
        """Faz a requisição e converte falhas em FiwareError.

        `aceitar` lista status de erro que, naquele contexto, contam como
        sucesso (ex.: 409 ao recriar o service group, 404 ao remover algo
        que já não existe).
        """
        try:
            resposta = await self._http.request(method, url, headers=self._headers(), **kwargs)
        except httpx.TimeoutException as exc:
            raise FiwareUnavailable(service, f"tempo esgotado em {url}") from exc
        except httpx.TransportError as exc:
            raise FiwareUnavailable(service, f"sem conexão com {url}: {exc}") from exc
        if resposta.is_success or resposta.status_code in aceitar:
            return resposta
        detalhe = resposta.text[:300] or resposta.reason_phrase
        if resposta.status_code == 404:
            raise FiwareNotFound(service, detalhe, 404)
        if resposta.status_code == 409:
            raise FiwareConflict(service, detalhe, 409)
        raise FiwareError(service, detalhe, resposta.status_code)

    # ----- Orion: leitura ----------------------------------------------------

    async def get_entity(self, entity_id: str) -> dict:
        """Estado atual de uma entidade, no formato simplificado keyValues."""
        resposta = await self._request(
            "orion", "GET", self.orion_url(f"/v2/entities/{entity_id}"),
            params={"options": "keyValues"},
        )
        return resposta.json()

    async def list_entities(self, entity_type: str = ENTITY_TYPE) -> list[dict]:
        """Todas as entidades de um tipo numa única chamada (usado pelo poller).

        O TimeInstant vem junto quando o service group tem timestamp: true.
        """
        resposta = await self._request(
            "orion", "GET", self.orion_url("/v2/entities"),
            params={"type": entity_type, "options": "keyValues", "limit": ORION_LIST_LIMIT},
        )
        return resposta.json()

    # ----- Saúde -------------------------------------------------------------

    async def _ping(self, service: str, url: str) -> ServiceHealth:
        """Testa um endpoint e mede a latência; nunca levanta exceção."""
        inicio = time.perf_counter()
        try:
            resposta = await self._request(service, "GET", url)
        except FiwareError as exc:
            return ServiceHealth(ok=False, status_code=exc.status_code, error=exc.message)
        latencia = int((time.perf_counter() - inicio) * 1000)
        return ServiceHealth(ok=True, status_code=resposta.status_code, latency_ms=latencia)

    async def health(self) -> HealthReport:
        """Testa Orion, IoT Agent e STH em paralelo no IP atual."""
        ec2_ip = self._config.get().ec2_ip
        try:
            urls = (
                self.orion_url("/version"),
                self.iota_url("/iot/about"),
                self.sth_url("/version"),
            )
        except FiwareUnavailable as exc:
            falha = ServiceHealth(ok=False, error=exc.message)
            return HealthReport(ok=False, ec2_ip=ec2_ip, orion=falha, iota=falha, sth=falha)
        orion, iota, sth = await asyncio.gather(
            self._ping("orion", urls[0]),
            self._ping("iota", urls[1]),
            self._ping("sth", urls[2]),
        )
        return HealthReport(ok=orion.ok and iota.ok and sth.ok, ec2_ip=ec2_ip,
                            orion=orion, iota=iota, sth=sth)
```

- [ ] **Passo 6: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_client.py -v`
Expected: 12 testes `PASSED`.

- [ ] **Passo 7: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 28 testes `PASSED`.

- [ ] **Passo 8: commit**

```bash
git add backend/app/services/fiware_errors.py backend/app/services/fiware_client.py backend/tests/conftest.py backend/tests/test_fiware_client.py
git commit -m "feat: adiciona base do cliente FIWARE com leitura do Orion e health"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 2.4 — IoT Agent: service group e devices (R6)

**Files:**
- Modify: `backend/app/services/fiware_client.py` (nova seção "IoT Agent")
- Create: `backend/tests/test_fiware_iota.py`

**Interfaces:**
- Consumes: `FiwareClient._request`, `iota_url`, `orion_url`, `SENSOR_ATTRS`, `COMMANDS`, `ENTITY_TYPE` (2.3); `Device` (2.2).
- Produces: `provision_service_group() -> None`, `provision_device(device: Device) -> None`, `delete_device(device_id: str) -> None`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_fiware_iota.py`:

```python
"""Testes do FiwareClient contra o IoT Agent (spec R6)."""
import json

import httpx
import pytest
import respx

from app.models.schemas import Device
from app.services.fiware_errors import FiwareConflict

pytestmark = pytest.mark.anyio

IOTA = "http://10.0.0.1:4041"
DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria São Paulo", city="São Paulo")


def _corpo(rota):
    """JSON enviado na última chamada da rota."""
    return json.loads(rota.calls.last.request.content)


@respx.mock
async def test_provision_service_group_envia_body(fiware):
    rota = respx.post(f"{IOTA}/iot/services").mock(return_value=httpx.Response(201))
    await fiware.provision_service_group()
    assert _corpo(rota) == {"services": [{
        "apikey": "TEF",
        "cbroker": "http://10.0.0.1:1026",
        "entity_type": "Thing",
        "resource": "",
        "timestamp": True,
    }]}


@respx.mock
async def test_provision_service_group_aceita_409(fiware):
    respx.post(f"{IOTA}/iot/services").mock(
        return_value=httpx.Response(409, json={"name": "DUPLICATE_GROUP"}))
    await fiware.provision_service_group()


@respx.mock
async def test_provision_device_envia_body(fiware):
    rota = respx.post(f"{IOTA}/iot/devices").mock(return_value=httpx.Response(201))
    await fiware.provision_device(DEVICE)
    device = _corpo(rota)["devices"][0]
    assert device["device_id"] == "vinheria001"
    assert device["entity_name"] == "urn:ngsi-ld:Vinheria:001"
    assert device["entity_type"] == "Vinheria"
    assert device["protocol"] == "PDI-IoTA-UltraLight"
    assert device["transport"] == "MQTT"
    assert device["commands"] == [
        {"name": "blink_temp", "type": "command"},
        {"name": "blink_hum", "type": "command"},
        {"name": "blink_lux", "type": "command"},
        {"name": "alert_off", "type": "command"},
        {"name": "set_limits", "type": "command"},
    ]
    assert device["attributes"] == [
        {"object_id": "t", "name": "temperature", "type": "Float"},
        {"object_id": "h", "name": "humidity", "type": "Float"},
        {"object_id": "l", "name": "luminosity", "type": "Integer"},
    ]


@respx.mock
async def test_provision_device_duplicado_levanta_conflict(fiware):
    respx.post(f"{IOTA}/iot/devices").mock(
        return_value=httpx.Response(409, json={"name": "DUPLICATE_DEVICE_ID"}))
    with pytest.raises(FiwareConflict) as erro:
        await fiware.provision_device(DEVICE)
    assert erro.value.service == "iota"


@respx.mock
async def test_delete_device_remove(fiware):
    rota = respx.delete(f"{IOTA}/iot/devices/vinheria001").mock(return_value=httpx.Response(204))
    await fiware.delete_device("vinheria001")
    assert rota.called


@respx.mock
async def test_delete_device_aceita_404(fiware):
    rota = respx.delete(f"{IOTA}/iot/devices/vinheria001").mock(return_value=httpx.Response(404))
    await fiware.delete_device("vinheria001")
    assert rota.called
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_iota.py -v`
Expected: 6 falhas com `AttributeError: 'FiwareClient' object has no attribute 'provision_service_group'` (e equivalentes).

- [ ] **Passo 3: implementar a seção IoT Agent**

Em `backend/app/services/fiware_client.py`, acrescentar `Device` ao import de schemas:

```python
from app.models.schemas import Device, HealthReport, ServiceHealth
```

E inserir esta seção logo antes de `# ----- Orion: leitura -----`:

```python
    # ----- IoT Agent ---------------------------------------------------------

    async def provision_service_group(self) -> None:
        """Cria o service group da apikey do projeto; se já existe (409), segue.

        timestamp: true faz o IoT Agent preencher TimeInstant a cada leitura,
        e a detecção de offline depende disso.
        """
        corpo = {"services": [{
            "apikey": self._settings.fiware_apikey,
            "cbroker": self.orion_url(""),
            "entity_type": "Thing",
            "resource": "",
            "timestamp": True,
        }]}
        await self._request("iota", "POST", self.iota_url("/iot/services"),
                            json=corpo, aceitar=(409,))

    async def provision_device(self, device: Device) -> None:
        """Provisiona a vinheria no IoT Agent com atributos e comandos.

        O próprio IoT Agent cria a registration dos comandos no Orion; criar
        outra à mão duplica e quebra o encaminhamento (achado da Task 1).
        Device já existente levanta FiwareConflict.
        """
        corpo = {"devices": [{
            "device_id": device.device_id,
            "entity_name": device.entity_id,
            "entity_type": ENTITY_TYPE,
            "protocol": "PDI-IoTA-UltraLight",
            "transport": "MQTT",
            "commands": [{"name": nome, "type": "command"} for nome in COMMANDS],
            "attributes": [
                {"object_id": curto, "name": longo, "type": tipo}
                for curto, longo, tipo in SENSOR_ATTRS
            ],
        }]}
        await self._request("iota", "POST", self.iota_url("/iot/devices"), json=corpo)

    async def delete_device(self, device_id: str) -> None:
        """Remove o device do IoT Agent; se já não existe (404), segue."""
        await self._request("iota", "DELETE", self.iota_url(f"/iot/devices/{device_id}"),
                            aceitar=(404,))
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_iota.py -v`
Expected: 6 testes `PASSED`.

- [ ] **Passo 5: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 34 testes `PASSED`.

- [ ] **Passo 6: commit**

```bash
git add backend/app/services/fiware_client.py backend/tests/test_fiware_iota.py
git commit -m "feat: adiciona provisionamento e remocao de devices no IoT Agent"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 2.5 — Orion: subscriptions, comandos, atributos e remoção (R7.1, R7.4 a R7.7)

**Files:**
- Modify: `backend/app/services/fiware_client.py` (nova seção "Orion: escrita")
- Create: `backend/tests/test_fiware_orion.py`

**Interfaces:**
- Consumes: `FiwareClient._request`, `orion_url`, `SENSOR_ATTRS`, `COMMANDS`, `ENTITY_TYPE`, `ORION_LIST_LIMIT` (2.3).
- Produces: `subscribe_attr(entity_id: str, attr: str) -> str`, `send_command(entity_id: str, command: str, value: str = "") -> None`, `update_attrs(entity_id: str, attrs: dict[str, float]) -> None`, `delete_entity(entity_id: str) -> None`, `delete_subscriptions(entity_id: str) -> int`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_fiware_orion.py`:

```python
"""Testes do FiwareClient contra o Orion: escrita e remoção (spec R7)."""
import json

import httpx
import pytest
import respx

pytestmark = pytest.mark.anyio

ORION = "http://10.0.0.1:1026"
E1 = "urn:ngsi-ld:Vinheria:001"
E2 = "urn:ngsi-ld:Vinheria:002"


def _corpo(rota):
    """JSON enviado na última chamada da rota."""
    return json.loads(rota.calls.last.request.content)


@respx.mock
async def test_subscribe_attr_envia_body_e_devolve_id(fiware):
    rota = respx.post(f"{ORION}/v2/subscriptions").mock(
        return_value=httpx.Response(201, headers={"Location": "/v2/subscriptions/abc123"}))
    assert await fiware.subscribe_attr(E1, "temperature") == "abc123"
    corpo = _corpo(rota)
    assert corpo["subject"] == {
        "entities": [{"id": E1, "type": "Vinheria"}],
        "condition": {"attrs": ["temperature"]},
    }
    assert corpo["notification"] == {
        "http": {"url": "http://sth-comet:8666/notify"},
        "attrs": ["temperature"],
        "attrsFormat": "legacy",
    }


async def test_subscribe_attr_rejeita_atributo_invalido(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.subscribe_attr(E1, "t")
    assert mock.calls.call_count == 0


@respx.mock
async def test_send_command_envia_patch(fiware):
    rota = respx.patch(f"{ORION}/v2/entities/{E2}/attrs").mock(return_value=httpx.Response(204))
    await fiware.send_command(E2, "blink_temp")
    assert _corpo(rota) == {"blink_temp": {"type": "command", "value": ""}}


@respx.mock
async def test_send_command_set_limits_com_valor(fiware):
    rota = respx.patch(f"{ORION}/v2/entities/{E1}/attrs").mock(return_value=httpx.Response(204))
    await fiware.send_command(E1, "set_limits", "12;18;50;70;0;30")
    assert _corpo(rota) == {"set_limits": {"type": "command", "value": "12;18;50;70;0;30"}}


async def test_send_command_rejeita_comando_invalido(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.send_command(E1, "explodir")
    assert mock.calls.call_count == 0


@respx.mock
async def test_update_attrs_envia_post(fiware):
    rota = respx.post(f"{ORION}/v2/entities/{E1}/attrs").mock(return_value=httpx.Response(204))
    await fiware.update_attrs(E1, {"temp_min": 12, "temp_max": 18.5})
    assert _corpo(rota) == {
        "temp_min": {"type": "Number", "value": 12},
        "temp_max": {"type": "Number", "value": 18.5},
    }


@respx.mock
async def test_delete_entity_remove(fiware):
    rota = respx.delete(f"{ORION}/v2/entities/{E1}").mock(return_value=httpx.Response(204))
    await fiware.delete_entity(E1)
    assert rota.called


@respx.mock
async def test_delete_entity_aceita_404(fiware):
    rota = respx.delete(f"{ORION}/v2/entities/{E1}").mock(return_value=httpx.Response(404))
    await fiware.delete_entity(E1)
    assert rota.called


@respx.mock
async def test_delete_subscriptions_apaga_so_as_da_entidade(fiware):
    assinaturas = [
        {"id": "s1", "subject": {"entities": [{"id": E1, "type": "Vinheria"}]}},
        {"id": "s2", "subject": {"entities": [{"id": E2, "type": "Vinheria"}]}},
        {"id": "s3", "subject": {"entities": [{"id": E1, "type": "Vinheria"}]}},
        {"id": "s4", "subject": {"entities": [{"idPattern": ".*"}]}},
    ]
    listagem = respx.get(f"{ORION}/v2/subscriptions").mock(
        return_value=httpx.Response(200, json=assinaturas))
    apaga_s1 = respx.delete(f"{ORION}/v2/subscriptions/s1").mock(return_value=httpx.Response(204))
    apaga_s3 = respx.delete(f"{ORION}/v2/subscriptions/s3").mock(return_value=httpx.Response(204))
    assert await fiware.delete_subscriptions(E1) == 2
    assert apaga_s1.called and apaga_s3.called
    assert listagem.calls.last.request.url.params["limit"] == "1000"
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_orion.py -v`
Expected: 9 falhas com `AttributeError` (`subscribe_attr`, `send_command`, `update_attrs`, `delete_entity`, `delete_subscriptions` não existem).

- [ ] **Passo 3: implementar a seção Orion: escrita**

Em `backend/app/services/fiware_client.py`, logo abaixo de `ORION_LIST_LIMIT = 1000`, acrescentar:

```python
# Nomes longos aceitos em subscriptions e no histórico
_ATRIBUTOS_LONGOS = tuple(longo for _, longo, _ in SENSOR_ATTRS)
```

E inserir esta seção logo depois do método `list_entities` (antes de `# ----- Saúde -----`):

```python
    # ----- Orion: escrita ----------------------------------------------------

    async def subscribe_attr(self, entity_id: str, attr: str) -> str:
        """Assina um atributo da entidade para o STH-Comet guardar o histórico.

        Uma subscription por atributo. O destino é o endereço interno do STH
        na rede Docker (STH_INTERNAL_URL). Devolve o id da subscription.
        """
        if attr not in _ATRIBUTOS_LONGOS:
            raise ValueError(f"atributo inválido: {attr!r}; use um de {_ATRIBUTOS_LONGOS}")
        corpo = {
            "description": f"Notify STH-Comet of {attr} changes",
            "subject": {
                "entities": [{"id": entity_id, "type": ENTITY_TYPE}],
                "condition": {"attrs": [attr]},
            },
            "notification": {
                "http": {"url": f"{self._settings.sth_internal_url}/notify"},
                "attrs": [attr],
                "attrsFormat": "legacy",
            },
        }
        resposta = await self._request("orion", "POST", self.orion_url("/v2/subscriptions"),
                                       json=corpo)
        # O Orion devolve o id no header Location: /v2/subscriptions/<id>
        return resposta.headers.get("Location", "").rstrip("/").split("/")[-1]

    async def send_command(self, entity_id: str, command: str, value: str = "") -> None:
        """Envia um comando à vinheria pelo Orion (que repassa ao IoT Agent).

        `value` só é usado pelo set_limits ("tmin;tmax;hmin;hmax;lmin;lmax").
        """
        if command not in COMMANDS:
            raise ValueError(f"comando inválido: {command!r}; use um de {COMMANDS}")
        corpo = {command: {"type": "command", "value": value}}
        await self._request("orion", "PATCH", self.orion_url(f"/v2/entities/{entity_id}/attrs"),
                            json=corpo)

    async def update_attrs(self, entity_id: str, attrs: dict[str, float]) -> None:
        """Cria ou atualiza atributos numéricos na entidade (ex.: faixa ideal).

        Usa POST (upsert) porque PATCH falha quando o atributo ainda não existe.
        """
        corpo = {nome: {"type": "Number", "value": valor} for nome, valor in attrs.items()}
        await self._request("orion", "POST", self.orion_url(f"/v2/entities/{entity_id}/attrs"),
                            json=corpo)

    async def delete_entity(self, entity_id: str) -> None:
        """Remove a entidade do Orion; se já não existe (404), segue."""
        await self._request("orion", "DELETE", self.orion_url(f"/v2/entities/{entity_id}"),
                            aceitar=(404,))

    async def delete_subscriptions(self, entity_id: str) -> int:
        """Apaga as subscriptions que observam esta entidade e devolve quantas foram."""
        resposta = await self._request("orion", "GET", self.orion_url("/v2/subscriptions"),
                                       params={"limit": ORION_LIST_LIMIT})
        apagadas = 0
        for assinatura in resposta.json():
            entidades = assinatura.get("subject", {}).get("entities", [])
            if any(e.get("id") == entity_id for e in entidades):
                await self._request(
                    "orion", "DELETE",
                    self.orion_url(f"/v2/subscriptions/{assinatura['id']}"),
                    aceitar=(404,),
                )
                apagadas += 1
        return apagadas
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_orion.py -v`
Expected: 9 testes `PASSED`.

- [ ] **Passo 5: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 43 testes `PASSED`.

- [ ] **Passo 6: commit**

```bash
git add backend/app/services/fiware_client.py backend/tests/test_fiware_orion.py
git commit -m "feat: adiciona subscriptions, comandos e remocao de entidades no Orion"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 2.6 — STH-Comet: histórico (R8)

**Files:**
- Modify: `backend/app/services/fiware_client.py` (nova seção "STH-Comet")
- Create: `backend/tests/test_fiware_sth.py`

**Interfaces:**
- Consumes: `FiwareClient._request`, `sth_url`, `_ATRIBUTOS_LONGOS` (2.3 e 2.5).
- Produces: `query_history(entity_type: str, entity_id: str, attr: str, last_n: int | None = None, date_from: str | None = None, date_to: str | None = None) -> list[dict]`, que devolve a lista crua `[{ "recvTime": str, "attrValue": str|number, ... }]`. A Task 3 normaliza para `[{ ts, value }]`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_fiware_sth.py`:

```python
"""Testes do FiwareClient contra o STH-Comet (spec R8)."""
import httpx
import pytest
import respx

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
URL = ("http://10.0.0.1:8666/STH/v1/contextEntities/type/Vinheria"
       f"/id/{E1}/attributes/temperature")
VALORES = [
    {"recvTime": "2026-10-05T22:00:00.000Z", "attrType": "Float", "attrValue": "14.2"},
    {"recvTime": "2026-10-05T22:00:02.000Z", "attrType": "Float", "attrValue": "14.3"},
]


def _resposta_sth(valores):
    """Monta uma resposta no formato do STH-Comet com os valores dados."""
    return {"contextResponses": [{
        "contextElement": {
            "attributes": [{"name": "temperature", "values": valores}],
            "id": E1, "isPattern": False, "type": "Vinheria",
        },
        "statusCode": {"code": "200", "reasonPhrase": "OK"},
    }]}


@respx.mock
async def test_query_history_last_n(fiware):
    rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_resposta_sth(VALORES)))
    assert await fiware.query_history("Vinheria", E1, "temperature", last_n=30) == VALORES
    params = rota.calls.last.request.url.params
    assert params["lastN"] == "30"
    assert rota.calls.last.request.headers["fiware-service"] == "smart"


@respx.mock
async def test_query_history_por_datas(fiware):
    rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_resposta_sth(VALORES)))
    await fiware.query_history("Vinheria", E1, "temperature",
                               date_from="2026-10-05T00:00:00", date_to="2026-10-05T23:59:59")
    params = rota.calls.last.request.url.params
    assert params["dateFrom"] == "2026-10-05T00:00:00"
    assert params["dateTo"] == "2026-10-05T23:59:59"
    assert params["hLimit"] == "500"
    assert params["hOffset"] == "0"
    assert "lastN" not in params


async def test_query_history_sem_janela_falha(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.query_history("Vinheria", E1, "temperature")
    assert mock.calls.call_count == 0


async def test_query_history_dois_modos_falha(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.query_history("Vinheria", E1, "temperature",
                                       last_n=10, date_from="2026-10-05T00:00:00")
    assert mock.calls.call_count == 0


@respx.mock
async def test_query_history_sem_dados_devolve_lista_vazia(fiware):
    respx.get(URL).mock(return_value=httpx.Response(200, json=_resposta_sth([])))
    assert await fiware.query_history("Vinheria", E1, "temperature", last_n=30) == []


@respx.mock
async def test_query_history_resposta_sem_entidade_devolve_lista_vazia(fiware):
    respx.get(URL).mock(return_value=httpx.Response(200, json={"contextResponses": []}))
    assert await fiware.query_history("Vinheria", E1, "temperature", last_n=30) == []
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_sth.py -v`
Expected: 6 falhas com `AttributeError: 'FiwareClient' object has no attribute 'query_history'`.

- [ ] **Passo 3: implementar a seção STH-Comet**

Em `backend/app/services/fiware_client.py`, logo abaixo de `_ATRIBUTOS_LONGOS`, acrescentar:

```python
# Página máxima pedida ao STH quando a consulta é por intervalo de datas
HISTORY_PAGE_LIMIT = 500
```

E inserir esta seção logo antes de `# ----- Saúde -----`:

```python
    # ----- STH-Comet ---------------------------------------------------------

    async def query_history(self, entity_type: str, entity_id: str, attr: str,
                            last_n: int | None = None,
                            date_from: str | None = None,
                            date_to: str | None = None) -> list[dict]:
        """Histórico bruto de um atributo no STH-Comet.

        Use OU last_n (últimos N pontos) OU date_from/date_to (datas ISO 8601).
        Devolve a lista `values` do STH ([{recvTime, attrValue, ...}]), ou []
        quando não há dados.
        """
        por_datas = date_from is not None or date_to is not None
        if last_n is None and not por_datas:
            raise ValueError("informe last_n ou date_from/date_to")
        if last_n is not None and por_datas:
            raise ValueError("use last_n ou date_from/date_to, não os dois")
        if last_n is not None:
            params = {"lastN": last_n}
        else:
            # Consulta por datas exige paginação explícita no STH
            params = {"hLimit": HISTORY_PAGE_LIMIT, "hOffset": 0}
            if date_from is not None:
                params["dateFrom"] = date_from
            if date_to is not None:
                params["dateTo"] = date_to
        caminho = (f"/STH/v1/contextEntities/type/{entity_type}"
                   f"/id/{entity_id}/attributes/{attr}")
        resposta = await self._request("sth", "GET", self.sth_url(caminho), params=params)
        try:
            return resposta.json()["contextResponses"][0]["contextElement"]["attributes"][0]["values"]
        except (KeyError, IndexError, TypeError):
            return []
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_sth.py -v`
Expected: 6 testes `PASSED`.

- [ ] **Passo 5: rodar a suíte inteira e conferir o tamanho do arquivo**

Run: `.venv/Scripts/python -m pytest -v` e depois `wc -l app/services/fiware_client.py`
Expected: 49 testes `PASSED`; o arquivo com menos de ~300 linhas. Se passar muito disso, **não divida por conta própria**: reporte e espere orientação (`CLAUDE.md` §6).

- [ ] **Passo 6: commit**

```bash
git add backend/app/services/fiware_client.py backend/tests/test_fiware_sth.py
git commit -m "feat: adiciona consulta de historico no STH-Comet"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 2.7 — API de configuração e app FastAPI (R5.3, R10)

**Files:**
- Create: `backend/app/api/deps.py`, `backend/app/api/errors.py`, `backend/app/api/routes_config.py`, `backend/app/main.py`
- Create: `backend/tests/test_routes_config.py`

**Interfaces:**
- Consumes: `load_settings`, `Settings`, `ConfigStore`, `connect`, `ConfigUpdate`, `RuntimeConfig`, `HealthReport` (2.2); `FiwareClient`, exceções `Fiware*` (2.3).
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`; objeto `app` para o uvicorn; `app.state.settings`, `app.state.conn`, `app.state.config_store`, `app.state.fiware`; dependências `get_config_store(request) -> ConfigStore` e `get_fiware(request) -> FiwareClient`; `register_error_handlers(app)`. Rotas `GET /api/config`, `PUT /api/config`, `GET /api/config/health`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_routes_config.py`:

```python
"""Testes da API de configuração e da tradução de erros (spec R5.3 e R10)."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.schemas import HealthReport, ServiceHealth
from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)


@pytest.fixture
def app(tmp_path):
    """App de teste com IP fictício e banco temporário."""
    return create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "api.db")))


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


class FiwareFalso:
    """Substitui o FiwareClient nos testes de rota (sem rede)."""

    async def health(self):
        ok = ServiceHealth(ok=True, status_code=200, latency_ms=12)
        return HealthReport(ok=True, ec2_ip="10.0.0.1", orion=ok, iota=ok, sth=ok)

    async def aclose(self):
        pass


def test_get_config(client):
    resposta = client.get("/api/config")
    assert resposta.status_code == 200
    assert resposta.json() == {
        "ec2_ip": "10.0.0.1", "orion_port": 1026, "iota_port": 4041,
        "sth_port": 8666, "poll_seconds": 5, "offline_seconds": 30,
    }


def test_get_config_sem_ip(tmp_path):
    app = create_app(Settings(fiware_host="", database_path=str(tmp_path / "sem_ip.db")))
    with TestClient(app) as cliente:
        resposta = cliente.get("/api/config")
    assert resposta.status_code == 200
    assert resposta.json()["ec2_ip"] == ""


def test_put_config_atualiza_e_normaliza(client):
    resposta = client.put("/api/config",
                          json={"ec2_ip": " http://20.0.0.2:1026/ ", "poll_seconds": 10})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ec2_ip"] == "20.0.0.2"
    assert corpo["poll_seconds"] == 10
    assert corpo["orion_port"] == 1026
    assert client.get("/api/config").json()["ec2_ip"] == "20.0.0.2"


def test_put_config_invalido_devolve_422(client):
    assert client.put("/api/config", json={"ec2_ip": "   "}).status_code == 422
    assert client.put("/api/config", json={"orion_port": 70000}).status_code == 422
    assert client.get("/api/config").json()["ec2_ip"] == "10.0.0.1"


def test_get_health(app):
    app.state.fiware = FiwareFalso()
    with TestClient(app) as cliente:
        resposta = cliente.get("/api/config/health")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ok"] is True
    assert corpo["orion"]["latency_ms"] == 12


@pytest.mark.parametrize("erro, status", [
    (FiwareUnavailable("orion", "sem conexão"), 503),
    (FiwareNotFound("orion", "não existe", 404), 404),
    (FiwareConflict("iota", "já existe", 409), 409),
    (FiwareError("sth", "quebrou", 500), 502),
])
def test_handler_traduz_erros_fiware(app, erro, status):
    async def rota_que_falha():
        raise erro

    app.add_api_route("/teste-erro", rota_que_falha)
    with TestClient(app) as cliente:
        resposta = cliente.get("/teste-erro")
    assert resposta.status_code == status
    assert resposta.json() == {"detail": erro.message, "service": erro.service}


def test_cors_libera_front(client):
    resposta = client.options("/api/config", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resposta.headers["access-control-allow-origin"] == "http://localhost:5173"
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_routes_config.py -v`
Expected: erro de coleta com `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Passo 3: implementar `backend/app/api/deps.py`**

```python
"""
Dependências do FastAPI.

As rotas recebem o ConfigStore e o FiwareClient por injeção, lidos de
app.state, em vez de importar instâncias globais. Assim os testes trocam
qualquer peça sem mexer nas rotas.
"""
from fastapi import Request

from app.core.config import ConfigStore
from app.services.fiware_client import FiwareClient


def get_config_store(request: Request) -> ConfigStore:
    """ConfigStore da aplicação."""
    return request.app.state.config_store


def get_fiware(request: Request) -> FiwareClient:
    """Cliente FIWARE da aplicação."""
    return request.app.state.fiware
```

- [ ] **Passo 4: implementar `backend/app/api/errors.py`**

```python
"""
Tradução das exceções do FIWARE em respostas HTTP.

Os services levantam FiwareError e suas subclasses; aqui elas viram JSON
{ "detail", "service" } com um status coerente, para o front-end mostrar
uma mensagem clara em vez de um erro 500 genérico.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)


def _status_para(erro: FiwareError) -> int:
    """Status HTTP da resposta para cada tipo de falha do FIWARE."""
    if isinstance(erro, FiwareUnavailable):
        return 503
    if isinstance(erro, FiwareNotFound):
        return 404
    if isinstance(erro, FiwareConflict):
        return 409
    return 502


def register_error_handlers(app: FastAPI) -> None:
    """Registra no app o tradutor de FiwareError."""

    @app.exception_handler(FiwareError)
    async def _trata_fiware(request: Request, erro: FiwareError) -> JSONResponse:
        return JSONResponse(status_code=_status_para(erro),
                            content={"detail": erro.message, "service": erro.service})
```

- [ ] **Passo 5: implementar `backend/app/api/routes_config.py`**

```python
"""
Rotas de configuração: ver e trocar o IP do FIWARE e os intervalos em
runtime, e testar a saúde dos componentes no IP atual.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_config_store, get_fiware
from app.core.config import ConfigStore
from app.models.schemas import ConfigUpdate, HealthReport, RuntimeConfig
from app.services.fiware_client import FiwareClient

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=RuntimeConfig)
def read_config(store: ConfigStore = Depends(get_config_store)) -> RuntimeConfig:
    """Configuração em uso agora."""
    return store.get()


@router.put("", response_model=RuntimeConfig)
def write_config(changes: ConfigUpdate,
                 store: ConfigStore = Depends(get_config_store)) -> RuntimeConfig:
    """Atualiza só os campos enviados; vale na hora, sem reiniciar."""
    return store.update(changes)


@router.get("/health", response_model=HealthReport)
async def read_health(fiware: FiwareClient = Depends(get_fiware)) -> HealthReport:
    """Testa Orion, IoT Agent e STH-Comet no IP configurado."""
    return await fiware.health()
```

- [ ] **Passo 6: implementar `backend/app/main.py`**

```python
"""
Ponto de entrada do backend FastAPI (Smart Solutions).

create_app() monta a aplicação: lê a configuração, abre o SQLite, cria o
cliente FIWARE e registra CORS, tradução de erros e rotas. Os testes chamam
create_app() com Settings próprios; o uvicorn usa o objeto `app` do fim do
arquivo (uvicorn app.main:app --reload, rodando de dentro de backend/).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_config
from app.api.errors import register_error_handlers
from app.core.config import ConfigStore, Settings, load_settings
from app.core.db import connect
from app.services.fiware_client import FiwareClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida do app: no desligamento, fecha o pool HTTP e o SQLite."""
    yield
    await app.state.fiware.aclose()
    app.state.conn.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação com todas as dependências ligadas."""
    settings = settings or load_settings()
    conn = connect(settings.database_path)
    store = ConfigStore(conn, settings)

    app = FastAPI(
        title="Smart Solutions — API de Vinherias",
        description="Backend do monitoramento de vinherias integrado ao FIWARE.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.conn = conn
    app.state.config_store = store
    app.state.fiware = FiwareClient(store, settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(routes_config.router)
    return app


app = create_app()
```

- [ ] **Passo 7: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_routes_config.py -v`
Expected: 10 testes `PASSED` (6 funções simples + 1 parametrizada com 4 casos).

- [ ] **Passo 8: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 59 testes `PASSED`, nenhum aviso de requisição real.

- [ ] **Passo 9: conferir a regra de camadas**

Run (de dentro de `backend/`): `grep -rn "import httpx" app/`
Expected: só `app/services/fiware_client.py`.

- [ ] **Passo 10: commit**

```bash
git add backend/app/api backend/app/main.py backend/tests/test_routes_config.py
git commit -m "feat: adiciona API de configuracao com health do FIWARE"
```

**Pare aqui para revisão do usuário.**

---

## Subtarefa 2.8 — Verificação real contra a EC2 e fechamento

**Requisitos:** EC2 ligada, containers de pé, `backend/.env` com `FIWARE_HOST` preenchido. Wokwi da `vinheria001` rodando (opcional, mas recomendado).

**Files:**
- Modify: `PLANO-CP5-VINHERIA.md` (marcar a Task 2), `README.md` (roadmap)

- [ ] **Passo 1: subir o backend**

Run (de dentro de `backend/`, em segundo plano): `.venv/Scripts/python -m uvicorn app.main:app --reload`
Expected: log `Uvicorn running on http://127.0.0.1:8000` e `Application startup complete`.

- [ ] **Passo 2: Swagger**

Abrir `http://localhost:8000/docs`.
Expected: aparecem `GET /api/config`, `PUT /api/config` e `GET /api/config/health`.

- [ ] **Passo 3: saúde no IP do `.env`**

Run: `curl -s http://localhost:8000/api/config/health`
Expected: `"ok":true`, com `orion`, `iota` e `sth` em `"ok":true` e `latency_ms` preenchido. Se der `false`, **pare**, cole a resposta e reporte (não altere código).

- [ ] **Passo 4: troca de IP em runtime**

Run:
```bash
curl -s -X PUT http://localhost:8000/api/config -H "Content-Type: application/json" -d "{\"ec2_ip\": \"10.255.255.1\"}"
curl -s http://localhost:8000/api/config/health
```
Expected: o `PUT` devolve `"ec2_ip":"10.255.255.1"`; o health devolve `"ok":false` com erro de tempo esgotado ou de conexão, em até ~5 s, sem reiniciar o uvicorn.

Depois, voltar ao IP elástico (trocar `<IP_ELASTICO>` pelo valor do `.env`) e conferir:
```bash
curl -s -X PUT http://localhost:8000/api/config -H "Content-Type: application/json" -d "{\"ec2_ip\": \"<IP_ELASTICO>\"}"
curl -s http://localhost:8000/api/config/health
```
Expected: `"ok":true` de novo.

- [ ] **Passo 5: smoke de leitura da frota**

Run (de dentro de `backend/`, com o uvicorn parado ou em outro terminal):
```bash
.venv/Scripts/python -c "import asyncio; from app.main import app; print(asyncio.run(app.state.fiware.list_entities()))"
```
Expected: uma lista com `urn:ngsi-ld:Vinheria:001` (e `002`, se estiver provisionada), contendo `temperature`, `humidity`, `luminosity` e `TimeInstant`. **Não** rodar provisionamento nem remoção contra a EC2 nesta task.

- [ ] **Passo 6: conferir segredos fora do Git**

Run (na raiz): `git status --short`
Expected: nenhum `backend/.env` nem `*.db` listado.

- [ ] **Passo 7: marcar a Task 2 como feita**

Em `PLANO-CP5-VINHERIA.md`, na seção `### Task 2`, marcar os passos com `[x]` e acrescentar logo abaixo do título uma nota curta: `> **FEITA em <data>** — executada pelo plano docs/specs/task-2-backend-config-fiware/plan.md (commits <primeiro>..<último>).`. Em `README.md`, na seção Roadmap, marcar `[x] Backend: configuração e cliente FIWARE`.

- [ ] **Passo 8: commit**

```bash
git add PLANO-CP5-VINHERIA.md README.md
git commit -m "docs: fecha task 2 com backend de configuracao e cliente FIWARE"
```

**Fim da Task 2. Pare para revisão do usuário.**

---

## Como verificar (aceite final)

Os seis itens da seção 6 da [`spec.md`](spec.md), todos com evidência colada no chat:

1. `pytest -v` → 59 testes passando, sem rede.
2. Swagger com as três rotas.
3. Health `ok: true` no IP do `.env`.
4. Troca de IP em runtime: falha no IP falso e volta a `ok: true`, sem reiniciar.
5. `list_entities()` real devolvendo as vinherias com `TimeInstant`.
6. `.env` e `*.db` fora do Git.
