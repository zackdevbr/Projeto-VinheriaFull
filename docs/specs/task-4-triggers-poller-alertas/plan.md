# Task 4 — Faixa editável, motor de alertas, frota, configuração do ESP32 e backup — Plano de execução

> **Para quem executa (Sonnet):** use `superpowers:executing-plans` (ou `superpowers:subagent-driven-development`). Os passos usam checkbox (`- [ ]`). Execute **uma subtarefa por vez**, informe o resultado de cada passo e **pare para revisão do usuário ao fim de cada subtarefa** (`CLAUDE.md` §2 e §4). Se algo não bater com a spec, pare e devolva para planejamento; não improvise.

**Objetivo:** o backend vigia a frota sozinho. A cada `poll_seconds`, compara as leituras de cada vinheria com a faixa dela, aciona o alerta certo no ESP32, detecta vinheria offline e EC2 fora do ar, registra os alertas e publica o retrato da frota. O ESP32 nasce sem faixa, mostra "Configure o dispositivo" e só aceita alertas depois de receber a faixa cadastrada. A faixa é editável e chega ao ESP32 na hora, os alertas podem ser disparados à mão, e o banco ganha backup automático.

**Arquitetura:** `Database` (SQLite com `RLock`) é a base. `trigger_rules` concentra as decisões puras. `AlertTracker` guarda os alertas abertos em memória, espelhando o `AlertLog`. `TriggerEngine` orquestra cada ciclo: lê o Orion, decide configuração, offline e alertas, manda comandos pelo `FiwareClient` e publica no `FleetState`. `DeviceControl` atende o painel (faixa e comandos manuais). `BackupService` copia o banco em fundo. No firmware, `limites.h` faz o parse da faixa, e o `.ino` ganha o estado "não configurado".

**Stack:** Python 3.12, FastAPI 0.142.2, Pydantic 2.13.5, httpx 0.28.1, SQLite, pytest + respx + `anyio`; firmware C++ no Wokwi. Nenhuma dependência nova.

**Spec:** [`spec.md`](spec.md) — requisitos R1 a R14, fatos F1 a F5 e decisões D1 a D15. Leia antes de começar.

> **Estado em 10/10/2026:** feitas as subtarefas 4.1 a 4.17. 281 testes passando. Desvios: separador do `set_limits` trocado para vírgula (o Orion rejeita `;`); `trigger_engine.py` com 284 linhas (mantido); verificação real feita com um Wokwi só (`vinheria001`), sem a 002. Detalhes em `PLANO-CP5-VINHERIA.md`, seção da Task 4.

## Global Constraints

- Comandos do backend rodam de dentro de `backend/` com `.venv/Scripts/python -m ...`.
- Nenhuma dependência nova; `requirements.txt` e `libraries.txt` não mudam.
- Comentários e docstrings **em português**, explicando o propósito de cada módulo e de cada função não óbvia.
- Só `app/services/fiware_base.py` importa `httpx` em código de produção. Rotas não importam `httpx` nem chamam `FiwareClient` direto.
- Nunca fazer `await` dentro de um bloco `with db:` (spec R1.4).
- Nomes canônicos: device `vinheria00N`, entity `urn:ngsi-ld:Vinheria:00N`, type `Vinheria`; atributos `temperature`, `humidity`, `luminosity` (+ `configured`, curto `c`); comandos `blink_temp`, `blink_hum`, `blink_lux`, `alert_off`, `set_limits` (valor `"tmin,tmax,hmin,hmax,lmin,lmax"`); faixa no Orion `temp_min`…`lux_max`.
- Firmware: nenhum `delay()` nos padrões de alerta nem na tela de configuração (só `millis()`).
- Nenhum arquivo novo passa de ~250 linhas.
- Testes nunca acessam a rede nem gravam fora de `tmp_path`.
- Commits: mensagem em português, imperativo, uma linha, prefixo `feat:`/`fix:`/`test:`/`chore:`/`docs:`, **sem linha de co-author** (`CLAUDE.md` §8 prevalece sobre qualquer lembrete de atribuição).
- Suíte de partida: **162 testes passando** (fim da Task 3, medido em 08/10/2026). A contagem esperada ao fim de cada subtarefa está no passo de verificação; se der diferente, reporte antes de seguir.

## Review Focus

Situações que um usuário real vai encontrar e que a spec implica. Cada uma tem teste na subtarefa indicada.

1. **ESP32 reinicia com alerta aberto:** tem que receber a faixa primeiro, mostrar "Configure o dispositivo" e só depois voltar a apitar, sem alerta duplicado. Teste `test_reinicio_do_esp32_reenvia_faixa_e_depois_o_alerta` (4.11).
2. **EC2 cai com o poller rodando e depois volta:** um único alerta da EC2, frota inteira offline no painel, e nenhum alerta falso por vinheria enquanto os ESP32 reconectam. Testes `test_ec2_fora_marca_offline_com_um_alerta` e `test_leitura_velha_logo_apos_a_volta_nao_abre_offline` (4.11).
3. **Duas anomalias ao mesmo tempo e só uma normaliza:** o ESP32 sai do padrão da que normalizou. Teste `test_duas_anomalias_temperatura_por_ultimo` (4.10).
4. **Adega escura com alerta de excesso de luz** (`lux_min = 0`, luz volta a 0): o alerta fecha. Teste `test_histerese_so_vale_do_lado_violado` (4.10).
5. **Operador dispara alerta à mão:** o motor não desfaz no ciclo seguinte; e vinheria configurando ou offline recusa com 409. Testes `test_segunda_passada_sem_mudanca_nao_envia_nada` (4.10) e `test_send_command_configurando_recusa` (4.12).

---

## Subtarefa 4.1 — Banco com lock entre threads (R1)

**Files:**
- Modify: `backend/app/core/db.py`
- Modify: `backend/app/core/config.py`, `backend/app/services/limits.py`, `backend/app/services/device_registry.py` (só anotação de tipo)
- Create: `backend/tests/test_db_concurrency.py`

**Interfaces:**
- Consumes: `SCHEMA`, `connect` (Task 2).
- Produces: `Result`, `Database` (`execute`, `with`, `backup_to`, `close`); `connect(path) -> Database`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_db_concurrency.py`:

```python
"""Testes do banco compartilhado entre threads (spec R1)."""
import threading

import pytest

from app.core.db import Database

INSERE_ALERTA = ("INSERT INTO alerts (device_id, attr, value, opened_at) "
                 "VALUES ('vinheria001', 'temperature', 21, '2026-10-08T12:00:00+00:00')")


def test_connect_devolve_database(conn):
    assert isinstance(conn, Database)


def test_execute_devolve_linhas_e_lastrowid(conn):
    with conn:
        resultado = conn.execute(INSERE_ALERTA)
    assert resultado.lastrowid == 1
    assert resultado.rowcount == 1
    linhas = conn.execute("SELECT id, attr FROM alerts")
    assert [tuple(linha) for linha in linhas] == [(1, "temperature")]
    assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1
    assert conn.execute("SELECT * FROM alerts WHERE id = 99").fetchone() is None
    assert len(conn.execute("SELECT * FROM alerts").fetchall()) == 1


def test_with_faz_commit_e_rollback(conn):
    with conn:
        conn.execute(INSERE_ALERTA)
    with pytest.raises(RuntimeError):
        with conn:
            conn.execute(INSERE_ALERTA)
            raise RuntimeError("falha no meio")
    assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1


def test_transacoes_de_threads_diferentes_nao_se_misturam(conn):
    """O rollback de uma thread não pode desfazer a transação da outra (poller × PUT)."""
    poller_gravou = threading.Event()
    rota_terminou = threading.Event()

    def poller():
        with conn:
            conn.execute(INSERE_ALERTA)
            poller_gravou.set()
            # Sem lock, a rota entra nesta mesma transação e o rollback dela leva o alerta
            rota_terminou.wait(timeout=0.5)

    def rota_que_falha():
        poller_gravou.wait(timeout=2)
        try:
            with conn:
                conn.execute("INSERT INTO config (key, value) VALUES ('x', '1')")
                raise RuntimeError("falha no meio da rota")
        except RuntimeError:
            pass
        finally:
            rota_terminou.set()

    threads = [threading.Thread(target=poller), threading.Thread(target=rota_que_falha)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM config WHERE key = 'x'").fetchone()[0] == 0
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_db_concurrency.py -v`
Expected: erro de coleta `ImportError: cannot import name 'Database' from 'app.core.db'`.

(O cenário do teste de concorrência já foi reproduzido no planejamento contra a conexão crua de hoje: o alerta do poller sumiu, `alertas: 0`.)

- [ ] **Passo 3: implementar `Database` em `backend/app/core/db.py`**

Substituir o arquivo inteiro por:

```python
"""
Banco local SQLite do backend.

Guarda o que não mora no FIWARE: configuração de runtime, cadastro das
vinherias (nome e cidade), faixas ideais (triggers) e histórico de alertas.
O schema é criado na abertura, então um banco novo já nasce pronto.

A conexão é uma só e é usada por threads diferentes (rotas síncronas no
threadpool do FastAPI, poller e rotas assíncronas no loop de eventos). O
Database embrulha a conexão com um lock para que duas transações nunca se
misturem: sem ele, o rollback de uma thread desfaria o que a outra ainda
estava gravando.
"""
import sqlite3
import threading

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


class Result:
    """Resultado de um comando SQL com as linhas já lidas.

    As linhas são lidas ainda dentro do lock, para nenhum cursor ficar
    aberto e ser consumido enquanto outra thread usa a conexão.
    """

    def __init__(self, cursor: sqlite3.Cursor):
        self._linhas = cursor.fetchall()
        self.rowcount = cursor.rowcount
        self.lastrowid = cursor.lastrowid

    def fetchone(self) -> sqlite3.Row | None:
        """Primeira linha, ou None se não houver."""
        return self._linhas[0] if self._linhas else None

    def fetchall(self) -> list[sqlite3.Row]:
        """Todas as linhas."""
        return list(self._linhas)

    def __iter__(self):
        return iter(self._linhas)


class Database:
    """Conexão SQLite protegida por um lock reentrante.

    - `db.execute(sql, params)` roda sob o lock e devolve um Result.
    - `with db:` segura o lock durante a transação inteira: commit no fim,
      rollback se houver exceção.

    Regra: nunca fazer `await` dentro de um `with db:`. O lock é por thread
    e todas as corrotinas dividem a mesma thread, então ele não separa uma
    corrotina da outra.
    """

    def __init__(self, conexao: sqlite3.Connection):
        self._conn = conexao
        self._lock = threading.RLock()

    def execute(self, sql: str, params: tuple = ()) -> Result:
        """Executa um comando SQL sob o lock."""
        with self._lock:
            return Result(self._conn.execute(sql, params))

    def __enter__(self) -> "Database":
        self._lock.acquire()
        try:
            self._conn.__enter__()
        except BaseException:
            self._lock.release()
            raise
        return self

    def __exit__(self, tipo, valor, rastro):
        try:
            return self._conn.__exit__(tipo, valor, rastro)
        finally:
            self._lock.release()

    def backup_to(self, destino: str) -> None:
        """Copia o banco inteiro para `destino` com a API de backup do sqlite3.

        Roda sob o lock, então a cópia nunca pega uma transação pela metade.
        """
        with self._lock:
            alvo = sqlite3.connect(destino)
            try:
                self._conn.backup(alvo)
            finally:
                alvo.close()

    def close(self) -> None:
        """Fecha a conexão."""
        with self._lock:
            self._conn.close()


def connect(path: str) -> Database:
    """Abre (ou cria) o banco em `path`, garante o schema e devolve o Database.

    check_same_thread=False porque threads diferentes usam a mesma conexão;
    quem impede que as transações se misturem é o lock do Database.
    """
    conexao = sqlite3.connect(path, check_same_thread=False)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.executescript(SCHEMA)
    conexao.commit()
    return Database(conexao)
```

- [ ] **Passo 4: trocar as anotações de tipo**

Em `backend/app/core/config.py`: trocar `import sqlite3` por `from app.core.db import Database` (junto dos imports de `app`) e a assinatura do `ConfigStore` por:

```python
    def __init__(self, conn: Database, settings: Settings):
```

Em `backend/app/services/limits.py`: trocar `import sqlite3` por `from app.core.db import Database` e a assinatura por:

```python
    def __init__(self, conn: Database):
```

Em `backend/app/services/device_registry.py`: **manter** `import sqlite3` (usado por `sqlite3.Row` e `sqlite3.IntegrityError`), acrescentar `from app.core.db import Database` junto dos imports de `app` e trocar a assinatura por:

```python
    def __init__(self, conn: Database, fiware: FiwareClient, limits: LimitsStore):
```

- [ ] **Passo 5: rodar os testes novos e a suíte inteira**

Run: `.venv/Scripts/python -m pytest tests/test_db_concurrency.py -v` → 4 passed.
Run: `.venv/Scripts/python -m pytest -q` → **166 passed**.

- [ ] **Passo 6: commit**

```bash
git add app/core/db.py app/core/config.py app/services/limits.py app/services/device_registry.py tests/test_db_concurrency.py
git commit -m "fix: protege a conexao SQLite compartilhada com lock entre threads"
```

---

## Subtarefa 4.2 — Settings de backup e tarefas de fundo (R2.1)

**Files:**
- Modify: `backend/app/core/config.py`, `backend/.env.example`, `backend/tests/test_config.py`

**Interfaces:**
- Produces: `Settings.backup_dir: str = ""`, `backup_minutes: int = 10`, `backup_keep: int = 20`, `run_background: bool = False`; `DEFAULT_BACKUP_DIR`.

- [ ] **Passo 1: atualizar os testes de config (falham)**

Em `backend/tests/test_config.py`, trocar a tupla `VARIAVEIS` por:

```python
VARIAVEIS = (
    "FIWARE_HOST", "ORION_PORT", "IOTA_PORT", "STH_PORT",
    "FIWARE_SERVICE", "FIWARE_SERVICEPATH", "FIWARE_APIKEY", "STH_INTERNAL_URL",
    "POLL_SECONDS", "OFFLINE_SECONDS", "HTTP_TIMEOUT_SECONDS",
    "DATABASE_PATH", "CORS_ORIGINS",
    "BACKUP_DIR", "BACKUP_MINUTES", "BACKUP_KEEP",
)
```

Trocar `test_load_settings_usa_defaults` por:

```python
def test_load_settings_usa_defaults(ambiente_limpo):
    s = load_settings(env_file=None)
    # Banco e backup são resolvidos para caminhos absolutos, e a produção liga o fundo
    assert s == Settings(database_path=s.database_path, backup_dir=s.backup_dir,
                         run_background=True)
    assert s.fiware_host == ""
    assert (s.orion_port, s.iota_port, s.sth_port) == (1026, 4041, 8666)
    assert (s.fiware_service, s.fiware_servicepath, s.fiware_apikey) == ("smart", "/", "TEF")
    assert s.sth_internal_url == "http://sth-comet:8666"
    assert (s.poll_seconds, s.offline_seconds) == (5, 30)
    assert s.cors_origins == ("http://localhost:5173",)
    assert Path(s.backup_dir) == Path.home() / "SmartSolutions" / "backups"
    assert (s.backup_minutes, s.backup_keep) == (10, 20)
```

E acrescentar ao fim do arquivo:

```python
def test_load_settings_le_backup_do_ambiente(ambiente_limpo, tmp_path):
    ambiente_limpo.setenv("BACKUP_DIR", str(tmp_path / "bk"))
    ambiente_limpo.setenv("BACKUP_MINUTES", "3")
    ambiente_limpo.setenv("BACKUP_KEEP", "7")
    s = load_settings(env_file=None)
    assert (s.backup_dir, s.backup_minutes, s.backup_keep) == (str(tmp_path / "bk"), 3, 7)


def test_settings_direto_desliga_backup_e_fundo():
    """Testes criam Settings direto: nada de backup na pasta do usuário nem poller."""
    s = Settings()
    assert s.backup_dir == ""
    assert s.run_background is False
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: FAIL com `TypeError: Settings.__init__() got an unexpected keyword argument 'backup_dir'` (ou `AttributeError`).

- [ ] **Passo 3: ampliar `backend/app/core/config.py`**

Logo depois de `BACKEND_DIR = ...`, acrescentar:

```python
# Pasta padrão dos backups do banco: fora do repositório (o *.db é ignorado
# pelo Git) e na pasta do usuário, para sobreviver a um clone novo
DEFAULT_BACKUP_DIR = Path.home() / "SmartSolutions" / "backups"
```

No `Settings`, acrescentar ao fim da classe (depois de `cors_origins`):

```python
    # Backup do banco. Pasta vazia desliga: é o padrão da classe, usado nos
    # testes; load_settings preenche com DEFAULT_BACKUP_DIR
    backup_dir: str = ""
    backup_minutes: int = 10
    backup_keep: int = 20
    # Poller e backup em fundo: só load_settings (produção) liga
    run_background: bool = False
```

No `return Settings(...)` de `load_settings`, acrescentar ao fim dos argumentos:

```python
        backup_dir=_env("BACKUP_DIR", str(DEFAULT_BACKUP_DIR)),
        backup_minutes=int(_env("BACKUP_MINUTES", p.backup_minutes)),
        backup_keep=int(_env("BACKUP_KEEP", p.backup_keep)),
        run_background=True,
```

E acrescentar ao fim da docstring de `load_settings`:

```
    Liga o poller e o backup em fundo (run_background), que ficam
    desligados quando os testes criam Settings direto.
```

- [ ] **Passo 4: documentar no `backend/.env.example`**

Acrescentar ao fim:

```
# Backup automático do banco (vinheria.db), sempre fora do repositório.
# Vazio usa ~/SmartSolutions/backups. Pode apontar para uma pasta do OneDrive
# para o cadastro sobreviver a uma troca de máquina.
BACKUP_DIR=
# Intervalo entre backups (minutos) e quantos backups manter
BACKUP_MINUTES=10
BACKUP_KEEP=20
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v` → todos passam.
Run: `.venv/Scripts/python -m pytest -q` → **168 passed**.

- [ ] **Passo 6: commit**

```bash
git add app/core/config.py .env.example tests/test_config.py
git commit -m "feat: adiciona configuracao de backup e de tarefas em fundo"
```

---

## Subtarefa 4.3 — Serviço de backup e restauração automática (R2.2–R2.4)

**Files:**
- Create: `backend/app/core/backup.py`, `backend/tests/test_backup.py`

**Interfaces:**
- Consumes: `Database.backup_to`, `connect`, fixtures `conn`, `cadastrar`, `settings`.
- Produces: `list_backups(dir) -> list[Path]`, `restore_if_missing(database_path, backup_dir) -> Path | None`, `BackupService(db, backup_dir, keep, minutes, clock=datetime.now, sleep=asyncio.sleep)` com `enabled`, `backup_now() -> Path | None`, `async run()`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_backup.py`:

```python
"""Testes do backup do banco (spec R2.2 a R2.4)."""
import sqlite3
from datetime import datetime, timedelta

import pytest

from app.core.backup import BackupService, list_backups, restore_if_missing
from app.core.db import connect

pytestmark = pytest.mark.anyio


class _Parar(BaseException):
    """Interrompe um laço infinito no teste (não é capturada como Exception)."""


def _relogio(inicio=datetime(2026, 10, 8, 12, 0, 0)):
    """Relógio que avança 1 minuto a cada chamada (nomes de backup distintos)."""
    estado = {"agora": inicio - timedelta(minutes=1)}

    def _agora():
        estado["agora"] += timedelta(minutes=1)
        return estado["agora"]
    return _agora


def _ids(caminho):
    conexao = sqlite3.connect(caminho)
    ids = [linha[0] for linha in conexao.execute("SELECT device_id FROM devices")]
    conexao.close()
    return ids


def test_backup_now_grava_copia_legivel(conn, cadastrar, tmp_path):
    cadastrar("001")
    servico = BackupService(conn, str(tmp_path / "bk"), keep=20, minutes=10, clock=_relogio())
    caminho = servico.backup_now()
    assert caminho.name == "vinheria-20261008-120000.db"
    assert _ids(caminho) == ["vinheria001"]


def test_backup_mantem_so_os_mais_recentes(conn, tmp_path):
    servico = BackupService(conn, str(tmp_path / "bk"), keep=3, minutes=10, clock=_relogio())
    for _ in range(5):
        servico.backup_now()
    assert [p.name for p in list_backups(tmp_path / "bk")] == [
        "vinheria-20261008-120400.db",
        "vinheria-20261008-120300.db",
        "vinheria-20261008-120200.db",
    ]


def test_backup_desligado_sem_pasta(conn):
    servico = BackupService(conn, "", keep=20, minutes=10)
    assert servico.enabled is False
    assert servico.backup_now() is None


def test_list_backups_pasta_inexistente(tmp_path):
    assert list_backups(tmp_path / "nao-existe") == []


def test_restaura_quando_banco_nao_existe(conn, cadastrar, tmp_path):
    cadastrar("001")
    pasta = tmp_path / "bk"
    BackupService(conn, str(pasta), keep=20, minutes=10, clock=_relogio()).backup_now()
    novo = tmp_path / "outra-maquina" / "vinheria.db"
    restaurado = restore_if_missing(str(novo), str(pasta))
    assert restaurado == list_backups(pasta)[0]
    banco = connect(str(novo))
    assert [linha["device_id"] for linha in banco.execute("SELECT device_id FROM devices")] \
        == ["vinheria001"]
    banco.close()


def test_nao_restaura_se_banco_existe(conn, cadastrar, settings, tmp_path):
    cadastrar("001")
    pasta = tmp_path / "bk"
    BackupService(conn, str(pasta), keep=20, minutes=10, clock=_relogio()).backup_now()
    with conn:
        conn.execute("DELETE FROM devices")
    assert restore_if_missing(settings.database_path, str(pasta)) is None
    assert conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 0


def test_nao_restaura_sem_backup(tmp_path):
    novo = tmp_path / "vinheria.db"
    assert restore_if_missing(str(novo), str(tmp_path / "bk")) is None
    assert restore_if_missing(str(novo), "") is None
    assert not novo.exists()


async def test_run_grava_backup_a_cada_intervalo(conn, tmp_path):
    esperas = []

    async def sleep_falso(segundos):
        esperas.append(segundos)
        if len(esperas) == 3:
            raise _Parar

    servico = BackupService(conn, str(tmp_path / "bk"), keep=20, minutes=10,
                            clock=_relogio(), sleep=sleep_falso)
    with pytest.raises(_Parar):
        await servico.run()
    assert esperas == [600, 600, 600]
    assert len(list_backups(tmp_path / "bk")) == 2


async def test_run_sobrevive_a_falha_de_disco(conn, tmp_path, monkeypatch):
    esperas = []

    async def sleep_falso(segundos):
        esperas.append(segundos)
        if len(esperas) == 3:
            raise _Parar

    servico = BackupService(conn, str(tmp_path / "bk"), keep=20, minutes=10, sleep=sleep_falso)

    def falha():
        raise OSError("disco cheio")
    monkeypatch.setattr(servico, "backup_now", falha)
    with pytest.raises(_Parar):
        await servico.run()
    assert len(esperas) == 3
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_backup.py -v`
Expected: erro de coleta `ModuleNotFoundError: No module named 'app.core.backup'`.

- [ ] **Passo 3: implementar `backend/app/core/backup.py`**

```python
"""
Backup do banco local (vinheria.db).

O SQLite é o único lugar com nome e cidade das vinherias, a faixa ideal
editada e o histórico de alertas; o FIWARE só guarda as leituras. Este
módulo faz a cópia periódica (API de backup do sqlite3, consistente mesmo
com o backend gravando), apaga os backups mais antigos e restaura o banco
sozinho quando o arquivo some (apagado por engano ou máquina nova).
"""
import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path

from app.core.db import Database

log = logging.getLogger(__name__)

PREFIXO = "vinheria-"
SUFIXO = ".db"


def list_backups(backup_dir: Path) -> list[Path]:
    """Backups da pasta, do mais novo para o mais velho (o nome traz data e hora)."""
    pasta = Path(backup_dir)
    if not pasta.is_dir():
        return []
    return sorted(pasta.glob(f"{PREFIXO}*{SUFIXO}"), reverse=True)


def restore_if_missing(database_path: str, backup_dir: str) -> Path | None:
    """Se o banco não existe e há backup, copia o mais recente no lugar.

    Nunca sobrescreve um banco existente. Devolve o backup usado, ou None.
    """
    destino = Path(database_path)
    if destino.exists() or not backup_dir:
        return None
    backups = list_backups(Path(backup_dir))
    if not backups:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backups[0], destino)
    log.warning("banco %s não existia; restaurado do backup %s", destino, backups[0])
    return backups[0]


class BackupService:
    """Cópias periódicas do banco para uma pasta fora do repositório."""

    def __init__(self, db: Database, backup_dir: str, keep: int, minutes: int,
                 clock=datetime.now, sleep=asyncio.sleep):
        self._db = db
        self._pasta = Path(backup_dir) if backup_dir else None
        self._keep = keep
        self._minutes = minutes
        self._clock = clock
        self._sleep = sleep

    @property
    def enabled(self) -> bool:
        """True quando há pasta de backup configurada."""
        return self._pasta is not None

    def backup_now(self) -> Path | None:
        """Grava um backup agora e apaga os excedentes; None se desligado."""
        if self._pasta is None:
            return None
        self._pasta.mkdir(parents=True, exist_ok=True)
        destino = self._pasta / f"{PREFIXO}{self._clock().strftime('%Y%m%d-%H%M%S')}{SUFIXO}"
        self._db.backup_to(str(destino))
        for antigo in list_backups(self._pasta)[self._keep:]:
            antigo.unlink()
        return destino

    async def run(self) -> None:
        """Laço em fundo: um backup a cada `minutes`. Falha de disco não para o laço."""
        while True:
            await self._sleep(self._minutes * 60)
            try:
                self.backup_now()
            except OSError:
                log.exception("falha ao gravar o backup do banco; tento de novo no próximo intervalo")
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_backup.py -v` → 9 passed.
Run: `.venv/Scripts/python -m pytest -q` → **177 passed**.

- [ ] **Passo 5: commit**

```bash
git add app/core/backup.py tests/test_backup.py
git commit -m "feat: adiciona backup periodico do banco e restauracao quando ele some"
```

---

## Subtarefa 4.4 — Ferramenta de restauração manual (R2.5)

**Files:**
- Create: `backend/app/tools/__init__.py`, `backend/app/tools/restore_backup.py`, `backend/tests/test_restore_backup.py`

**Interfaces:**
- Consumes: `list_backups`, `load_settings`, `Settings`, `connect`.
- Produces: `is_valid_backup(path) -> bool`, `restore(backup, database_path, clock=datetime.now) -> Path | None`, `main(argv=None, settings=None) -> int`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_restore_backup.py`:

```python
"""Testes da ferramenta de restauração manual do banco (spec R2.5)."""
import sqlite3
from datetime import datetime

import pytest

from app.core.config import Settings
from app.core.db import connect
from app.tools.restore_backup import is_valid_backup, main, restore


def _banco_com(caminho, device_id):
    """Cria um banco com uma vinheria cadastrada."""
    banco = connect(str(caminho))
    with banco:
        banco.execute(
            "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
            "VALUES (?, ?, 'Vinheria', 'Cidade', '2026-10-08T12:00:00+00:00')",
            (device_id, "urn:ngsi-ld:Vinheria:" + device_id[-3:]),
        )
    banco.close()


def _ids(caminho):
    conexao = sqlite3.connect(caminho)
    ids = [linha[0] for linha in conexao.execute("SELECT device_id FROM devices")]
    conexao.close()
    return ids


def test_is_valid_backup(tmp_path):
    bom = tmp_path / "bom.db"
    _banco_com(bom, "vinheria001")
    ruim = tmp_path / "ruim.db"
    ruim.write_text("não é sqlite", encoding="utf-8")
    vazio = tmp_path / "vazio.db"
    sqlite3.connect(vazio).close()
    assert is_valid_backup(bom) is True
    assert is_valid_backup(ruim) is False
    assert is_valid_backup(vazio) is False
    assert is_valid_backup(tmp_path / "nao-existe.db") is False


def test_restore_substitui_e_guarda_o_atual(tmp_path):
    atual = tmp_path / "vinheria.db"
    _banco_com(atual, "vinheria001")
    backup = tmp_path / "vinheria-20261008-120000.db"
    _banco_com(backup, "vinheria002")
    salvo = restore(backup, atual, clock=lambda: datetime(2026, 10, 8, 13, 0, 0))
    assert _ids(atual) == ["vinheria002"]
    assert salvo.name == "vinheria.db.antes-da-restauracao-20261008-130000"
    assert _ids(salvo) == ["vinheria001"]


def test_restore_recusa_arquivo_invalido(tmp_path):
    atual = tmp_path / "vinheria.db"
    _banco_com(atual, "vinheria001")
    falso = tmp_path / "falso.db"
    falso.write_text("não é sqlite", encoding="utf-8")
    with pytest.raises(ValueError):
        restore(falso, atual)
    assert _ids(atual) == ["vinheria001"]


def test_main_lista_backups(tmp_path, capsys):
    pasta = tmp_path / "bk"
    pasta.mkdir()
    _banco_com(pasta / "vinheria-20261008-120000.db", "vinheria001")
    settings = Settings(database_path=str(tmp_path / "vinheria.db"), backup_dir=str(pasta))
    assert main([], settings=settings) == 0
    assert "vinheria-20261008-120000.db" in capsys.readouterr().out


def test_main_restaura_pelo_nome_do_arquivo(tmp_path):
    pasta = tmp_path / "bk"
    pasta.mkdir()
    _banco_com(pasta / "vinheria-20261008-120000.db", "vinheria002")
    banco = tmp_path / "vinheria.db"
    settings = Settings(database_path=str(banco), backup_dir=str(pasta))
    assert main(["vinheria-20261008-120000.db"], settings=settings) == 0
    assert _ids(banco) == ["vinheria002"]


def test_main_arquivo_invalido_devolve_erro(tmp_path):
    settings = Settings(database_path=str(tmp_path / "vinheria.db"), backup_dir=str(tmp_path))
    assert main([str(tmp_path / "nao-existe.db")], settings=settings) == 1
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_restore_backup.py -v`
Expected: erro de coleta `ModuleNotFoundError: No module named 'app.tools'`.

- [ ] **Passo 3: criar `backend/app/tools/__init__.py`**

```python
"""Ferramentas de linha de comando do backend (manutenção do banco)."""
```

- [ ] **Passo 4: implementar `backend/app/tools/restore_backup.py`**

```python
"""
Restauração manual do banco a partir de um backup.

Uso, de dentro de backend/ e com o backend PARADO:

    .venv/Scripts/python -m app.tools.restore_backup             # lista os backups
    .venv/Scripts/python -m app.tools.restore_backup <arquivo>   # restaura um deles

O banco atual não se perde: antes de restaurar, ele é copiado para
vinheria.db.antes-da-restauracao-<data>, na mesma pasta.
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from app.core.backup import list_backups
from app.core.config import Settings, load_settings


def is_valid_backup(path: Path) -> bool:
    """True se o arquivo é um banco SQLite com a tabela devices."""
    caminho = Path(path)
    if not caminho.is_file():
        return False
    try:
        conexao = sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True)
        try:
            linha = conexao.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'devices'"
            ).fetchone()
        finally:
            conexao.close()
    except sqlite3.DatabaseError:
        return False
    return linha is not None


def restore(backup: Path, database_path: Path, clock=datetime.now) -> Path | None:
    """Copia o backup no lugar do banco, guardando antes o banco atual.

    Devolve o caminho da cópia do banco anterior (None se não havia banco).
    Levanta ValueError se o arquivo não for um backup válido.
    """
    if not is_valid_backup(backup):
        raise ValueError(f"{backup} não é um backup válido do banco das vinherias")
    banco = Path(database_path)
    salvo = None
    if banco.exists():
        carimbo = clock().strftime("%Y%m%d-%H%M%S")
        salvo = banco.with_name(f"{banco.name}.antes-da-restauracao-{carimbo}")
        shutil.copy2(banco, salvo)
    banco.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, banco)
    return salvo


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    """Sem argumento, lista os backups; com um arquivo, restaura. Devolve o código de saída."""
    argv = sys.argv[1:] if argv is None else argv
    settings = settings or load_settings()
    pasta = Path(settings.backup_dir) if settings.backup_dir else None
    if not argv:
        backups = list_backups(pasta) if pasta else []
        if not backups:
            print(f"Nenhum backup encontrado em {pasta}.")
            return 0
        print(f"Backups em {pasta} (mais novo primeiro):")
        for backup in backups:
            print(f"  {backup.name}")
        print("Para restaurar, com o backend parado: "
              "python -m app.tools.restore_backup <arquivo>")
        return 0
    escolhido = Path(argv[0])
    if not escolhido.exists() and pasta is not None:
        escolhido = pasta / escolhido
    try:
        salvo = restore(escolhido, Path(settings.database_path))
    except ValueError as exc:
        print(exc)
        return 1
    print(f"Banco restaurado de {escolhido}.")
    if salvo:
        print(f"O banco anterior foi guardado em {salvo}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_restore_backup.py -v` → 6 passed.
Run: `.venv/Scripts/python -m pytest -q` → **183 passed**.

- [ ] **Passo 6: commit**

```bash
git add app/tools/__init__.py app/tools/restore_backup.py tests/test_restore_backup.py
git commit -m "feat: adiciona comando para listar e restaurar backups do banco"
```

---

## Subtarefa 4.5 — Modelos da frota e log de alertas (R3)

**Files:**
- Create: `backend/app/models/schemas_fleet.py`, `backend/app/services/alert_log.py`, `backend/tests/fakes.py`, `backend/tests/test_alert_log.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `Database`, `Limits`.
- Produces: `FIWARE_ALERT_ID`, `AlertAttr`, `FleetStatus`, `OfflineReason`, `ManualCommand`, `Alert`, `ActiveAlert`, `SensorValues`, `VinheriaStatus`, `FleetReport`, `LimitsUpdate`, `CommandRequest`, `CommandResult`; `AlertLog(db)`; fixture `alert_log`; `tests/fakes.py` com `status_vinheria(device_id, status)`.

- [ ] **Passo 1: criar `backend/tests/fakes.py` (só o primeiro helper; os outros entram na 4.10)**

```python
"""Peças falsas compartilhadas pelos testes da Task 4 (FIWARE, relógio, frota)."""
from app.models.schemas_fleet import SensorValues, VinheriaStatus


def status_vinheria(device_id: str = "vinheria001", status: str = "ok") -> VinheriaStatus:
    """Um VinheriaStatus mínimo, para testes de frota e de comandos."""
    return VinheriaStatus(device_id=device_id, name="Vinheria", city="Cidade", status=status,
                          current=SensorValues(), active_alerts=[])
```

- [ ] **Passo 2: escrever os testes que falham**

`backend/tests/test_alert_log.py`:

```python
"""Testes do log de alertas (spec R3)."""
from app.models.schemas_fleet import Alert
from tests.fakes import status_vinheria

T0 = "2026-10-08T12:00:00+00:00"


def test_open_grava_e_devolve_alerta(alert_log):
    alerta = alert_log.open("vinheria001", "temperature", 21.5, T0)
    assert isinstance(alerta, Alert)
    assert alerta.id >= 1
    assert (alerta.attr, alerta.value, alerta.opened_at) == ("temperature", 21.5, T0)
    assert alerta.closed_at is None
    assert alerta.duration_seconds is None
    assert alert_log.list() == [alerta]


def test_close_fecha_e_calcula_duracao(alert_log):
    alerta = alert_log.open("vinheria001", "humidity", 40.0, T0)
    alert_log.close(alerta.id, "2026-10-08T12:02:30+00:00")
    fechado = alert_log.list()[0]
    assert fechado.closed_at == "2026-10-08T12:02:30+00:00"
    assert fechado.duration_seconds == 150


def test_close_duas_vezes_mantem_primeiro_fechamento(alert_log):
    alerta = alert_log.open("vinheria001", "humidity", 40.0, T0)
    alert_log.close(alerta.id, "2026-10-08T12:02:30+00:00")
    alert_log.close(alerta.id, "2026-10-08T12:05:00+00:00")
    assert alert_log.list()[0].closed_at == "2026-10-08T12:02:30+00:00"


def test_alerta_offline_sem_valor(alert_log):
    alerta = alert_log.open("fiware", "offline", None, T0)
    assert alerta.value is None
    assert (alert_log.list()[0].device_id, alert_log.list()[0].attr) == ("fiware", "offline")


def test_open_alerts_so_abertos(alert_log):
    a1 = alert_log.open("vinheria001", "temperature", 21.0, T0)
    a2 = alert_log.open("vinheria001", "humidity", 40.0, "2026-10-08T12:01:00+00:00")
    a3 = alert_log.open("vinheria002", "offline", None, "2026-10-08T12:02:00+00:00")
    alert_log.close(a2.id, "2026-10-08T12:03:00+00:00")
    assert [a.id for a in alert_log.open_alerts()] == [a1.id, a3.id]


def test_list_mais_novo_primeiro_e_filtra(alert_log):
    a1 = alert_log.open("vinheria001", "temperature", 21.0, T0)
    a2 = alert_log.open("vinheria002", "humidity", 40.0, "2026-10-08T12:01:00+00:00")
    a3 = alert_log.open("vinheria001", "luminosity", 50.0, "2026-10-08T12:02:00+00:00")
    assert [a.id for a in alert_log.list()] == [a3.id, a2.id, a1.id]
    assert [a.id for a in alert_log.list(device_id="vinheria001")] == [a3.id, a1.id]
    assert [a.id for a in alert_log.list(limit=1)] == [a3.id]


def test_status_vinheria_monta_modelo():
    status = status_vinheria("vinheria003", "configurando")
    assert status.status == "configurando"
    assert status.offline_reason is None
```

Em `backend/tests/conftest.py`, acrescentar o import junto dos demais:

```python
from app.services.alert_log import AlertLog
```

E, ao fim do arquivo:

```python
@pytest.fixture
def alert_log(conn):
    """AlertLog sobre o banco de teste."""
    return AlertLog(conn)
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_alert_log.py -v`
Expected: erro de coleta `ModuleNotFoundError: No module named 'app.services.alert_log'` (vindo do `conftest.py`) ou de `app.models.schemas_fleet`.

- [ ] **Passo 4: criar `backend/app/models/schemas_fleet.py`**

```python
"""
Modelos de dados da Task 4: alertas, comandos manuais, faixa salva e
retrato da frota.

Ficam separados de schemas.py para nenhum arquivo passar de ~250 linhas.
"""
from typing import Literal

from pydantic import BaseModel

from app.models.schemas import Limits

# device_id do alerta que registra a EC2/FIWARE fora do ar (um só para a frota)
FIWARE_ALERT_ID = "fiware"

# Atributo de um alerta: um dos sensores ou o equipamento inteiro offline
AlertAttr = Literal["temperature", "humidity", "luminosity", "offline"]
# Status de uma vinheria na visão geral; "configurando" = ESP32 ligado
# aguardando a faixa (set_limits), sem avaliar alertas
FleetStatus = Literal["ok", "alerta", "offline", "configurando"]
# Por que a vinheria está offline: ela parou de mandar leituras, ou a EC2 caiu
OfflineReason = Literal["sem_leitura", "fiware"]
# Comandos que o painel pode disparar à mão (RF09); set_limits sai só pelo PUT da faixa
ManualCommand = Literal["blink_temp", "blink_hum", "blink_lux", "alert_off"]


class Alert(BaseModel):
    """Um alerta do histórico (RF10); duration_seconds é None enquanto aberto."""
    id: int
    device_id: str
    attr: AlertAttr
    value: float | None = None
    opened_at: str
    closed_at: str | None = None
    duration_seconds: int | None = None


class ActiveAlert(BaseModel):
    """Alerta em aberto, como aparece no retrato da frota."""
    attr: AlertAttr
    value: float | None = None
    since: str


class SensorValues(BaseModel):
    """Valores atuais dos sensores; None quando falta a leitura."""
    temperature: float | None = None
    humidity: float | None = None
    luminosity: float | None = None


class VinheriaStatus(BaseModel):
    """Retrato de uma vinheria no último ciclo do poller."""
    device_id: str
    name: str
    city: str
    status: FleetStatus
    offline_reason: OfflineReason | None = None
    last_seen: str | None = None
    seconds_since: int | None = None
    current: SensorValues
    score: float | None = None
    active_alerts: list[ActiveAlert]


class FleetReport(BaseModel):
    """Resposta de GET /api/fleet: estado da EC2 e de cada vinheria."""
    fiware_online: bool
    fiware_offline_since: str | None = None
    updated_at: str | None = None
    vinherias: list[VinheriaStatus]


class LimitsUpdate(BaseModel):
    """Resposta do PUT da faixa: o que foi gravado e se já chegou ao ESP32."""
    device_id: str
    limits: Limits
    device_sync: Literal["enviado", "pendente"]


class CommandRequest(BaseModel):
    """Pedido de comando manual vindo do painel."""
    command: ManualCommand


class CommandResult(BaseModel):
    """Confirmação de que o comando foi entregue ao Orion."""
    device_id: str
    command: ManualCommand
```

- [ ] **Passo 5: implementar `backend/app/services/alert_log.py`**

```python
"""
Log de alertas (RF10): cada alerta tem vinheria, atributo, valor, início,
fim e duração.

O alerta abre quando um atributo sai da faixa (ou a vinheria, ou a EC2,
fica offline) e fecha quando volta. As linhas ficam no SQLite mesmo depois
que a vinheria é removida, para o histórico não se perder.
"""
from datetime import datetime

from app.core.db import Database
from app.models.schemas_fleet import Alert


def _duracao(opened_at: str, closed_at: str | None) -> int | None:
    """Segundos entre abertura e fechamento; None enquanto aberto."""
    if closed_at is None:
        return None
    delta = datetime.fromisoformat(closed_at) - datetime.fromisoformat(opened_at)
    return max(0, int(delta.total_seconds()))


def _linha_para_alert(linha) -> Alert:
    """Converte uma linha da tabela alerts no modelo Alert."""
    return Alert(id=linha["id"], device_id=linha["device_id"], attr=linha["attr"],
                 value=linha["value"], opened_at=linha["opened_at"],
                 closed_at=linha["closed_at"],
                 duration_seconds=_duracao(linha["opened_at"], linha["closed_at"]))


class AlertLog:
    """Gravação e consulta do histórico de alertas."""

    def __init__(self, db: Database):
        self._db = db

    def open(self, device_id: str, attr: str, value: float | None, opened_at: str) -> Alert:
        """Abre um alerta e devolve o registro com o id gerado."""
        with self._db:
            resultado = self._db.execute(
                "INSERT INTO alerts (device_id, attr, value, opened_at) VALUES (?, ?, ?, ?)",
                (device_id, attr, value, opened_at),
            )
        return Alert(id=resultado.lastrowid, device_id=device_id, attr=attr, value=value,
                     opened_at=opened_at)

    def close(self, alert_id: int, closed_at: str) -> None:
        """Fecha um alerta aberto; alerta já fechado não muda."""
        with self._db:
            self._db.execute(
                "UPDATE alerts SET closed_at = ? WHERE id = ? AND closed_at IS NULL",
                (closed_at, alert_id),
            )

    def open_alerts(self) -> list[Alert]:
        """Alertas ainda abertos, na ordem em que abriram (usado na partida do poller)."""
        linhas = self._db.execute("SELECT * FROM alerts WHERE closed_at IS NULL ORDER BY id")
        return [_linha_para_alert(linha) for linha in linhas]

    def list(self, device_id: str | None = None, limit: int = 100) -> list[Alert]:
        """Histórico do mais novo para o mais velho, opcionalmente de uma vinheria só."""
        if device_id is None:
            linhas = self._db.execute(
                "SELECT * FROM alerts ORDER BY opened_at DESC, id DESC LIMIT ?", (limit,))
        else:
            linhas = self._db.execute(
                "SELECT * FROM alerts WHERE device_id = ? "
                "ORDER BY opened_at DESC, id DESC LIMIT ?", (device_id, limit))
        return [_linha_para_alert(linha) for linha in linhas]
```

- [ ] **Passo 6: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_alert_log.py -v` → 7 passed.
Run: `.venv/Scripts/python -m pytest -q` → **190 passed**.

- [ ] **Passo 7: commit**

```bash
git add app/models/schemas_fleet.py app/services/alert_log.py tests/fakes.py tests/test_alert_log.py tests/conftest.py
git commit -m "feat: adiciona log de alertas e modelos da frota"
```

---

## Subtarefa 4.6 — Edição da faixa, valor do `set_limits` e conversão de entidade (R4.1–R4.3)

**Files:**
- Modify: `backend/app/models/schemas.py`, `backend/app/services/limits.py`, `backend/app/services/readings.py`
- Modify: `backend/tests/test_limits.py`, `backend/tests/test_readings.py`

**Interfaces:**
- Produces: `CurrentReading.configured: bool | None`; `LimitsStore.update(device_id, limits) -> None`; `limits_to_command_value(limits) -> str`; `reading_from_entity(device_id, entidade) -> CurrentReading`.

- [ ] **Passo 1: escrever os testes de faixa que falham**

Em `backend/tests/test_limits.py`, trocar o import de `app.services.limits` por:

```python
from app.services.limits import DEFAULT_LIMITS, limits_to_command_value, limits_to_orion_attrs
```

e o de `app.models.schemas` por:

```python
from app.models.schemas import AttrLimits, Limits
```

E, ao fim do arquivo:

```python
def test_limits_update_substitui_faixa(conn, limits):
    _grava_device(conn)
    with conn:
        limits.seed_defaults("vinheria001")
    nova = Limits(temperature=AttrLimits(min=10, max=16),
                  humidity=AttrLimits(min=55, max=75),
                  luminosity=AttrLimits(min=0, max=20))
    limits.update("vinheria001", nova)
    assert limits.get("vinheria001") == nova
    assert conn.execute("SELECT COUNT(*) FROM triggers").fetchone()[0] == 3


def test_command_value_padrao():
    assert limits_to_command_value(DEFAULT_LIMITS) == "12,18,50,70,0,30"


def test_command_value_com_decimais():
    faixa = Limits(temperature=AttrLimits(min=12.5, max=18),
                   humidity=AttrLimits(min=50, max=70.5),
                   luminosity=AttrLimits(min=0, max=30))
    assert limits_to_command_value(faixa) == "12.5,18,50,70.5,0,30"
```

- [ ] **Passo 2: escrever o teste de conversão que falha**

Em `backend/tests/test_readings.py`, acrescentar ao fim (teste síncrono num arquivo com `pytestmark = pytest.mark.anyio` é normal; o arquivo já tem `test_history_query_exige_um_modo` assim):

```python
@pytest.mark.parametrize("bruto, esperado", [(1, True), ("1", True), (0, False),
                                             (None, None), ("x", None)])
def test_reading_from_entity_converte(bruto, esperado):
    from app.services.readings import reading_from_entity

    entidade = {"temperature": "14.5", "humidity": 60, "luminosity": " ",
                "TimeInstant": "2026-10-08T11:59:58.000Z"}
    if bruto is not None:
        entidade["configured"] = bruto
    leitura = reading_from_entity("vinheria001", entidade)
    assert (leitura.temperature, leitura.humidity, leitura.luminosity) == (14.5, 60.0, None)
    assert leitura.time_instant == "2026-10-08T11:59:58.000Z"
    assert leitura.configured is esperado
    vazia = reading_from_entity("vinheria001", {})
    assert vazia.temperature is None and vazia.time_instant is None and vazia.configured is None
```

- [ ] **Passo 3: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_limits.py tests/test_readings.py -v`
Expected: erro de coleta `ImportError: cannot import name 'limits_to_command_value'`.

- [ ] **Passo 4: acrescentar `configured` ao `CurrentReading` em `backend/app/models/schemas.py`**

Trocar a classe `CurrentReading` por:

```python
class CurrentReading(BaseModel):
    """Estado atual de uma vinheria; None quando ainda não há leitura válida."""
    device_id: str
    temperature: float | None = None
    humidity: float | None = None
    luminosity: float | None = None
    time_instant: str | None = None
    # True quando o ESP32 já recebeu a faixa (set_limits); False aguardando; None sem dado
    configured: bool | None = None
```

- [ ] **Passo 5: ampliar `backend/app/services/limits.py`**

Na docstring do módulo, trocar "A Task 4 acrescenta aqui a edição da faixa." por "O painel pode editá-la depois (Task 4)."

Depois de `limits_to_orion_attrs`, acrescentar:

```python
def limits_to_command_value(limits: Limits) -> str:
    """Valor do comando set_limits: "tmin,tmax,hmin,hmax,lmin,lmax".

    O separador é vírgula: ; seria barrado pelo Orion ("Invalid characters in attribute value")
    e | colide com o UltraLight. Inteiros saem
    sem ".0" (12) e decimais saem como estão (12.5).
    """
    return ";".join(f"{valor:g}" for valor in limits_to_orion_attrs(limits).values())
```

E, no `LimitsStore`, depois de `seed_defaults`:

```python
    def update(self, device_id: str, limits: Limits) -> None:
        """Substitui a faixa da vinheria numa transação própria (edição pelo painel)."""
        with self._conn:
            for attr in ORION_LIMIT_NAMES:
                faixa = getattr(limits, attr)
                self._conn.execute(
                    "INSERT INTO triggers (device_id, attr, min_value, max_value) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(device_id, attr) DO UPDATE SET "
                    "min_value = excluded.min_value, max_value = excluded.max_value",
                    (device_id, attr, faixa.min, faixa.max),
                )
```

- [ ] **Passo 6: extrair `reading_from_entity` em `backend/app/services/readings.py`**

Depois de `to_float`, acrescentar:

```python
def _to_configured(valor) -> bool | None:
    """Atributo configured do ESP32: 1 -> True, 0 -> False, ausente ou inválido -> None."""
    numero = to_float(valor)
    if numero is None:
        return None
    return numero == 1


def reading_from_entity(device_id: str, entidade: dict) -> CurrentReading:
    """Converte uma entidade do Orion (keyValues) no estado atual da vinheria.

    Usada na consulta de uma vinheria e pelo poller da frota. Entidade vazia
    ({}) vira todos os valores None.
    """
    instante = entidade.get("TimeInstant")
    return CurrentReading(
        device_id=device_id,
        temperature=to_float(entidade.get("temperature")),
        humidity=to_float(entidade.get("humidity")),
        luminosity=to_float(entidade.get("luminosity")),
        time_instant=instante if isinstance(instante, str) and instante.strip() else None,
        configured=_to_configured(entidade.get("configured")),
    )
```

E trocar o corpo de `ReadingsService.current` por:

```python
    async def current(self, device_id: str) -> CurrentReading:
        """Estado atual no Orion; sem entidade ou sem leitura, valores None."""
        device = self._registry.get(device_id)
        try:
            entidade = await self._fiware.get_entity(device.entity_id)
        except FiwareNotFound:
            entidade = {}
        return reading_from_entity(device.device_id, entidade)
```

- [ ] **Passo 7: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_limits.py tests/test_readings.py -v` → todos passam.
Run: `.venv/Scripts/python -m pytest -q` → **198 passed** (3 de faixa + 5 casos parametrizados de conversão).

- [ ] **Passo 8: commit**

```bash
git add app/models/schemas.py app/services/limits.py app/services/readings.py tests/test_limits.py tests/test_readings.py
git commit -m "feat: permite editar a faixa e le o atributo configured do ESP32"
```

---

## Subtarefa 4.7 — Provisionar o atributo `configured` (R4.4)

**Files:**
- Modify: `backend/app/services/fiware_constants.py`, `backend/app/services/fiware_iota.py`, `backend/tests/test_fiware_iota.py`

**Interfaces:**
- Produces: `STATUS_ATTRS = (("c", "configured", "Integer"),)`; `provision_device` declara sensores + estado.

- [ ] **Passo 1: atualizar o teste (falha)**

Em `backend/tests/test_fiware_iota.py`, no `test_provision_device_envia_body`, trocar a asserção de `attributes` por:

```python
    assert device["attributes"] == [
        {"object_id": "t", "name": "temperature", "type": "Float"},
        {"object_id": "h", "name": "humidity", "type": "Float"},
        {"object_id": "l", "name": "luminosity", "type": "Integer"},
        {"object_id": "c", "name": "configured", "type": "Integer"},
    ]
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_iota.py -v`
Expected: FAIL em `test_provision_device_envia_body` (falta o item `configured`).

- [ ] **Passo 3: acrescentar a constante em `backend/app/services/fiware_constants.py`**

Logo depois de `SENSOR_ATTRS`:

```python
# Atributos de estado do dispositivo, fora do STH: c = 1 quando o ESP32 já
# recebeu a faixa por set_limits, 0 enquanto mostra "Configure o dispositivo"
STATUS_ATTRS = (
    ("c", "configured", "Integer"),
)
```

(`ATRIBUTOS_LONGOS` continua derivado só de `SENSOR_ATTRS`, então nenhuma subscription nova é criada.)

- [ ] **Passo 4: declarar no provisionamento (`backend/app/services/fiware_iota.py`)**

Trocar o import de constantes por:

```python
from app.services.fiware_constants import COMMANDS, ENTITY_TYPE, SENSOR_ATTRS, STATUS_ATTRS
```

E, em `provision_device`, trocar a lista `attributes` por:

```python
            "attributes": [
                {"object_id": curto, "name": longo, "type": tipo}
                for curto, longo, tipo in SENSOR_ATTRS + STATUS_ATTRS
            ],
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_fiware_iota.py -v` → todos passam.
Run: `.venv/Scripts/python -m pytest -q` → **198 passed**.

- [ ] **Passo 6: commit**

```bash
git add app/services/fiware_constants.py app/services/fiware_iota.py tests/test_fiware_iota.py
git commit -m "feat: provisiona o atributo configured do ESP32 no IoT Agent"
```

---

## Subtarefa 4.8 — Regras puras do motor (R5)

**Files:**
- Create: `backend/app/services/trigger_rules.py`, `backend/tests/test_trigger_rules.py`

**Interfaces:**
- Produces: `SENSOR_ORDER`, `BLINK_COMMANDS`, `SEND_ORDER`, `DEFAULT_HYSTERESIS`, `MAX_HYSTERESIS_FRACTION`; `parse_instant`, `seconds_since`, `is_offline`, `direction`, `hysteresis_margin`, `can_close`, `command_plan`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_trigger_rules.py`:

```python
"""Testes das regras puras do motor de alertas (spec R5)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.trigger_rules import (
    can_close,
    command_plan,
    direction,
    hysteresis_margin,
    is_offline,
    parse_instant,
    seconds_since,
)

UTC = timezone.utc
MEIO_DIA = datetime(2026, 10, 8, 12, 0, 0, tzinfo=UTC)


def test_parse_instant_formatos():
    esperado = datetime(2026, 10, 8, 11, 59, 58, tzinfo=UTC)
    assert parse_instant("2026-10-08T11:59:58.000Z") == esperado
    assert parse_instant("2026-10-08T11:59:58+00:00") == esperado
    assert parse_instant("2026-10-08T11:59:58") == esperado  # sem fuso = UTC


@pytest.mark.parametrize("texto", [None, "", "   ", "ontem", 123])
def test_parse_instant_invalido(texto):
    assert parse_instant(texto) is None


def test_seconds_since():
    assert seconds_since(MEIO_DIA - timedelta(seconds=4), MEIO_DIA) == 4
    assert seconds_since(MEIO_DIA + timedelta(seconds=3), MEIO_DIA) == 0  # relógio adiantado
    assert seconds_since(None, MEIO_DIA) is None


def test_is_offline_pela_leitura():
    visto = MEIO_DIA
    assert is_offline(visto, None, MEIO_DIA + timedelta(seconds=30), 30) is False
    assert is_offline(visto, None, MEIO_DIA + timedelta(seconds=31), 30) is True


def test_is_offline_sem_leitura_usa_cadastro():
    cadastro = MEIO_DIA
    assert is_offline(None, cadastro, MEIO_DIA + timedelta(seconds=10), 30) is False
    assert is_offline(None, cadastro, MEIO_DIA + timedelta(seconds=31), 30) is True
    assert is_offline(None, None, MEIO_DIA, 30) is True


def test_direction():
    assert direction(19, 12, 18) == "above"
    assert direction(11, 12, 18) == "below"
    assert direction(12, 12, 18) is None
    assert direction(18, 12, 18) is None
    assert direction(15, 12, 18) is None


def test_hysteresis_margin_limitada_pela_largura():
    assert hysteresis_margin("temperature", 12, 18) == 0.5
    assert hysteresis_margin("humidity", 50, 70) == 2.0
    assert hysteresis_margin("luminosity", 0, 30) == 2.0
    assert hysteresis_margin("temperature", 15, 16) == 0.25


def test_can_close_respeita_lado():
    assert can_close(17.6, 12, 18, "above", 0.5) is False
    assert can_close(17.5, 12, 18, "above", 0.5) is True
    assert can_close(12.1, 12, 18, "above", 0.5) is True    # folga só do lado violado
    assert can_close(12.4, 12, 18, "below", 0.5) is False
    assert can_close(12.5, 12, 18, "below", 0.5) is True
    assert can_close(18.0, 12, 18, None, 0.5) is True       # lado desconhecido
    assert can_close(18.1, 12, 18, None, 0.5) is False
    assert can_close(11.0, 12, 18, "above", 0.5) is False   # passou para o outro lado


def test_command_plan():
    assert command_plan(set()) == ["alert_off"]
    assert command_plan({"temperature"}) == ["alert_off", "blink_temp"]
    assert command_plan({"temperature", "humidity", "luminosity"}) == [
        "alert_off", "blink_lux", "blink_hum", "blink_temp"]
    assert command_plan(frozenset({"luminosity", "humidity"})) == [
        "alert_off", "blink_lux", "blink_hum"]
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_trigger_rules.py -v`
Expected: erro de coleta `ModuleNotFoundError: No module named 'app.services.trigger_rules'`.

- [ ] **Passo 3: implementar `backend/app/services/trigger_rules.py`**

```python
"""
Regras puras do motor de alertas: tempo, offline, faixa com folga
(histerese) e plano de comandos para o ESP32.

Sem banco e sem rede, para cada decisão ser testada isolada. Quem aplica
as regras a cada ciclo é o TriggerEngine.
"""
from datetime import datetime, timezone

# Ordem canônica dos atributos de sensor
SENSOR_ORDER = ("temperature", "humidity", "luminosity")
# Comando de alerta de cada atributo
BLINK_COMMANDS = {"temperature": "blink_temp", "humidity": "blink_hum",
                  "luminosity": "blink_lux"}
# Ordem de envio dos blinks: o último recebido define o padrão de LED e
# buzzer no ESP32, então a temperatura (a anomalia mais danosa ao vinho)
# vai por último
SEND_ORDER = ("luminosity", "humidity", "temperature")
# Folga para fechar um alerta, por atributo (°C, % e %)
DEFAULT_HYSTERESIS = {"temperature": 0.5, "humidity": 2.0, "luminosity": 2.0}
# A folga nunca passa de 25 % da largura da faixa (faixas estreitas)
MAX_HYSTERESIS_FRACTION = 0.25


def parse_instant(texto) -> datetime | None:
    """Converte o TimeInstant do IoT Agent (ex.: 2026-10-08T11:59:58.000Z).

    Sem fuso, assume UTC. Vazio, inválido ou não texto devolve None.
    """
    if not isinstance(texto, str) or not texto.strip():
        return None
    try:
        instante = datetime.fromisoformat(texto.strip())
    except ValueError:
        return None
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante


def seconds_since(reference: datetime | None, now: datetime) -> int | None:
    """Segundos inteiros desde `reference` (nunca negativo); None sem referência."""
    if reference is None:
        return None
    return max(0, int((now - reference).total_seconds()))


def is_offline(last_seen: datetime | None, created_at: datetime | None,
               now: datetime, offline_seconds: int) -> bool:
    """Offline se a última leitura passou do limite.

    Sem leitura, a referência é o cadastro: vinheria recém-cadastrada tem
    `offline_seconds` para mandar a primeira leitura antes de ficar offline.
    """
    referencia = last_seen or created_at
    if referencia is None:
        return True
    return (now - referencia).total_seconds() > offline_seconds


def direction(value: float, lo: float, hi: float) -> str | None:
    """Lado violado da faixa: "above", "below" ou None (dentro, bordas incluídas)."""
    if value > hi:
        return "above"
    if value < lo:
        return "below"
    return None


def hysteresis_margin(attr: str, lo: float, hi: float,
                      table: dict[str, float] = DEFAULT_HYSTERESIS) -> float:
    """Folga para fechar o alerta: a da tabela, limitada a 25 % da largura."""
    return min(table[attr], MAX_HYSTERESIS_FRACTION * (hi - lo))


def can_close(value: float, lo: float, hi: float, side: str | None, margin: float) -> bool:
    """True se o alerta pode fechar.

    Exige estar dentro da faixa e, do lado que foi violado, afastado da
    borda pela folga. Do lado oposto não há folga: com lux_min = 0, a adega
    escura (luz 0) precisa fechar um alerta de excesso de luz. Lado
    desconhecido (alerta retomado após reinício) fecha ao entrar na faixa.
    """
    if not lo <= value <= hi:
        return False
    if side == "above":
        return value <= hi - margin
    if side == "below":
        return value >= lo + margin
    return True


def command_plan(active) -> list[str]:
    """Comandos que deixam o ESP32 coerente com o conjunto de atributos em alerta.

    O firmware não desliga um atributo só, então o plano recomeça do zero:
    alert_off e um blink por atributo ativo, do menos para o mais prioritário.
    """
    return ["alert_off"] + [BLINK_COMMANDS[attr] for attr in SEND_ORDER if attr in active]
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_trigger_rules.py -v` → 13 passed.
Run: `.venv/Scripts/python -m pytest -q` → **211 passed**.

- [ ] **Passo 5: commit**

```bash
git add app/services/trigger_rules.py tests/test_trigger_rules.py
git commit -m "feat: adiciona regras puras de offline, histerese e plano de comandos"
```

---

## Subtarefa 4.9 — Alertas em memória e retrato da frota (R6)

**Files:**
- Create: `backend/app/services/alert_tracker.py`, `backend/app/services/fleet_state.py`, `backend/tests/test_alert_tracker.py`, `backend/tests/test_fleet.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `AlertLog`, `SENSOR_ORDER`, schemas da 4.5.
- Produces: `OFFLINE`, `ORDEM_ALERTAS`, `OpenAlert`, `AlertTracker(alerts)` (`load`, `get`, `open`, `close`, `close_except`, `active`, `active_sensors`); `FleetState` (`replace`, `snapshot`, `get`, `status_of`, `report`, `updated_at`, `fiware_online`, `fiware_offline_since`); fixture `fleet`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_alert_tracker.py`:

```python
"""Testes dos alertas abertos em memória (spec R6.1)."""
from app.services.alert_tracker import AlertTracker

T0 = "2026-10-08T12:00:00+00:00"


def test_open_e_idempotente(alert_log):
    tracker = AlertTracker(alert_log)
    tracker.open("vinheria001", "temperature", 21.0, "above", T0)
    tracker.open("vinheria001", "temperature", 22.0, "above", T0)
    assert len(alert_log.open_alerts()) == 1
    assert tracker.get("vinheria001", "temperature").side == "above"


def test_close_fecha_no_log(alert_log):
    tracker = AlertTracker(alert_log)
    tracker.open("vinheria001", "temperature", 21.0, "above", T0)
    tracker.close("vinheria001", "temperature", "2026-10-08T12:01:00+00:00")
    tracker.close("vinheria001", "temperature", "2026-10-08T12:02:00+00:00")  # já fechado
    assert alert_log.open_alerts() == []
    assert alert_log.list()[0].duration_seconds == 60
    assert tracker.get("vinheria001", "temperature") is None


def test_active_em_ordem_canonica(alert_log):
    tracker = AlertTracker(alert_log)
    tracker.open("vinheria001", "offline", None, None, T0)
    tracker.open("vinheria001", "luminosity", 40.0, "above", T0)
    tracker.open("vinheria001", "temperature", 21.0, "above", T0)
    tracker.open("vinheria002", "humidity", 40.0, "below", T0)
    assert [a.attr for a in tracker.active("vinheria001")] == [
        "temperature", "luminosity", "offline"]
    assert tracker.active_sensors("vinheria001") == frozenset({"temperature", "luminosity"})


def test_close_except_fecha_quem_nao_esta(alert_log):
    tracker = AlertTracker(alert_log)
    tracker.open("vinheria001", "temperature", 21.0, "above", T0)
    tracker.open("vinheria002", "temperature", 21.0, "above", T0)
    tracker.open("fiware", "offline", None, None, T0)
    tracker.close_except({"vinheria001", "fiware"}, "2026-10-08T12:01:00+00:00")
    assert sorted(a.device_id for a in alert_log.open_alerts()) == ["fiware", "vinheria001"]
```

`backend/tests/test_fleet.py`:

```python
"""Testes do retrato da frota em memória (spec R6.2)."""
from tests.fakes import status_vinheria


def test_fleet_comeca_vazio(fleet):
    assert fleet.snapshot() == []
    assert fleet.updated_at is None
    assert fleet.fiware_online is True


def test_fleet_snapshot_ordena_e_filtra(fleet):
    fleet.replace([status_vinheria("vinheria002"), status_vinheria("vinheria001")],
                  "2026-10-08T12:00:00+00:00")
    assert [s.device_id for s in fleet.snapshot()] == ["vinheria001", "vinheria002"]
    assert [s.device_id for s in fleet.snapshot(["vinheria002", "vinheria009"])] \
        == ["vinheria002"]
    assert fleet.updated_at == "2026-10-08T12:00:00+00:00"


def test_fleet_status_of(fleet):
    fleet.replace([status_vinheria("vinheria001", "offline")], "2026-10-08T12:00:00+00:00")
    assert fleet.status_of("vinheria001") == "offline"
    assert fleet.status_of("vinheria002") is None
    assert fleet.get("vinheria001").status == "offline"
    assert fleet.get("vinheria002") is None


def test_fleet_replace_troca_tudo(fleet):
    fleet.replace([status_vinheria("vinheria001")], "t1")
    fleet.replace([status_vinheria("vinheria002")], "t2")
    assert [s.device_id for s in fleet.snapshot()] == ["vinheria002"]


def test_fleet_report(fleet):
    fleet.replace([status_vinheria("vinheria001", "offline"), status_vinheria("vinheria099")],
                  "2026-10-08T12:00:40+00:00", fiware_online=False,
                  fiware_offline_since="2026-10-08T12:00:00+00:00")
    relatorio = fleet.report(["vinheria001"])
    assert relatorio.fiware_online is False
    assert relatorio.fiware_offline_since == "2026-10-08T12:00:00+00:00"
    assert relatorio.updated_at == "2026-10-08T12:00:40+00:00"
    assert [s.device_id for s in relatorio.vinherias] == ["vinheria001"]
```

Em `backend/tests/conftest.py`, acrescentar o import:

```python
from app.services.fleet_state import FleetState
```

E, ao fim do arquivo:

```python
@pytest.fixture
def fleet():
    """Retrato da frota vazio."""
    return FleetState()
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_alert_tracker.py tests/test_fleet.py -v`
Expected: erro de coleta `ModuleNotFoundError: No module named 'app.services.fleet_state'` (vindo do `conftest.py`).

- [ ] **Passo 3: implementar `backend/app/services/alert_tracker.py`**

```python
"""
Alertas abertos em memória, sempre espelhados no AlertLog (SQLite).

O motor consulta este estado a cada ciclo para saber o que já está aberto
sem ir ao banco, e de que lado da faixa o valor saiu (para a folga ao
fechar). Abrir e fechar aqui grava no log na mesma hora.
"""
import logging
from dataclasses import dataclass

from app.models.schemas_fleet import ActiveAlert, Alert
from app.services.alert_log import AlertLog
from app.services.trigger_rules import SENSOR_ORDER

log = logging.getLogger(__name__)

OFFLINE = "offline"
# Ordem dos alertas ativos no retrato: sensores na ordem canônica, offline por último
ORDEM_ALERTAS = SENSOR_ORDER + (OFFLINE,)


@dataclass
class OpenAlert:
    """Alerta aberto: id no SQLite, lado violado ("above"/"below"/None), valor e início."""
    alert_id: int
    side: str | None
    value: float | None
    since: str


class AlertTracker:
    """Alertas abertos por (device_id, attr)."""

    def __init__(self, alerts: AlertLog):
        self._alerts = alerts
        self._open: dict[tuple[str, str], OpenAlert] = {}

    def load(self) -> list[Alert]:
        """Retoma os alertas abertos no SQLite (partida do backend).

        O lado violado não fica gravado, então volta como None (desconhecido).
        Devolve os alertas retomados.
        """
        abertos = self._alerts.open_alerts()
        for alerta in abertos:
            self._open[(alerta.device_id, alerta.attr)] = OpenAlert(
                alerta.id, None, alerta.value, alerta.opened_at)
        return abertos

    def get(self, device_id: str, attr: str) -> OpenAlert | None:
        """Alerta aberto daquele atributo, ou None."""
        return self._open.get((device_id, attr))

    def open(self, device_id: str, attr: str, value: float | None, side: str | None,
             when: str) -> None:
        """Abre o alerta (se ainda não estiver aberto) e grava no log."""
        chave = (device_id, attr)
        if chave in self._open:
            return
        alerta = self._alerts.open(device_id, attr, value, when)
        self._open[chave] = OpenAlert(alerta.id, side, value, alerta.opened_at)
        log.info("alerta aberto: %s %s (%s)", device_id, attr, value)

    def close(self, device_id: str, attr: str, when: str) -> None:
        """Fecha o alerta, se estiver aberto."""
        aberto = self._open.pop((device_id, attr), None)
        if aberto is not None:
            self._alerts.close(aberto.alert_id, when)
            log.info("alerta fechado: %s %s", device_id, attr)

    def close_except(self, keep: set[str], when: str) -> None:
        """Fecha os alertas de quem não está em `keep` (vinherias removidas)."""
        for device_id, attr in [chave for chave in self._open if chave[0] not in keep]:
            self.close(device_id, attr, when)

    def active(self, device_id: str) -> list[ActiveAlert]:
        """Alertas ativos da vinheria, sensores na ordem canônica e offline por último."""
        ativos = [ActiveAlert(attr=attr, value=aberto.value, since=aberto.since)
                  for (dono, attr), aberto in self._open.items() if dono == device_id]
        return sorted(ativos, key=lambda alerta: ORDEM_ALERTAS.index(alerta.attr))

    def active_sensors(self, device_id: str) -> frozenset[str]:
        """Atributos de sensor em alerta (o que o ESP32 deve estar mostrando)."""
        return frozenset(attr for attr in SENSOR_ORDER if (device_id, attr) in self._open)
```

- [ ] **Passo 4: implementar `backend/app/services/fleet_state.py`**

```python
"""
Retrato da frota em memória: o status de cada vinheria e da EC2 no último
ciclo do poller.

O TriggerEngine escreve a cada ciclo e as rotas leem (GET /api/fleet,
recusa de comando para vinheria offline ou configurando). Tudo roda no loop
de eventos, então não precisa de lock.
"""
from app.models.schemas_fleet import FleetReport, VinheriaStatus


class FleetState:
    """Último VinheriaStatus de cada vinheria e o estado da EC2."""

    def __init__(self):
        self._statuses: dict[str, VinheriaStatus] = {}
        self.updated_at: str | None = None
        self.fiware_online = True
        self.fiware_offline_since: str | None = None

    def replace(self, statuses: list[VinheriaStatus], at: str, fiware_online: bool = True,
                fiware_offline_since: str | None = None) -> None:
        """Troca o retrato inteiro pelo do ciclo atual."""
        self._statuses = {status.device_id: status for status in statuses}
        self.updated_at = at
        self.fiware_online = fiware_online
        self.fiware_offline_since = fiware_offline_since

    def snapshot(self, device_ids: list[str] | None = None) -> list[VinheriaStatus]:
        """Retrato ordenado por id; com `device_ids`, só essas vinherias."""
        itens = sorted(self._statuses.values(), key=lambda status: status.device_id)
        if device_ids is None:
            return itens
        pedidos = set(device_ids)
        return [status for status in itens if status.device_id in pedidos]

    def get(self, device_id: str) -> VinheriaStatus | None:
        """Retrato de uma vinheria no último ciclo, ou None."""
        return self._statuses.get(device_id)

    def status_of(self, device_id: str) -> str | None:
        """Status da vinheria no último ciclo; None se o motor ainda não a avaliou."""
        status = self._statuses.get(device_id)
        return status.status if status else None

    def report(self, device_ids: list[str]) -> FleetReport:
        """Resposta de /api/fleet, só com as vinherias pedidas (as cadastradas)."""
        return FleetReport(fiware_online=self.fiware_online,
                           fiware_offline_since=self.fiware_offline_since,
                           updated_at=self.updated_at,
                           vinherias=self.snapshot(device_ids))
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_alert_tracker.py tests/test_fleet.py -v` → 9 passed.
Run: `.venv/Scripts/python -m pytest -q` → **220 passed**.

- [ ] **Passo 6: commit**

```bash
git add app/services/alert_tracker.py app/services/fleet_state.py tests/test_alert_tracker.py tests/test_fleet.py tests/conftest.py
git commit -m "feat: adiciona alertas abertos em memoria e retrato da frota"
```

---

## Subtarefa 4.10 — Motor de alertas: sensores e comandos (R7)

**Files:**
- Create: `backend/app/services/trigger_engine.py`, `backend/tests/test_trigger_engine.py`
- Modify: `backend/tests/fakes.py`, `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `DeviceRegistry.list`, `LimitsStore.get`, `AlertLog`, `AlertTracker`, `ConfigStore.get`, `FleetState`, `reading_from_entity`, `quality_score`, `limits_to_command_value`, regras da 4.8, `FiwareClient.list_entities/send_command`, `FIWARE_ALERT_ID`.
- Produces: `TriggerEngine(registry, limits, alerts, fiware, config, fleet, clock=_agora_utc, sleep=asyncio.sleep, hysteresis=None)` com `mark_limits_pending`, `tick`, `run`; fakes `FiwareFalso`, `Relogio`, `entidade`, `instante_de`; fixtures `fiware_falso`, `relogio`, `engine`; parâmetro `created_at` no `cadastrar`.

> O motor inteiro (inclusive configuração, offline, EC2 e `run`) é escrito nesta subtarefa, porque as partes dividem o mesmo estado. A 4.11 só acrescenta os testes desses casos, que devem passar sem mudar código; se algum falhar, é defeito a corrigir na 4.11.

- [ ] **Passo 1: ampliar `backend/tests/fakes.py`**

Trocar o arquivo inteiro por:

```python
"""Peças falsas compartilhadas pelos testes da Task 4 (FIWARE, relógio, frota)."""
from datetime import datetime, timedelta, timezone

from app.models.schemas_fleet import SensorValues, VinheriaStatus


def status_vinheria(device_id: str = "vinheria001", status: str = "ok") -> VinheriaStatus:
    """Um VinheriaStatus mínimo, para testes de frota e de comandos."""
    return VinheriaStatus(device_id=device_id, name="Vinheria", city="Cidade", status=status,
                          current=SensorValues(), active_alerts=[])


class FiwareFalso:
    """Substitui o FiwareClient: guarda o que foi pedido e falha quando mandado."""

    def __init__(self):
        self.entidades: list[dict] = []
        self.comandos: list[tuple[str, str, str]] = []
        self.atualizacoes: list[tuple[str, dict]] = []
        self.chamadas_listar = 0
        self.erro_listar = None
        self.erro_comando = None
        self.erro_update = None

    async def list_entities(self, entity_type: str = "Vinheria") -> list[dict]:
        self.chamadas_listar += 1
        if self.erro_listar:
            raise self.erro_listar
        return list(self.entidades)

    async def send_command(self, entity_id: str, command: str, value: str = "") -> None:
        if self.erro_comando:
            raise self.erro_comando
        self.comandos.append((entity_id, command, value))

    async def update_attrs(self, entity_id: str, attrs: dict) -> None:
        if self.erro_update:
            raise self.erro_update
        self.atualizacoes.append((entity_id, attrs))


class Relogio:
    """Relógio controlado pelo teste (UTC)."""

    def __init__(self, inicio: datetime = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)):
        self.agora = inicio

    def __call__(self) -> datetime:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += timedelta(seconds=segundos)

    def iso(self, segundos_atras: float = 0) -> str:
        """Instante no formato do cadastro (ISO com +00:00)."""
        return (self.agora - timedelta(seconds=segundos_atras)).isoformat(timespec="seconds")


def instante_de(relogio: Relogio, segundos_atras: float = 2) -> str:
    """TimeInstant no formato do IoT Agent, `segundos_atras` antes do relógio."""
    instante = relogio.agora - timedelta(seconds=segundos_atras)
    return instante.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def entidade(numero: str = "001", t: float | None = 15.0, h: float | None = 60.0,
             l: float | None = 10.0, c: int | None = 1,
             instante: str = "2026-10-08T11:59:58.000Z") -> dict:
    """Entidade Vinheria como o Orion devolve em keyValues; None omite o atributo.

    c = 1 é um ESP32 já configurado (recebeu a faixa); c = 0, aguardando.
    """
    dados = {"id": f"urn:ngsi-ld:Vinheria:{numero}", "type": "Vinheria", "TimeInstant": instante}
    for nome, valor in (("temperature", t), ("humidity", h), ("luminosity", l),
                        ("configured", c)):
        if valor is not None:
            dados[nome] = valor
    return dados
```

- [ ] **Passo 2: ampliar `backend/tests/conftest.py`**

Acrescentar aos imports:

```python
from app.services.trigger_engine import TriggerEngine
from tests.fakes import FiwareFalso, Relogio
```

Trocar a fixture `cadastrar` inteira por (ganha `created_at`, mesmo comportamento de antes):

```python
@pytest.fixture
def cadastrar(conn, limits):
    """Grava vinherias direto no SQLite, sem FIWARE (para testes de leitura e remoção)."""
    def _cadastrar(numero="001", name="Vinheria Paulista", city="São Paulo",
                   created_at="2026-10-07T21:00:00+00:00"):
        device = Device(device_id=f"vinheria{numero}",
                        entity_id=f"urn:ngsi-ld:Vinheria:{numero}",
                        name=name, city=city, created_at=created_at)
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

E, ao fim do arquivo:

```python
@pytest.fixture
def fiware_falso():
    """FIWARE falso para o motor e o controle (sem respx)."""
    return FiwareFalso()


@pytest.fixture
def relogio():
    """Relógio parado em 2026-10-08 12:00:00 UTC, avançado pelo teste."""
    return Relogio()


@pytest.fixture
def engine(registry, limits, alert_log, fiware_falso, store, fleet, relogio):
    """TriggerEngine com FIWARE falso, banco de teste e relógio controlado."""
    return TriggerEngine(registry, limits, alert_log, fiware_falso, store, fleet, clock=relogio)
```

- [ ] **Passo 3: escrever os testes do motor que falham**

`backend/tests/test_trigger_engine.py`:

```python
"""Testes do motor de alertas: sensores, comandos e retrato (spec R7)."""
import pytest

from app.models.schemas import AttrLimits, Limits
from app.services.limits import DEFAULT_LIMITS
from tests.fakes import entidade

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
E2 = "urn:ngsi-ld:Vinheria:002"


def comandos(fiware, entity_id=E1):
    """Nomes dos comandos enviados a uma entidade, na ordem."""
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def primeira_passada(engine, fiware):
    """Roda a ressincronização da partida e limpa os comandos dela."""
    await engine.tick()
    fiware.comandos.clear()


async def test_primeira_passada_sincroniza_faixa_e_desliga_alerta(engine, fiware_falso, cadastrar):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    assert fiware_falso.comandos == [(E1, "set_limits", "12,18,50,70,0,30"),
                                     (E1, "alert_off", "")]


async def test_segunda_passada_sem_mudanca_nao_envia_nada(engine, fiware_falso, cadastrar):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    await engine.tick()
    await engine.tick()
    assert fiware_falso.comandos == []


async def test_uma_chamada_list_entities_por_ciclo(engine, fiware_falso, cadastrar):
    for numero in ("001", "002", "003"):
        cadastrar(numero)
    fiware_falso.entidades = [entidade(n) for n in ("001", "002", "003")]
    await engine.tick()
    assert fiware_falso.chamadas_listar == 1


async def test_frota_vazia_nao_chama_fiware(engine, fiware_falso, fleet):
    await engine.tick()
    assert fiware_falso.chamadas_listar == 0
    assert fleet.snapshot() == []


async def test_acima_do_maximo_abre_alerta_e_envia_blink_uma_vez(engine, fiware_falso,
                                                                 cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]  # sem repetição
    assert [(a.attr, a.value) for a in alert_log.open_alerts()] == [("temperature", 21.0)]


async def test_abaixo_do_minimo_abre_alerta(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", h=40.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_hum"]
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", h=51.0)]  # dentro, mas sem folga (min 50 + 2)
    await engine.tick()
    assert fiware_falso.comandos == []
    assert len(alert_log.open_alerts()) == 1
    fiware_falso.entidades = [entidade("001", h=53.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []


async def test_volta_a_faixa_fecha_alerta_e_envia_alert_off(engine, fiware_falso, cadastrar,
                                                           alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=15.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []
    assert alert_log.list()[0].closed_at == "2026-10-08T12:00:00+00:00"


async def test_histerese_segura_alerta_perto_do_limite(engine, fiware_falso, cadastrar,
                                                       alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=17.8)]  # dentro, mas a menos de 0,5 do máximo
    await engine.tick()
    assert fiware_falso.comandos == []
    assert len(alert_log.open_alerts()) == 1
    fiware_falso.entidades = [entidade("001", t=17.4)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]


async def test_histerese_so_vale_do_lado_violado(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", l=40.0)]  # excesso de luz (faixa 0–30)
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", l=0.0)]  # adega escura
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []


async def test_duas_anomalias_temperatura_por_ultimo(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0, h=40.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_hum", "blink_temp"]
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, h=60.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=15.0, h=60.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]


async def test_leitura_ausente_nao_muda_estado(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=None)]
    await engine.tick()
    assert fiware_falso.comandos == []
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]


async def test_anomalia_numa_vinheria_nao_afeta_outra(engine, fiware_falso, cadastrar, fleet):
    cadastrar("001")
    cadastrar("002", name="Vinheria Mineira", city="Minas Gerais")
    fiware_falso.entidades = [entidade("001"), entidade("002")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001"), entidade("002", t=21.0)]
    await engine.tick()
    assert comandos(fiware_falso, E1) == []
    assert comandos(fiware_falso, E2) == ["alert_off", "blink_temp"]
    assert fleet.status_of("vinheria001") == "ok"
    assert fleet.status_of("vinheria002") == "alerta"


async def test_faixa_nova_vale_no_proximo_ciclo(engine, fiware_falso, cadastrar, limits,
                                                alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    limits.update("vinheria001", DEFAULT_LIMITS.model_copy(
        update={"temperature": AttrLimits(min=12, max=25)}))
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []


async def test_faixa_pendente_envia_set_limits(engine, fiware_falso, cadastrar, limits):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    limits.update("vinheria001", Limits(temperature=AttrLimits(min=10, max=16),
                                        humidity=DEFAULT_LIMITS.humidity,
                                        luminosity=DEFAULT_LIMITS.luminosity))
    engine.mark_limits_pending("vinheria001")
    await engine.tick()
    assert fiware_falso.comandos == [(E1, "set_limits", "10,16,50,70,0,30")]
    fiware_falso.comandos.clear()
    await engine.tick()
    assert fiware_falso.comandos == []


async def test_retrato_da_frota_tem_valores_score_e_alertas(engine, fiware_falso, cadastrar,
                                                            fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    [status] = fleet.snapshot()
    assert (status.device_id, status.name, status.city) == (
        "vinheria001", "Vinheria Paulista", "São Paulo")
    assert status.status == "alerta"
    assert status.offline_reason is None
    assert status.last_seen == "2026-10-08T11:59:58.000Z"
    assert status.seconds_since == 2
    assert (status.current.temperature, status.current.humidity,
            status.current.luminosity) == (21.0, 60.0, 10.0)
    assert status.score == 83.3  # temperatura 50 (3 °C acima numa faixa de 6), demais 100
    assert [(a.attr, a.value, a.since) for a in status.active_alerts] == [
        ("temperature", 21.0, "2026-10-08T12:00:00+00:00")]
    assert fleet.updated_at == "2026-10-08T12:00:00+00:00"
    assert fleet.fiware_online is True
```

- [ ] **Passo 4: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_trigger_engine.py -v`
Expected: erro de coleta `ModuleNotFoundError: No module named 'app.services.trigger_engine'` (vindo do `conftest.py`).

- [ ] **Passo 5: implementar `backend/app/services/trigger_engine.py`**

```python
"""
Motor de alertas da frota (o poller do "backend decide, ESP32 obedece").

A cada ciclo faz UMA chamada list_entities ao Orion e, para cada vinheria
cadastrada, decide entre:
- offline: sem leitura há mais de offline_seconds;
- configurando: ESP32 ligado que ainda não recebeu a faixa (configured != 1).
  O motor manda o set_limits na hora e não avalia alertas até ele confirmar;
- alerta ou ok: compara cada atributo com a faixa, com folga (histerese)
  para fechar.

Se a EC2 não responde por mais de offline_seconds, a frota inteira aparece
offline (motivo "fiware") e um único alerta da EC2 vai para o histórico.

O motor só manda o padrão de alerta quando o conjunto de atributos em
alerta muda ou quando precisa ressincronizar o ESP32, então um comando
manual do painel (RF09) não é desfeito no ciclo seguinte.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import ConfigStore
from app.models.schemas import AttrLimits, CurrentReading, Device, Limits
from app.models.schemas_fleet import FIWARE_ALERT_ID, SensorValues, VinheriaStatus
from app.services.alert_log import AlertLog
from app.services.alert_tracker import OFFLINE, AlertTracker
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fiware_errors import FiwareError
from app.services.fleet_state import FleetState
from app.services.limits import LimitsStore, limits_to_command_value
from app.services.quality_score import quality_score
from app.services.readings import reading_from_entity
from app.services.trigger_rules import (
    DEFAULT_HYSTERESIS,
    SENSOR_ORDER,
    can_close,
    command_plan,
    direction,
    hysteresis_margin,
    is_offline,
    parse_instant,
    seconds_since,
)

log = logging.getLogger(__name__)


def _agora_utc() -> datetime:
    """Relógio padrão do motor (os testes injetam outro)."""
    return datetime.now(timezone.utc)


def _iso(instante: datetime) -> str:
    """Instante no formato gravado no SQLite (ISO 8601, segundos)."""
    return instante.isoformat(timespec="seconds")


class TriggerEngine:
    """Avalia a frota a cada ciclo, abre e fecha alertas e comanda os ESP32."""

    def __init__(self, registry: DeviceRegistry, limits: LimitsStore, alerts: AlertLog,
                 fiware: FiwareClient, config: ConfigStore, fleet: FleetState,
                 clock=_agora_utc, sleep=asyncio.sleep,
                 hysteresis: dict[str, float] | None = None):
        self._registry = registry
        self._limits = limits
        self._fiware = fiware
        self._config = config
        self._fleet = fleet
        self._clock = clock
        self._sleep = sleep
        self._hysteresis = hysteresis or DEFAULT_HYSTERESIS
        self._tracker = AlertTracker(alerts)
        # device_id -> último conjunto de atributos em alerta entregue ao ESP32;
        # ausente significa "precisa ressincronizar o padrão de alerta"
        self._synced: dict[str, frozenset[str]] = {}
        # ESP32 que já têm a faixa atual (set_limits entregue)
        self._faixa_ok: set[str] = set()
        self._loaded = False
        # Estado da EC2: instante da primeira falha, se está fora e quando voltou
        self._fiware_falha_desde: datetime | None = None
        self._fiware_offline = False
        self._fiware_voltou: datetime | None = None

    def mark_limits_pending(self, device_id: str) -> None:
        """A faixa mudou e não chegou ao ESP32: o próximo ciclo envia set_limits."""
        self._faixa_ok.discard(device_id)

    async def run(self) -> None:
        """Laço em fundo: um tick a cada poll_seconds (lido a cada volta)."""
        while True:
            try:
                await self.tick()
            except Exception:  # o poller não pode morrer por causa de um ciclo ruim
                log.exception("falha inesperada no ciclo do poller; sigo no próximo")
            await self._sleep(self._config.get().poll_seconds)

    async def tick(self) -> None:
        """Uma passada pela frota inteira (testável sem o laço)."""
        if not self._loaded:
            self._retomar()
        agora = self._clock()
        offline_seconds = self._config.get().offline_seconds
        devices = self._registry.list()
        registrados = {device.device_id for device in devices}
        self._tracker.close_except(registrados | {FIWARE_ALERT_ID}, _iso(agora))
        self._esquecer_removidos(registrados)
        if not devices:
            self._publicar([], agora)
            return
        try:
            entidades = await self._fiware.list_entities()
        except FiwareError as exc:
            log.warning("poller sem resposta do FIWARE (%s)", exc.message)
            self._fiware_fora(devices, agora, offline_seconds)
            return
        self._fiware_de_volta(agora)
        por_id = {entidade.get("id"): entidade for entidade in entidades}
        statuses = []
        for device in devices:
            statuses.append(await self._avaliar(
                device, por_id.get(device.entity_id, {}), agora, offline_seconds))
        self._publicar(statuses, agora)

    # ----- uma vinheria -----------------------------------------------------------

    async def _avaliar(self, device: Device, entidade: dict, agora: datetime,
                       offline_seconds: int) -> VinheriaStatus:
        """Decide offline, configurando, alerta ou ok, e sincroniza o ESP32."""
        device_id = device.device_id
        leitura = reading_from_entity(device_id, entidade)
        visto = parse_instant(leitura.time_instant)
        limites = self._limits.get(device_id)
        if is_offline(visto, parse_instant(device.created_at), agora, offline_seconds):
            if not self._em_carencia(agora, offline_seconds):
                self._tracker.open(device_id, OFFLINE, None, None, _iso(agora))
            self._esquecer_esp32(device_id)
            return self._retrato(device, leitura, visto, limites, "offline", agora)
        self._tracker.close(device_id, OFFLINE, _iso(agora))
        if leitura.configured is not True:
            # ESP32 ligado sem faixa: manda agora e não avalia alertas até ele confirmar
            self._synced.pop(device_id, None)
            await self._enviar_faixa(device, limites)
            return self._retrato(device, leitura, visto, limites, "configurando", agora)
        for attr in SENSOR_ORDER:
            self._avaliar_atributo(device_id, attr, getattr(leitura, attr),
                                   getattr(limites, attr), agora)
        await self._sincronizar(device, limites)
        status = "alerta" if self._tracker.active_sensors(device_id) else "ok"
        return self._retrato(device, leitura, visto, limites, status, agora)

    def _avaliar_atributo(self, device_id: str, attr: str, value: float | None,
                          faixa: AttrLimits, agora: datetime) -> None:
        """Abre o alerta ao sair da faixa; fecha ao voltar com folga (histerese)."""
        if value is None:
            return
        aberto = self._tracker.get(device_id, attr)
        if aberto is None:
            lado = direction(value, faixa.min, faixa.max)
            if lado is not None:
                self._tracker.open(device_id, attr, value, lado, _iso(agora))
            return
        margem = hysteresis_margin(attr, faixa.min, faixa.max, self._hysteresis)
        if can_close(value, faixa.min, faixa.max, aberto.side, margem):
            self._tracker.close(device_id, attr, _iso(agora))

    async def _enviar_faixa(self, device: Device, limites: Limits) -> None:
        """Manda o set_limits; se falhar, o próximo ciclo tenta de novo."""
        try:
            await self._fiware.send_command(device.entity_id, "set_limits",
                                            limits_to_command_value(limites))
            self._faixa_ok.add(device.device_id)
        except FiwareError as exc:
            log.warning("set_limits para %s falhou (%s); tento de novo no próximo ciclo",
                        device.device_id, exc.message)

    async def _sincronizar(self, device: Device, limites: Limits) -> None:
        """Leva ao ESP32 a faixa (se não chegou) e o padrão de alerta (se mudou)."""
        device_id = device.device_id
        if device_id not in self._faixa_ok:
            await self._enviar_faixa(device, limites)
            if device_id not in self._faixa_ok:
                return
        ativos = self._tracker.active_sensors(device_id)
        if self._synced.get(device_id) == ativos:
            return
        try:
            for comando in command_plan(ativos):
                await self._fiware.send_command(device.entity_id, comando)
            self._synced[device_id] = ativos
        except FiwareError as exc:
            log.warning("comando para %s falhou (%s); tento de novo no próximo ciclo",
                        device_id, exc.message)

    def _retrato(self, device: Device, leitura: CurrentReading, visto: datetime | None,
                 limites: Limits, status: str, agora: datetime) -> VinheriaStatus:
        """Monta o VinheriaStatus da vinheria neste ciclo."""
        nota, _ = quality_score(leitura, limites)
        return VinheriaStatus(
            device_id=device.device_id, name=device.name, city=device.city, status=status,
            offline_reason="sem_leitura" if status == "offline" else None,
            last_seen=leitura.time_instant, seconds_since=seconds_since(visto, agora),
            current=SensorValues(temperature=leitura.temperature, humidity=leitura.humidity,
                                 luminosity=leitura.luminosity),
            # Valor antigo de vinheria offline não gera nota
            score=None if status == "offline" else nota,
            active_alerts=self._tracker.active(device.device_id),
        )

    # ----- EC2 / FIWARE -------------------------------------------------------------

    def _fiware_fora(self, devices: list[Device], agora: datetime, offline_seconds: int) -> None:
        """FIWARE sem resposta: falha curta não muda nada; longa marca a frota offline."""
        if self._fiware_falha_desde is None:
            self._fiware_falha_desde = agora
        if not self._fiware_offline:
            if (agora - self._fiware_falha_desde).total_seconds() <= offline_seconds:
                return
            self._fiware_offline = True
            self._tracker.open(FIWARE_ALERT_ID, OFFLINE, None, None,
                               _iso(self._fiware_falha_desde))
            # Na volta, todos os ESP32 recebem faixa e padrão de alerta de novo
            self._synced.clear()
            self._faixa_ok.clear()
        self._publicar([self._retrato_sem_fiware(device, agora) for device in devices], agora)

    def _fiware_de_volta(self, agora: datetime) -> None:
        """FIWARE respondeu: fecha o alerta da EC2 e abre a carência dos offline."""
        self._fiware_falha_desde = None
        if self._fiware_offline:
            self._fiware_offline = False
            self._tracker.close(FIWARE_ALERT_ID, OFFLINE, _iso(agora))
            self._fiware_voltou = agora

    def _em_carencia(self, agora: datetime, offline_seconds: int) -> bool:
        """Logo após a EC2 voltar, os ESP32 ainda reconectam: não abre alerta offline."""
        return (self._fiware_voltou is not None
                and (agora - self._fiware_voltou).total_seconds() <= offline_seconds)

    def _retrato_sem_fiware(self, device: Device, agora: datetime) -> VinheriaStatus:
        """Vinheria offline por causa da EC2, com os últimos valores conhecidos."""
        anterior = self._fleet.get(device.device_id)
        last_seen = anterior.last_seen if anterior else None
        return VinheriaStatus(
            device_id=device.device_id, name=device.name, city=device.city,
            status="offline", offline_reason="fiware", last_seen=last_seen,
            seconds_since=seconds_since(parse_instant(last_seen), agora),
            current=anterior.current if anterior else SensorValues(),
            score=None, active_alerts=self._tracker.active(device.device_id),
        )

    # ----- estado ---------------------------------------------------------------------

    def _retomar(self) -> None:
        """Primeira passada: retoma os alertas abertos no SQLite.

        Se o backend reiniciou com a EC2 fora, o alerta dela volta aberto e o
        motor segue considerando a EC2 fora até o FIWARE responder.
        """
        for alerta in self._tracker.load():
            if alerta.device_id == FIWARE_ALERT_ID:
                self._fiware_offline = True
                self._fiware_falha_desde = parse_instant(alerta.opened_at)
        self._loaded = True

    def _publicar(self, statuses: list[VinheriaStatus], agora: datetime) -> None:
        """Entrega o retrato do ciclo ao FleetState, com o estado da EC2."""
        desde = (_iso(self._fiware_falha_desde)
                 if self._fiware_offline and self._fiware_falha_desde else None)
        self._fleet.replace(statuses, _iso(agora), fiware_online=not self._fiware_offline,
                            fiware_offline_since=desde)

    def _esquecer_esp32(self, device_id: str) -> None:
        """O ESP32 pode ter reiniciado: na volta, faixa e padrão de alerta vão de novo."""
        self._synced.pop(device_id, None)
        self._faixa_ok.discard(device_id)

    def _esquecer_removidos(self, registrados: set[str]) -> None:
        """Descarta o estado de vinherias removidas do cadastro."""
        for device_id in [d for d in self._synced if d not in registrados]:
            del self._synced[device_id]
        self._faixa_ok &= registrados
```

- [ ] **Passo 6: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_trigger_engine.py -v` → 15 passed.
Run: `.venv/Scripts/python -m pytest -q` → **235 passed**.
Run (bash): `wc -l app/services/trigger_engine.py` → até ~270 linhas. Se passar de 280, **pare e reporte** (dividir o arquivo é decisão de planejamento).

- [ ] **Passo 7: commit**

```bash
git add app/services/trigger_engine.py tests/fakes.py tests/conftest.py tests/test_trigger_engine.py
git commit -m "feat: adiciona motor de alertas da frota com histerese e plano de comandos"
```

---

## Subtarefa 4.11 — Motor: configuração do ESP32, offline e EC2 fora (R8, R9, R10)

**Files:**
- Create: `backend/tests/test_trigger_config.py`, `backend/tests/test_trigger_offline.py`, `backend/tests/test_trigger_fiware.py`
- Modify: `backend/app/services/trigger_engine.py` **só se** algum teste falhar (ver Passo 4)

**Interfaces:**
- Consumes: tudo da 4.10.

- [ ] **Passo 1: testes de configuração**

`backend/tests/test_trigger_config.py`:

```python
"""Testes do motor: ESP32 sem faixa recebe na hora e não dispara alerta (spec R8)."""
import pytest

from app.services.fiware_errors import FiwareUnavailable
from tests.fakes import entidade

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"


def comandos(fiware, entity_id=E1):
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def test_sem_configuracao_recebe_faixa_na_hora_e_nao_avalia(engine, fiware_falso,
                                                                  cadastrar, alert_log, fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0, c=0)]  # fora da faixa, mas sem configurar
    await engine.tick()
    assert fiware_falso.comandos == [(E1, "set_limits", "12,18,50,70,0,30")]
    assert alert_log.open_alerts() == []
    assert fleet.status_of("vinheria001") == "configurando"
    fiware_falso.comandos.clear()
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]  # ainda c=0: manda de novo


async def test_configured_ausente_conta_como_nao_configurado(engine, fiware_falso, cadastrar,
                                                             fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", c=None)]  # firmware antigo, sem o atributo c
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]
    assert fleet.status_of("vinheria001") == "configurando"


async def test_apos_configurar_sincroniza_alerta_sem_reenviar_faixa(engine, fiware_falso,
                                                                    cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0, c=0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, c=1)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]


async def test_reinicio_do_esp32_reenvia_faixa_e_depois_o_alerta(engine, fiware_falso,
                                                                 cadastrar, alert_log, fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()  # faixa + alerta de temperatura
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, c=0)]  # ESP32 reiniciou
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]
    assert fleet.status_of("vinheria001") == "configurando"
    assert len(alert_log.open_alerts()) == 1
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, c=1)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert len(alert_log.open_alerts()) == 1


async def test_falha_ao_enviar_faixa_tenta_no_proximo_ciclo(engine, fiware_falso, cadastrar):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", c=0)]
    fiware_falso.erro_comando = FiwareUnavailable("orion", "sem conexão")
    await engine.tick()
    assert fiware_falso.comandos == []
    fiware_falso.erro_comando = None
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]
```

- [ ] **Passo 2: testes de offline e falhas**

`backend/tests/test_trigger_offline.py`:

```python
"""Testes do motor: vinheria offline, retomada, órfãos e falhas (spec R9)."""
import pytest

from app.services.fiware_errors import FiwareUnavailable
from app.services.trigger_engine import TriggerEngine
from tests.fakes import entidade, instante_de

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"


class _Parar(BaseException):
    """Interrompe o laço do run() no teste (não é capturada como Exception)."""


def comandos(fiware, entity_id=E1):
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def primeira_passada(engine, fiware):
    await engine.tick()
    fiware.comandos.clear()


async def test_sem_leitura_ha_mais_de_offline_seconds_abre_alerta_offline_sem_comando(
        engine, fiware_falso, cadastrar, alert_log, fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]  # leitura de 11:59:58
    await primeira_passada(engine, fiware_falso)
    relogio.avancar(40)  # 42 s sem leitura (limite 30)
    await engine.tick()
    await engine.tick()
    assert fiware_falso.comandos == []
    assert [(a.attr, a.value) for a in alert_log.open_alerts()] == [("offline", None)]
    [status] = fleet.snapshot()
    assert (status.status, status.offline_reason) == ("offline", "sem_leitura")
    assert status.score is None
    assert status.seconds_since == 42


async def test_volta_do_offline_fecha_alerta_e_ressincroniza(engine, fiware_falso, cadastrar,
                                                             alert_log, fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    relogio.avancar(40)
    await engine.tick()
    fiware_falso.entidades = [entidade("001", instante=instante_de(relogio, 1))]
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits", "alert_off"]
    assert alert_log.open_alerts() == []
    assert alert_log.list()[0].duration_seconds == 0
    assert fleet.status_of("vinheria001") == "ok"


async def test_volta_do_offline_com_anomalia_reenvia_blink(engine, fiware_falso, cadastrar,
                                                           alert_log, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    relogio.avancar(40)  # a mesma leitura velha: offline
    await engine.tick()
    fiware_falso.entidades = [entidade("001", t=21.0, instante=instante_de(relogio, 1))]
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits", "alert_off", "blink_temp"]
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]


async def test_vinheria_recem_cadastrada_sem_leitura_fica_configurando_ate_o_limite(
        engine, fiware_falso, cadastrar, alert_log, fleet, relogio):
    cadastrar("001", created_at=relogio.iso(segundos_atras=10))
    fiware_falso.entidades = []  # ainda sem entidade no Orion
    await engine.tick()
    [status] = fleet.snapshot()
    assert status.status == "configurando"
    assert status.current.temperature is None
    assert status.score is None
    assert alert_log.open_alerts() == []
    relogio.avancar(25)  # 35 s desde o cadastro
    await engine.tick()
    assert [a.attr for a in alert_log.open_alerts()] == ["offline"]


async def test_vinheria_antiga_sem_entidade_fica_offline(engine, fiware_falso, cadastrar,
                                                         alert_log, fleet):
    cadastrar("001")  # cadastrada em 07/10
    fiware_falso.entidades = []
    await engine.tick()
    assert fleet.status_of("vinheria001") == "offline"
    assert [a.attr for a in alert_log.open_alerts()] == ["offline"]
    assert fiware_falso.comandos == []


async def test_falha_no_comando_tenta_de_novo_no_proximo_ciclo(engine, fiware_falso, cadastrar,
                                                               alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.erro_comando = FiwareUnavailable("orion", "sem conexão")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    assert fiware_falso.comandos == []
    fiware_falso.erro_comando = None
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert len(alert_log.open_alerts()) == 1


async def test_alertas_abertos_sao_retomados_apos_reinicio(engine, fiware_falso, cadastrar,
                                                           alert_log):
    cadastrar("001")
    alert_log.open("vinheria001", "temperature", 21.0, "2026-10-08T11:00:00+00:00")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    assert len(alert_log.open_alerts()) == 1
    assert comandos(fiware_falso) == ["set_limits", "alert_off", "blink_temp"]


async def test_alerta_retomado_fecha_quando_volta_a_faixa(engine, fiware_falso, cadastrar,
                                                          alert_log):
    cadastrar("001")
    alert_log.open("vinheria001", "temperature", 21.0, "2026-10-08T11:00:00+00:00")
    fiware_falso.entidades = [entidade("001", t=17.9)]  # dentro; lado desconhecido fecha
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert comandos(fiware_falso) == ["set_limits", "alert_off"]


async def test_vinheria_removida_tem_alertas_fechados(engine, fiware_falso, cadastrar, conn,
                                                      alert_log, fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    with conn:
        conn.execute("DELETE FROM devices WHERE device_id = 'vinheria001'")
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert alert_log.list()[0].closed_at is not None
    assert fleet.snapshot() == []


async def test_run_repete_tick_e_sobrevive_a_erro(registry, limits, alert_log, fiware_falso,
                                                  store, fleet, relogio):
    esperas = []

    async def sleep_falso(segundos):
        esperas.append(segundos)
        if len(esperas) == 3:
            raise _Parar

    motor = TriggerEngine(registry, limits, alert_log, fiware_falso, store, fleet,
                          clock=relogio, sleep=sleep_falso)
    chamadas = []

    async def tick_falso():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("ciclo ruim")

    motor.tick = tick_falso
    with pytest.raises(_Parar):
        await motor.run()
    assert len(chamadas) == 3
    assert esperas == [5, 5, 5]  # poll_seconds padrão
```

- [ ] **Passo 3: testes da EC2 fora**

`backend/tests/test_trigger_fiware.py`:

```python
"""Testes do motor: EC2/FIWARE fora do ar (spec R10)."""
import pytest

from app.services.fiware_errors import FiwareUnavailable
from tests.fakes import entidade, instante_de

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
FORA = FiwareUnavailable("orion", "sem conexão")


def comandos(fiware, entity_id=E1):
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def derrubar_ec2(engine, fiware, relogio):
    """Primeira falha agora (12:00:00) e outra 31 s depois: EC2 fora."""
    fiware.erro_listar = FORA
    await engine.tick()
    relogio.avancar(31)
    await engine.tick()


async def test_falha_curta_do_fiware_mantem_retrato(engine, fiware_falso, cadastrar, alert_log,
                                                    fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    fiware_falso.comandos.clear()
    antes = fleet.snapshot()
    fiware_falso.erro_listar = FORA
    await engine.tick()
    relogio.avancar(20)
    await engine.tick()
    assert fleet.snapshot() == antes
    assert fleet.fiware_online is True
    assert alert_log.open_alerts() == []
    assert fiware_falso.comandos == []


async def test_ec2_fora_marca_offline_com_um_alerta(engine, fiware_falso, cadastrar, alert_log,
                                                    fleet, relogio):
    cadastrar("001")
    cadastrar("002", name="Vinheria Mineira", city="Minas Gerais")
    fiware_falso.entidades = [entidade("001"), entidade("002")]
    await engine.tick()
    fiware_falso.comandos.clear()
    await derrubar_ec2(engine, fiware_falso, relogio)
    assert fleet.fiware_online is False
    assert fleet.fiware_offline_since == "2026-10-08T12:00:00+00:00"
    statuses = fleet.snapshot()
    assert [(s.status, s.offline_reason) for s in statuses] == [("offline", "fiware")] * 2
    assert statuses[0].current.temperature == 15.0  # último valor conhecido
    assert statuses[0].score is None
    abertos = alert_log.open_alerts()
    assert [(a.device_id, a.attr) for a in abertos] == [("fiware", "offline")]
    assert abertos[0].opened_at == "2026-10-08T12:00:00+00:00"
    assert fiware_falso.comandos == []


async def test_ec2_volta_fecha_alerta_e_ressincroniza(engine, fiware_falso, cadastrar,
                                                      alert_log, fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    fiware_falso.comandos.clear()
    await derrubar_ec2(engine, fiware_falso, relogio)
    fiware_falso.erro_listar = None
    fiware_falso.entidades = [entidade("001", instante=instante_de(relogio, 1))]
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert alert_log.list(device_id="fiware")[0].duration_seconds == 31
    assert fleet.fiware_online is True
    assert fleet.status_of("vinheria001") == "ok"
    assert comandos(fiware_falso) == ["set_limits", "alert_off"]


async def test_leitura_velha_logo_apos_a_volta_nao_abre_offline(engine, fiware_falso,
                                                                cadastrar, alert_log, fleet,
                                                                relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]  # leitura de 11:59:58
    await engine.tick()
    await derrubar_ec2(engine, fiware_falso, relogio)
    fiware_falso.erro_listar = None  # EC2 voltou, mas o ESP32 ainda não publicou
    await engine.tick()
    [status] = fleet.snapshot()
    assert (status.status, status.offline_reason) == ("offline", "sem_leitura")
    assert alert_log.open_alerts() == []
    relogio.avancar(31)  # passou a carência e a leitura não veio
    await engine.tick()
    assert [(a.device_id, a.attr) for a in alert_log.open_alerts()] == [
        ("vinheria001", "offline")]


async def test_alerta_da_ec2_retomado_apos_reinicio_fecha_quando_volta(engine, fiware_falso,
                                                                      cadastrar, alert_log,
                                                                      fleet):
    cadastrar("001")
    alert_log.open("fiware", "offline", None, "2026-10-08T11:50:00+00:00")
    fiware_falso.erro_listar = FORA
    await engine.tick()
    assert fleet.fiware_online is False  # segue fora desde 11:50
    assert fleet.fiware_offline_since == "2026-10-08T11:50:00+00:00"
    fiware_falso.erro_listar = None
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert fleet.fiware_online is True
```

- [ ] **Passo 4: rodar**

Run: `.venv/Scripts/python -m pytest tests/test_trigger_config.py tests/test_trigger_offline.py tests/test_trigger_fiware.py -v`
Expected: 20 passed (o motor da 4.10 já cobre estes casos). **Se algum falhar:** é defeito do motor. Aplique `superpowers:systematic-debugging`, reporte o teste, o erro exato e a hipótese, e espere orientação antes de mudar o `trigger_engine.py`.

- [ ] **Passo 5: rodar a suíte inteira**

Run: `.venv/Scripts/python -m pytest -q` → **255 passed**.

- [ ] **Passo 6: commit**

```bash
git add tests/test_trigger_config.py tests/test_trigger_offline.py tests/test_trigger_fiware.py
git commit -m "test: cobre configuracao do ESP32, offline e EC2 fora no motor de alertas"
```

---

## Subtarefa 4.12 — Controle da vinheria: faixa na hora e comandos manuais (R11)

**Files:**
- Create: `backend/app/services/device_control.py`, `backend/tests/test_device_control.py`
- Modify: `backend/app/services/registry_errors.py`

**Interfaces:**
- Consumes: `DeviceRegistry.get`, `LimitsStore.get/update`, `limits_to_orion_attrs`, `limits_to_command_value`, `FiwareClient.update_attrs/send_command`, `FleetState.status_of`, `TriggerEngine.mark_limits_pending`, `LimitsUpdate`.
- Produces: `DeviceUnavailable(RegistryError)`; `DeviceControl(registry, limits, fiware, fleet, engine)` com `get_limits`, `update_limits -> LimitsUpdate`, `send_command`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_device_control.py`:

```python
"""Testes do controle da vinheria: faixa na hora e comandos manuais (spec R11)."""
import pytest

from app.models.schemas import AttrLimits, Limits
from app.services.device_control import DeviceControl
from app.services.fiware_errors import FiwareUnavailable
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import DeviceNotFound, DeviceUnavailable
from tests.fakes import status_vinheria

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
NOVA = Limits(temperature=AttrLimits(min=10, max=16),
              humidity=AttrLimits(min=55, max=75),
              luminosity=AttrLimits(min=0, max=20))
T0 = "2026-10-08T12:00:00+00:00"


class MotorFalso:
    """Registra os pedidos de set_limits pendente."""

    def __init__(self):
        self.pendentes = []

    def mark_limits_pending(self, device_id):
        self.pendentes.append(device_id)


@pytest.fixture
def motor_falso():
    return MotorFalso()


@pytest.fixture
def control(registry, limits, fiware_falso, fleet, motor_falso):
    return DeviceControl(registry, limits, fiware_falso, fleet, motor_falso)


async def test_update_limits_publica_grava_e_envia_na_hora(control, cadastrar, fiware_falso,
                                                           limits, motor_falso):
    cadastrar("001")
    resultado = await control.update_limits("vinheria001", NOVA)
    assert (resultado.device_id, resultado.limits, resultado.device_sync) == (
        "vinheria001", NOVA, "enviado")
    assert fiware_falso.atualizacoes == [(E1, {"temp_min": 10, "temp_max": 16,
                                               "hum_min": 55, "hum_max": 75,
                                               "lux_min": 0, "lux_max": 20})]
    assert fiware_falso.comandos == [(E1, "set_limits", "10,16,55,75,0,20")]
    assert limits.get("vinheria001") == NOVA
    assert motor_falso.pendentes == []


async def test_update_limits_offline_fica_pendente(control, cadastrar, fiware_falso, fleet,
                                                   limits, motor_falso):
    cadastrar("001")
    fleet.replace([status_vinheria("vinheria001", "offline")], T0)
    resultado = await control.update_limits("vinheria001", NOVA)
    assert resultado.device_sync == "pendente"
    assert fiware_falso.comandos == []
    assert limits.get("vinheria001") == NOVA
    assert motor_falso.pendentes == ["vinheria001"]


async def test_update_limits_falha_no_envio_fica_pendente(control, cadastrar, fiware_falso,
                                                          limits, motor_falso):
    cadastrar("001")
    fiware_falso.erro_comando = FiwareUnavailable("orion", "sem conexão")
    resultado = await control.update_limits("vinheria001", NOVA)
    assert resultado.device_sync == "pendente"
    assert limits.get("vinheria001") == NOVA
    assert motor_falso.pendentes == ["vinheria001"]


async def test_update_limits_fiware_fora_nao_grava(control, cadastrar, fiware_falso, limits,
                                                   motor_falso):
    cadastrar("001")
    fiware_falso.erro_update = FiwareUnavailable("orion", "sem conexão")
    with pytest.raises(FiwareUnavailable):
        await control.update_limits("vinheria001", NOVA)
    assert limits.get("vinheria001") == DEFAULT_LIMITS
    assert fiware_falso.comandos == []
    assert motor_falso.pendentes == []


async def test_update_limits_inexistente_sem_rede(control, fiware_falso):
    with pytest.raises(DeviceNotFound):
        await control.update_limits("vinheria009", NOVA)
    assert fiware_falso.atualizacoes == []


def test_get_limits(control, cadastrar):
    cadastrar("001")
    assert control.get_limits("vinheria001") == DEFAULT_LIMITS


def test_get_limits_inexistente(control):
    with pytest.raises(DeviceNotFound):
        control.get_limits("vinheria009")


async def test_send_command_envia(control, cadastrar, fiware_falso):
    cadastrar("001")
    await control.send_command("vinheria001", "blink_hum")
    assert fiware_falso.comandos == [(E1, "blink_hum", "")]


async def test_send_command_offline_recusa(control, cadastrar, fiware_falso, fleet):
    cadastrar("001")
    fleet.replace([status_vinheria("vinheria001", "offline")], T0)
    with pytest.raises(DeviceUnavailable, match="offline"):
        await control.send_command("vinheria001", "blink_temp")
    assert fiware_falso.comandos == []


async def test_send_command_configurando_recusa(control, cadastrar, fiware_falso, fleet):
    cadastrar("001")
    fleet.replace([status_vinheria("vinheria001", "configurando")], T0)
    with pytest.raises(DeviceUnavailable, match="faixa"):
        await control.send_command("vinheria001", "blink_temp")
    assert fiware_falso.comandos == []


async def test_send_command_inexistente_sem_rede(control, fiware_falso):
    with pytest.raises(DeviceNotFound):
        await control.send_command("vinheria009", "alert_off")
    assert fiware_falso.comandos == []
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_device_control.py -v`
Expected: erro de coleta `ImportError: cannot import name 'DeviceUnavailable'` (ou `ModuleNotFoundError` de `device_control`).

- [ ] **Passo 3: acrescentar `DeviceUnavailable` em `backend/app/services/registry_errors.py`**

Depois de `DeviceAlreadyExists`:

```python
class DeviceUnavailable(RegistryError):
    """A vinheria está offline ou aguardando a faixa e não recebe comandos de alerta."""
```

- [ ] **Passo 4: implementar `backend/app/services/device_control.py`**

```python
"""
Controle de uma vinheria pelo painel: faixa ideal (RF06) e alertas
disparados à mão (RF09).

A faixa vai primeiro para o Orion e só depois para o SQLite: se o FIWARE
falha, nada muda e o usuário tenta de novo. Em seguida o set_limits sai na
hora para o ESP32; se a vinheria está offline ou o envio falha, o motor é
avisado e manda no próximo ciclo em que ela estiver online.
"""
import logging

from app.models.schemas import Limits
from app.models.schemas_fleet import LimitsUpdate
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fiware_errors import FiwareError
from app.services.fleet_state import FleetState
from app.services.limits import LimitsStore, limits_to_command_value, limits_to_orion_attrs
from app.services.registry_errors import DeviceUnavailable

log = logging.getLogger(__name__)


class DeviceControl:
    """Faixa ideal e comandos manuais de uma vinheria."""

    def __init__(self, registry: DeviceRegistry, limits: LimitsStore, fiware: FiwareClient,
                 fleet: FleetState, engine):
        # engine: qualquer objeto com mark_limits_pending (o TriggerEngine)
        self._registry = registry
        self._limits = limits
        self._fiware = fiware
        self._fleet = fleet
        self._engine = engine

    def get_limits(self, device_id: str) -> Limits:
        """Faixa atual; DeviceNotFound se a vinheria não está cadastrada."""
        self._registry.get(device_id)
        return self._limits.get(device_id)

    async def update_limits(self, device_id: str, limits: Limits) -> LimitsUpdate:
        """Publica a faixa no Orion, grava no SQLite e manda o set_limits na hora."""
        device = self._registry.get(device_id)
        await self._fiware.update_attrs(device.entity_id, limits_to_orion_attrs(limits))
        self._limits.update(device_id, limits)
        enviado = False
        if self._fleet.status_of(device_id) != "offline":
            try:
                await self._fiware.send_command(device.entity_id, "set_limits",
                                                limits_to_command_value(limits))
                enviado = True
            except FiwareError as exc:
                log.warning("set_limits para %s falhou (%s); o poller tenta de novo",
                            device_id, exc.message)
        if not enviado:
            self._engine.mark_limits_pending(device_id)
        return LimitsUpdate(device_id=device_id, limits=self._limits.get(device_id),
                            device_sync="enviado" if enviado else "pendente")

    async def send_command(self, device_id: str, command: str) -> None:
        """Envia um alerta manual; offline ou configurando recusa com DeviceUnavailable."""
        device = self._registry.get(device_id)
        status = self._fleet.status_of(device_id)
        if status == "offline":
            raise DeviceUnavailable(f"{device_id} está offline e não recebe comandos")
        if status == "configurando":
            raise DeviceUnavailable(
                f"{device_id} ainda não recebeu a faixa ideal e não aceita alertas")
        await self._fiware.send_command(device.entity_id, command)
```

- [ ] **Passo 5: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_device_control.py -v` → 11 passed.
Run: `.venv/Scripts/python -m pytest -q` → **266 passed**.

- [ ] **Passo 6: commit**

```bash
git add app/services/device_control.py app/services/registry_errors.py tests/test_device_control.py
git commit -m "feat: adiciona edicao da faixa com envio imediato e comandos manuais"
```

---

## Subtarefa 4.13 — Rotas de faixa, comandos, alertas e frota (R12)

**Files:**
- Create: `backend/app/api/routes_triggers.py`, `backend/app/api/routes_alerts.py`, `backend/app/api/routes_fleet.py`, `backend/tests/test_routes_control.py`
- Modify: `backend/app/api/deps.py`, `backend/app/api/errors.py`, `backend/app/main.py` (só montagem dos services e routers; o lifespan fica para a 4.14)

**Interfaces:**
- Consumes: `DeviceControl`, `AlertLog`, `FleetState`, `DeviceRegistry.list`, schemas da 4.5.
- Produces: `get_control`, `get_alert_log`, `get_fleet`; rotas da spec 4.4; `app.state.alerts`, `app.state.fleet`, `app.state.engine`, `app.state.control`.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_routes_control.py`:

```python
"""Testes das rotas de faixa, comandos, alertas e frota (spec R12).

Faixa e comandos usam um DeviceControl falso (o contrato HTTP é o que
importa aqui); alertas e frota usam as peças reais do app, com o cadastro
falso.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.schemas import Device
from app.models.schemas_fleet import LimitsUpdate
from app.services.fiware_errors import FiwareUnavailable
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import DeviceNotFound, DeviceUnavailable
from tests.fakes import status_vinheria

DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria Paulista", city="São Paulo",
                created_at="2026-10-07T21:00:00+00:00")
FAIXA = {"temperature": {"min": 10, "max": 16},
         "humidity": {"min": 55, "max": 75},
         "luminosity": {"min": 0, "max": 20}}


class ControlFalso:
    """Substitui o DeviceControl nos testes de rota."""

    def __init__(self):
        self.faixas = {}
        self.comandos = []
        self.erro = None

    def get_limits(self, device_id):
        if device_id != DEVICE.device_id:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        return DEFAULT_LIMITS

    async def update_limits(self, device_id, limits):
        if self.erro:
            raise self.erro
        self.faixas[device_id] = limits
        return LimitsUpdate(device_id=device_id, limits=limits, device_sync="enviado")

    async def send_command(self, device_id, command):
        if self.erro:
            raise self.erro
        self.comandos.append((device_id, command))


class RegistryFalso:
    """Só a listagem, usada pela rota da frota."""

    def list(self):
        return [DEVICE]


@pytest.fixture
def app(tmp_path):
    aplicacao = create_app(Settings(fiware_host="10.0.0.1",
                                    database_path=str(tmp_path / "rotas.db")))
    aplicacao.state.control = ControlFalso()
    aplicacao.state.registry = RegistryFalso()
    return aplicacao


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


def test_get_triggers_200(client):
    resposta = client.get("/api/devices/vinheria001/triggers")
    assert resposta.status_code == 200
    assert resposta.json() == DEFAULT_LIMITS.model_dump()


def test_get_triggers_404(client):
    resposta = client.get("/api/devices/vinheria009/triggers")
    assert resposta.status_code == 404
    assert resposta.json()["service"] == "registry"


def test_put_triggers_200(client, app):
    resposta = client.put("/api/devices/vinheria001/triggers", json=FAIXA)
    assert resposta.status_code == 200
    assert resposta.json() == {"device_id": "vinheria001", "limits": FAIXA,
                               "device_sync": "enviado"}
    assert app.state.control.faixas["vinheria001"].temperature.max == 16


def test_put_triggers_min_maior_que_max_422(client, app):
    invertida = {**FAIXA, "temperature": {"min": 18, "max": 12}}
    assert client.put("/api/devices/vinheria001/triggers", json=invertida).status_code == 422
    incompleta = {"temperature": FAIXA["temperature"], "humidity": FAIXA["humidity"]}
    assert client.put("/api/devices/vinheria001/triggers", json=incompleta).status_code == 422
    assert app.state.control.faixas == {}


def test_put_triggers_fiware_fora_503(client, app):
    app.state.control.erro = FiwareUnavailable("orion", "sem conexão")
    resposta = client.put("/api/devices/vinheria001/triggers", json=FAIXA)
    assert resposta.status_code == 503
    assert resposta.json()["service"] == "orion"


def test_post_command_202(client, app):
    resposta = client.post("/api/devices/vinheria001/commands", json={"command": "blink_hum"})
    assert resposta.status_code == 202
    assert resposta.json() == {"device_id": "vinheria001", "command": "blink_hum"}
    assert app.state.control.comandos == [("vinheria001", "blink_hum")]


def test_post_command_invalido_422(client, app):
    for comando in ("set_limits", "tocar_musica"):
        resposta = client.post("/api/devices/vinheria001/commands", json={"command": comando})
        assert resposta.status_code == 422
    assert app.state.control.comandos == []


def test_post_command_indisponivel_409(client, app):
    app.state.control.erro = DeviceUnavailable("vinheria001 está offline e não recebe comandos")
    resposta = client.post("/api/devices/vinheria001/commands", json={"command": "blink_temp"})
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "vinheria001 está offline e não recebe comandos",
                               "service": "registry"}


def test_get_alerts_lista_e_filtra(client, app):
    a1 = app.state.alerts.open("vinheria001", "temperature", 21.0, "2026-10-08T12:00:00+00:00")
    a2 = app.state.alerts.open("fiware", "offline", None, "2026-10-08T12:01:00+00:00")
    todos = client.get("/api/alerts").json()
    assert [a["id"] for a in todos] == [a2.id, a1.id]
    assert todos[0]["value"] is None
    so_001 = client.get("/api/alerts", params={"device_id": "vinheria001"}).json()
    assert [a["id"] for a in so_001] == [a1.id]
    so_ec2 = client.get("/api/alerts", params={"device_id": "fiware"}).json()
    assert [a["id"] for a in so_ec2] == [a2.id]
    assert len(client.get("/api/alerts", params={"limit": 1}).json()) == 1


def test_get_alerts_limit_invalido_422(client):
    assert client.get("/api/alerts", params={"limit": 0}).status_code == 422
    assert client.get("/api/alerts", params={"limit": 501}).status_code == 422


def test_get_fleet_so_vinherias_cadastradas(client, app):
    app.state.fleet.replace([status_vinheria("vinheria001", "ok"),
                             status_vinheria("vinheria099", "alerta")],
                            "2026-10-08T12:00:00+00:00")
    resposta = client.get("/api/fleet")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["fiware_online"] is True
    assert corpo["updated_at"] == "2026-10-08T12:00:00+00:00"
    assert [s["device_id"] for s in corpo["vinherias"]] == ["vinheria001"]
    assert corpo["vinherias"][0]["status"] == "ok"


def test_get_fleet_ec2_offline(client, app):
    app.state.fleet.replace([status_vinheria("vinheria001", "offline")],
                            "2026-10-08T12:00:40+00:00", fiware_online=False,
                            fiware_offline_since="2026-10-08T12:00:00+00:00")
    corpo = client.get("/api/fleet").json()
    assert corpo["fiware_online"] is False
    assert corpo["fiware_offline_since"] == "2026-10-08T12:00:00+00:00"
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_routes_control.py -v`
Expected: FAIL — 404 nas rotas novas e `AttributeError: 'State' object has no attribute 'alerts'` (ou `fleet`).

- [ ] **Passo 3: ampliar `backend/app/api/deps.py`**

Trocar a docstring do módulo por:

```python
"""
Dependências do FastAPI.

As rotas recebem os services por injeção, lidos de app.state, em vez de
importar instâncias globais. Assim os testes trocam qualquer peça sem
mexer nas rotas.
"""
```

Acrescentar aos imports:

```python
from app.services.alert_log import AlertLog
from app.services.device_control import DeviceControl
from app.services.fleet_state import FleetState
```

E ao fim do arquivo:

```python
def get_alert_log(request: Request) -> AlertLog:
    """Log de alertas da aplicação."""
    return request.app.state.alerts


def get_fleet(request: Request) -> FleetState:
    """Retrato da frota da aplicação."""
    return request.app.state.fleet


def get_control(request: Request) -> DeviceControl:
    """Controle de faixa e comandos da aplicação."""
    return request.app.state.control
```

- [ ] **Passo 4: mapear `DeviceUnavailable` em `backend/app/api/errors.py`**

Trocar o import de `registry_errors` por:

```python
from app.services.registry_errors import (
    AmbiguousVinheria,
    DeviceAlreadyExists,
    DeviceUnavailable,
    RegistryError,
)
```

E `_status_registry` por:

```python
def _status_registry(erro: RegistryError) -> int:
    """Conflito (cadastro repetido, referência ambígua, vinheria indisponível) dá 409; o resto é 404."""
    if isinstance(erro, (DeviceAlreadyExists, AmbiguousVinheria, DeviceUnavailable)):
        return 409
    return 404
```

- [ ] **Passo 5: criar `backend/app/api/routes_triggers.py`**

```python
"""
Rotas de controle de uma vinheria: faixa ideal (RF06) e alertas
disparados à mão pelo painel (RF09).
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_control
from app.models.schemas import Limits
from app.models.schemas_fleet import CommandRequest, CommandResult, LimitsUpdate
from app.services.device_control import DeviceControl

router = APIRouter(prefix="/api/devices", tags=["faixa e comandos"])


@router.get("/{device_id}/triggers", response_model=Limits)
def read_triggers(device_id: str, control: DeviceControl = Depends(get_control)) -> Limits:
    """Faixa ideal atual da vinheria."""
    return control.get_limits(device_id)


@router.put("/{device_id}/triggers", response_model=LimitsUpdate)
async def write_triggers(device_id: str, limits: Limits,
                         control: DeviceControl = Depends(get_control)) -> LimitsUpdate:
    """Salva a faixa (Orion e SQLite) e manda ao ESP32 na hora; offline fica pendente."""
    return await control.update_limits(device_id, limits)


@router.post("/{device_id}/commands", response_model=CommandResult, status_code=202)
async def post_command(device_id: str, body: CommandRequest,
                       control: DeviceControl = Depends(get_control)) -> CommandResult:
    """Dispara ou desliga um alerta à mão; offline ou configurando responde 409."""
    await control.send_command(device_id, body.command)
    return CommandResult(device_id=device_id, command=body.command)
```

- [ ] **Passo 6: criar `backend/app/api/routes_alerts.py`**

```python
"""Rota do histórico de alertas (RF10), geral, de uma vinheria ou da EC2 (device_id=fiware)."""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_alert_log
from app.models.schemas_fleet import Alert
from app.services.alert_log import AlertLog

router = APIRouter(prefix="/api/alerts", tags=["alertas"])


@router.get("", response_model=list[Alert])
def list_alerts(device_id: str | None = None,
                limit: int = Query(default=100, ge=1, le=500),
                alerts: AlertLog = Depends(get_alert_log)) -> list[Alert]:
    """Alertas do mais novo para o mais velho, com início, fim e duração."""
    return alerts.list(device_id=device_id, limit=limit)
```

- [ ] **Passo 7: criar `backend/app/api/routes_fleet.py`**

```python
"""Rota da visão geral da frota (RF12): estado da EC2 e de todas as vinherias."""
from fastapi import APIRouter, Depends

from app.api.deps import get_fleet, get_registry
from app.models.schemas_fleet import FleetReport
from app.services.device_registry import DeviceRegistry
from app.services.fleet_state import FleetState

router = APIRouter(prefix="/api/fleet", tags=["frota"])


@router.get("", response_model=FleetReport)
async def read_fleet(fleet: FleetState = Depends(get_fleet),
                     registry: DeviceRegistry = Depends(get_registry)) -> FleetReport:
    """Retrato do último ciclo do poller, só das vinherias ainda cadastradas.

    Uma vinheria recém-cadastrada aparece no ciclo seguinte (até poll_seconds).
    """
    return fleet.report([device.device_id for device in registry.list()])
```

- [ ] **Passo 8: montagem em `backend/app/main.py`**

Trocar o import de rotas por:

```python
from app.api import (
    routes_alerts,
    routes_config,
    routes_data,
    routes_devices,
    routes_fleet,
    routes_triggers,
)
```

Acrescentar aos imports de services:

```python
from app.services.alert_log import AlertLog
from app.services.device_control import DeviceControl
from app.services.fleet_state import FleetState
from app.services.trigger_engine import TriggerEngine
```

Em `create_app`, logo depois de `app.state.readings = ReadingsService(registry, fiware, limits)`, acrescentar:

```python
    alerts = AlertLog(conn)
    fleet = FleetState()
    engine = TriggerEngine(registry, limits, alerts, fiware, store, fleet)
    app.state.alerts = alerts
    app.state.fleet = fleet
    app.state.engine = engine
    app.state.control = DeviceControl(registry, limits, fiware, fleet, engine)
```

E depois de `app.include_router(routes_data.router)`:

```python
    app.include_router(routes_triggers.router)
    app.include_router(routes_alerts.router)
    app.include_router(routes_fleet.router)
```

- [ ] **Passo 9: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_routes_control.py -v` → 12 passed.
Run: `.venv/Scripts/python -m pytest -q` → **278 passed**.

- [ ] **Passo 10: commit**

```bash
git add app/api/routes_triggers.py app/api/routes_alerts.py app/api/routes_fleet.py app/api/deps.py app/api/errors.py app/main.py tests/test_routes_control.py
git commit -m "feat: expoe rotas de faixa, comandos manuais, alertas e frota"
```

---

## Subtarefa 4.14 — Lifespan: poller e backup em fundo, restauração na partida (R13, R2.3, R2.4)

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_lifespan.py`

**Interfaces:**
- Consumes: `BackupService`, `restore_if_missing`, `list_backups`, `TriggerEngine.run`, `Settings.run_background/backup_*`.
- Produces: `app.state.backup`; lifespan com tarefas de fundo.

- [ ] **Passo 1: escrever os testes que falham**

`backend/tests/test_lifespan.py`:

```python
"""Testes da montagem do app: tarefas de fundo, backup final e restauração (spec R13)."""
import asyncio

from fastapi.testclient import TestClient

from app.core.backup import list_backups
from app.core.config import Settings
from app.core.db import connect
from app.main import create_app


class MotorFalso:
    """Substitui o TriggerEngine: registra se o laço começou e se foi cancelado."""

    def __init__(self):
        self.iniciado = False
        self.cancelado = False

    async def run(self):
        self.iniciado = True
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelado = True
            raise

    def mark_limits_pending(self, device_id):
        pass


def test_lifespan_inicia_e_para_o_fundo_e_faz_backup_na_saida(tmp_path):
    pasta = tmp_path / "bk"
    app = create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "v.db"),
                              backup_dir=str(pasta), run_background=True))
    motor = MotorFalso()
    app.state.engine = motor
    with TestClient(app) as cliente:
        cliente.get("/api/config")  # dá voltas no loop para as tarefas começarem
    assert motor.iniciado
    assert motor.cancelado
    assert len(list_backups(pasta)) == 1  # o backup final do desligamento


def test_sem_run_background_nao_inicia_poller(tmp_path):
    app = create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "v.db")))
    motor = MotorFalso()
    app.state.engine = motor
    with TestClient(app) as cliente:
        cliente.get("/api/config")
    assert not motor.iniciado


def test_create_app_restaura_banco_ausente(tmp_path):
    pasta = tmp_path / "bk"
    pasta.mkdir()
    origem = connect(str(pasta / "vinheria-20261008-120000.db"))
    with origem:
        origem.execute(
            "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
            "VALUES ('vinheria001', 'urn:ngsi-ld:Vinheria:001', 'Vinheria Paulista', "
            "'São Paulo', '2026-10-07T21:00:00+00:00')")
    origem.close()
    app = create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "v.db"),
                              backup_dir=str(pasta)))
    assert [d.device_id for d in app.state.registry.list()] == ["vinheria001"]
    app.state.conn.close()
```

- [ ] **Passo 2: rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_lifespan.py -v`
Expected: FAIL — `assert motor.iniciado` (o lifespan ainda não sobe tarefas) e `[] == ['vinheria001']` (sem restauração).

- [ ] **Passo 3: completar `backend/app/main.py`**

Trocar a docstring do módulo por:

```python
"""
Ponto de entrada do backend FastAPI (Smart Solutions).

create_app() monta a aplicação: lê a configuração, restaura o banco de um
backup se o arquivo sumiu, abre o SQLite, cria o cliente FIWARE e os
services (cadastro, leituras, alertas, frota, motor, controle e backup) e
registra CORS, tradução de erros e rotas. O lifespan sobe o poller e o
backup em fundo quando Settings.run_background está ligado. Os testes
chamam create_app() com Settings próprios; o uvicorn usa o objeto `app` do
fim do arquivo (uvicorn app.main:app --reload, rodando de dentro de
backend/).
"""
```

Trocar `from contextlib import asynccontextmanager` por:

```python
import asyncio
import logging
from contextlib import asynccontextmanager, suppress
```

Acrescentar aos imports de `app.core`:

```python
from app.core.backup import BackupService, restore_if_missing
```

Logo depois dos imports, acrescentar:

```python
log = logging.getLogger(__name__)
```

Trocar a função `lifespan` inteira por:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida do app.

    Na partida, com run_background ligado, sobe o poller (TriggerEngine) e
    o backup periódico. No desligamento, cancela as tarefas, grava o backup
    final e fecha o pool HTTP e o SQLite.
    """
    tarefas = []
    if app.state.settings.run_background:
        tarefas.append(asyncio.create_task(app.state.engine.run()))
        if app.state.backup.enabled:
            tarefas.append(asyncio.create_task(app.state.backup.run()))
    yield
    for tarefa in tarefas:
        tarefa.cancel()
    for tarefa in tarefas:
        with suppress(asyncio.CancelledError):
            await tarefa
    try:
        app.state.backup.backup_now()
    except OSError:
        log.exception("falha ao gravar o backup final do banco")
    await app.state.fiware.aclose()
    app.state.conn.close()
```

Em `create_app`, trocar a linha `conn = connect(settings.database_path)` por:

```python
    # Banco apagado por engano ou máquina nova: volta do backup mais recente
    restore_if_missing(settings.database_path, settings.backup_dir)
    conn = connect(settings.database_path)
```

E, logo depois de `app.state.control = DeviceControl(...)`, acrescentar:

```python
    app.state.backup = BackupService(conn, settings.backup_dir, settings.backup_keep,
                                     settings.backup_minutes)
```

- [ ] **Passo 4: rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_lifespan.py -v` → 3 passed.
Run: `.venv/Scripts/python -m pytest -q` → **281 passed**.

- [ ] **Passo 5: conferir as rotas montadas**

Run (bash): `.venv/Scripts/python -c "from app.main import create_app; from app.core.config import Settings; print(sorted(r.path for r in create_app(Settings(database_path=':memory:')).routes if r.path.startswith('/api')))"`
Expected: a lista inclui `/api/alerts`, `/api/devices/{device_id}/commands`, `/api/devices/{device_id}/triggers` e `/api/fleet`.

- [ ] **Passo 6: commit**

```bash
git add app/main.py tests/test_lifespan.py
git commit -m "feat: sobe poller e backup em fundo e restaura banco ausente na partida"
```

---

## Subtarefa 4.15 — Firmware: ESP32 sem faixa até ser configurado (R14)

**Files:**
- Create: `firmware/limites.h`
- Modify: `firmware/vinheria_full.ino`

**Interfaces:**
- Consumes: comando `set_limits` com valor `"tmin,tmax,hmin,hmax,lmin,lmax"` (backend da 4.12/4.10).
- Produces: telemetria `t|<t>|h|<h>|l|<l>|c|<0|1>`; `blink_*` recusado antes de configurar.

> Sem teste automatizado: cada passo é verificado no Wokwi da `vinheria001`. O backend fica **parado** nesta subtarefa; os comandos vão direto ao Orion por `curl` (bash), com o IP elástico `3.215.3.216`. Antes de começar, o usuário abre o Wokwi da 001 e confirma que a EC2 está ligada. No Wokwi, adicionar o arquivo `limites.h` pelo botão "+" ao lado das abas e colar o conteúdo do Passo 1.

Comando de apoio (usado nos passos), em bash:

```bash
ORION=http://3.215.3.216:1026
cmd() {  # uso: cmd <comando> [valor]
  curl -s -o /dev/null -w "%{http_code}\n" -X PATCH \
    "$ORION/v2/entities/urn:ngsi-ld:Vinheria:001/attrs" \
    -H "fiware-service: smart" -H "fiware-servicepath: /" -H "Content-Type: application/json" \
    -d "{\"$1\":{\"type\":\"command\",\"value\":\"${2:-}\"}}"
}
```

- [ ] **Passo 1: criar `firmware/limites.h`**

```cpp
/*
 * Faixa ideal da vinheria recebida do backend pelo comando set_limits.
 *
 * Formato do valor: "tmin,tmax,hmin,hmax,lmin,lmax", separado por vírgula (o
 * Orion rejeita ; em valores de atributo), com decimais opcionais
 * (ex.: "12.5,18,50,70,0,30"). Funções puras: não usam LCD, MQTT nem as
 * variáveis globais do .ino.
 */
#ifndef LIMITES_H
#define LIMITES_H

#include <Arduino.h>

// Faixa ideal dos três atributos (mínimo e máximo de cada)
struct Faixa {
  float tempMin, tempMax;
  float humMin, humMax;
  float luxMin, luxMax;
};

// Converte texto em número aceitando só sinal opcional, dígitos e no
// máximo um ponto decimal. Rejeita vazio, letras e "1.2.3" (o toFloat()
// da String aceitaria lixo e devolveria 0).
bool parseDecimal(String s, float &out) {
  s.trim();
  if (s.length() == 0) return false;
  int i = (s[0] == '-') ? 1 : 0;
  bool temDigito = false;
  bool temPonto = false;
  for (; i < (int)s.length(); i++) {
    if (isDigit(s[i])) {
      temDigito = true;
    } else if (s[i] == '.' && !temPonto) {
      temPonto = true;
    } else {
      return false;
    }
  }
  if (!temDigito) return false;
  out = s.toFloat();
  return true;
}

// Lê os 6 valores na ordem canônica. Só devolve true com exatamente 6
// números e mínimo < máximo em cada par; caso contrário não altera
// `faixa` (validação atômica: ou aplica tudo, ou nada).
bool parseFaixa(String args, Faixa &faixa) {
  float v[6];
  int inicio = 0;
  for (int i = 0; i < 6; i++) {
    int fim = args.indexOf(',', inicio);
    if (i < 5 && fim < 0) return false;   // faltam campos
    if (i == 5 && fim >= 0) return false; // sobrou campo (7º valor)
    String campo = (fim >= 0) ? args.substring(inicio, fim) : args.substring(inicio);
    if (!parseDecimal(campo, v[i])) return false;
    inicio = fim + 1;
  }
  if (v[0] >= v[1] || v[2] >= v[3] || v[4] >= v[5]) return false;
  faixa = {v[0], v[1], v[2], v[3], v[4], v[5]};
  return true;
}

// Imprime um limite no LCD sem casas quando é inteiro (12) e com uma casa
// quando não é (12.5), para caber nas 16 colunas.
void imprimirLimite(Print &saida, float valor) {
  if (valor == (int)valor) {
    saida.print((int)valor);
  } else {
    saida.print(valor, 1);
  }
}

#endif
```

Resultado: arquivo criado no repositório e no Wokwi. O sketch ainda compila igual (ninguém o inclui). Commit:

```bash
git add firmware/limites.h
git commit -m "feat: adiciona parse da faixa do set_limits com virgula e decimais"
```

- [ ] **Passo 2: trocar a faixa fixa pelo estado "não configurado"**

Em `firmware/vinheria_full.ino`:

1. Depois de `#include "boot_animacao.h"`, acrescentar `#include "limites.h"`.
2. Trocar o bloco inteiro de "Limites de alerta configuráveis pelo backend" (as linhas do comentário e os três `int lim...`) por:

```cpp
// --- Faixa ideal recebida do backend (comando set_limits) ---
// O ESP32 nasce SEM faixa: até o backend mandar o set_limits, o LCD mostra
// "Configure o dispositivo" e os comandos de alerta são recusados, para
// nenhum alerta disparar com parâmetros que não foram cadastrados. A faixa
// é só informativa no LCD (quem decide o alerta é o backend). `configurado`
// vai na telemetria (c|0 ou c|1): é por ele que o backend percebe que o
// ESP32 reiniciou e reenvia a faixa na hora.
Faixa faixa;
bool configurado = false;
```

3. Trocar o comentário do bloco das flags (`alert_off vindo do backend só é mandado quando nenhum atributo mais está em alerta...`) por: `// alert_off limpa as três de uma vez; quando uma anomalia normaliza e outra continua, o backend manda alert_off e em seguida o blink da que restou.`
4. Nas telas, trocar os `lcd.print(limXxx)` por `imprimirLimite(lcd, faixa.xxx)`:
   - `telaTemp`: `imprimirLimite(lcd, faixa.tempMin);` e `imprimirLimite(lcd, faixa.tempMax);`
   - `telaUmidade`: `imprimirLimite(lcd, faixa.humMin);` e `imprimirLimite(lcd, faixa.humMax);`
   - `telaLuz`: `imprimirLimite(lcd, faixa.luxMax);`
5. Apagar as funções `parseInteiro` e `parseLimites` (substituídas por `limites.h`).
6. No `mqttCallback`, trocar o ramo `else if (cmd == "set_limits") { ... }` inteiro por:

```cpp
  } else if (cmd == "set_limits") {
    String args = (posPipe >= 0) ? msg.substring(posPipe + 1) : "";
    Faixa nova;
    if (!parseFaixa(args, nova)) {
      Serial.print("set_limits invalido, comando ignorado: ");
      Serial.println(args);
      publicarAck(cmd, "erro");
      return;
    }
    bool primeiraVez = !configurado;
    faixa = nova;
    configurado = true;
    if (primeiraVez) {
      // Sai da tela de espera: mostra a confirmação e o carrossel segue depois
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Configurado!");
      lcd.setCursor(0, 1);
      lcd.print(ID_DEVICE);
      telaAtual = 0;
      ultimaTela = millis();
    }
```

7. Ainda no `mqttCallback`, trocar o bloco final do ack ok (`char ack[50]; snprintf(...); MQTT.publish(...)`) por `publicarAck(cmd, "ok");` e, logo **antes** do `mqttCallback`, acrescentar:

```cpp
// Responde o comando no tópico cmdexe: "<device_id>@<comando>|<ok|erro>".
void publicarAck(const String &cmd, const char *resultado) {
  char ack[60];
  snprintf(ack, sizeof(ack), "%s@%s|%s", ID_DEVICE, cmd.c_str(), resultado);
  MQTT.publish(topicCmdExe, ack);
}
```

8. Mover as declarações `const unsigned long T_TELA = 3000;` e `unsigned long ultimaTela = 0;` (hoje antes do `loop()`) para logo depois de `int telaAtual = 0;`, porque o `mqttCallback` agora usa `ultimaTela`. Apagar o comentário "(passo 8 vai expandir para 5 telas)".

Resultado esperado no Wokwi: compila. Ainda não há tela de espera (próximo passo), e `cmd set_limits "12.5,18,50,70,0,30"` → `204`, o Serial não mostra "invalido" e a tela de temperatura passa a mostrar `Ideal 12.5-18C`. Commit:

```bash
git add firmware/vinheria_full.ino
git commit -m "feat: firmware nasce sem faixa e aceita set_limits do contrato"
```

- [ ] **Passo 3: recusar alertas antes de configurar e publicar `c`**

1. No `mqttCallback`, logo depois de extrair `cmd` (antes do `if (cmd == "blink_temp")`), acrescentar:

```cpp
  // Sem faixa cadastrada, nenhum alerta toca: evita disparo ao ligar com
  // parâmetros que não vieram do backend. alert_off é sempre aceito.
  bool ehBlink = (cmd == "blink_temp" || cmd == "blink_hum" || cmd == "blink_lux");
  if (ehBlink && !configurado) {
    Serial.println("Alerta recusado: dispositivo ainda nao configurado (aguardando set_limits)");
    publicarAck(cmd, "erro");
    return;
  }
```

2. Em `publicarTelemetria`, trocar a montagem do payload por:

```cpp
  char payload[80];
  snprintf(payload, sizeof(payload), "t|%.1f|h|%.1f|l|%d|c|%d",
           temperatura, umidade, luminosidade, configurado ? 1 : 0);
```

e atualizar o comentário da função para `// Lê DHT+LDR e publica "t|<temp>|h|<umid>|l|<lux>|c|<0 ou 1>" em topicAttrs.`

Verificação no Wokwi: reiniciar a simulação.
- O Serial mostra payloads terminando em `|c|0`.
- `cmd blink_temp` → `204`; o Serial mostra "Alerta recusado..." e **nada pisca nem apita**.
- `cmd set_limits "12,18,50,70,0,30"` → os payloads passam a terminar em `|c|1`.
- `cmd blink_temp` → agora pisca a 500 ms com 2 bipes; `cmd alert_off` → para.

Commit:

```bash
git add firmware/vinheria_full.ino
git commit -m "feat: firmware recusa alertas antes da faixa e publica o estado configurado"
```

- [ ] **Passo 4: tela "Configure o dispositivo"**

1. Logo depois de `telaStatus()`, acrescentar:

```cpp
// Tela de espera enquanto o backend não mandou a faixa. Os pontos animados
// mostram que o dispositivo está vivo; sem MQTT, avisa que está conectando.
int pontosCarregando = 0;

void telaConfigurar() {
  lcd.clear();
  lcd.setCursor(0, 0);
  if (MQTT.connected()) {
    lcd.print("Configure o");
    lcd.setCursor(0, 1);
    lcd.print("dispositivo");
  } else {
    lcd.print("Conectando");
    lcd.setCursor(0, 1);
    lcd.print(ID_DEVICE);
  }
  for (int i = 0; i < pontosCarregando; i++) {
    lcd.print(".");
  }
  pontosCarregando = (pontosCarregando + 1) % 4;
}
```

2. Junto de `T_TELA`, acrescentar `const unsigned long T_CARREGANDO = 500; // ritmo dos pontos da tela de espera`.
3. No `loop()`, trocar o bloco `if (agora - ultimaTela >= T_TELA) { ... }` por:

```cpp
  if (!configurado) {
    if (agora - ultimaTela >= T_CARREGANDO) {
      ultimaTela = agora;
      telaConfigurar();
    }
  } else if (agora - ultimaTela >= T_TELA) {
    ultimaTela = agora;
    telaLCD();
  }
```

Verificação no Wokwi: reiniciar a simulação.
- Depois da animação de boot e de "Inicializando...", o LCD mostra "Configure o" / "dispositivo" com 0 a 3 pontos girando, e **não sai disso** sozinho.
- `cmd set_limits "12.5,18,50,70,0,30"` → "Configurado!" / `vinheria001` por ~3 s, depois o carrossel; a tela de temperatura mostra `Ideal 12.5-18C`.
- `cmd set_limits "18,12,50,70,0,30"` (invertido) → Serial "set_limits invalido"; a faixa na tela continua 12.5–18.

Commit:

```bash
git add firmware/vinheria_full.ino
git commit -m "feat: firmware mostra configure o dispositivo ate receber a faixa"
```

- [ ] **Passo 5: conferir o cabeçalho e o tamanho**

Atualizar o cabeçalho do `.ino` acrescentando ao parágrafo: "Nasce sem faixa ideal: mostra \"Configure o dispositivo\" e recusa alertas até o backend mandar o set_limits." Rodar `grep -n "limTemp\|parseInteiro\|parseLimites" firmware/vinheria_full.ino` → nenhum resultado. Commit:

```bash
git add firmware/vinheria_full.ino
git commit -m "docs: descreve no firmware a espera pela faixa do backend"
```

---

## Subtarefa 4.16 — Recadastro da 001 e da 002 e verificação real na EC2 (spec §6)

**Pré-requisitos (o usuário confirma antes de começar):**
- EC2 ligada e containers de pé.
- Wokwi da 001 e da 002 com o firmware da 4.15 (incluindo `limites.h`), sensores **dentro da faixa padrão**: temperatura ~15 °C, umidade ~60 %, luminosidade ≤ 30 %.
- Backend parado no início.

Todos os comandos rodam em **bash** (Git Bash), de dentro de `backend/`. Para ler JSON, use `| .venv/Scripts/python -m json.tool`. Ao fim de **cada** passo, informe a saída real; se não bater com o esperado, pare e reporte.

- [ ] **Passo 1: subir o backend**

Run (em segundo plano): `.venv/Scripts/python -m uvicorn app.main:app --port 8000`
Expected: partida sem erro.

- [ ] **Passo 2: recadastrar a 001 e a 002 (o IoT Agent precisa conhecer o atributo `c`, D14)**

> **Atenção:** remove e recria as duas vinherias no FIWARE e no SQLite. A faixa volta ao padrão e os alertas antigos (se houver) ficam no histórico. O histórico do STH não é afetado.

```bash
for par in "001|Vinheria Paulista|São Paulo" "002|Vinheria Mineira|Minas Gerais"; do
  IFS="|" read -r n nome cidade <<< "$par"
  curl -s -o /dev/null -w "DELETE $n: %{http_code}\n" -X DELETE "localhost:8000/api/devices/vinheria$n"
  curl -s -o /dev/null -w "POST $n: %{http_code}\n" -X POST localhost:8000/api/devices \
    -H "Content-Type: application/json" \
    -d "{\"device_id\":\"vinheria$n\",\"name\":\"$nome\",\"city\":\"$cidade\"}"
done
curl -s -H "fiware-service: smart" -H "fiware-servicepath: /" http://3.215.3.216:4041/iot/devices/vinheria001 | .venv/Scripts/python -m json.tool
```

Expected: `DELETE` 204 e `POST` 201 para as duas; o device lista o atributo `{"object_id": "c", "name": "configured", ...}`.

- [ ] **Passo 3: configuração na partida**

Ação: reiniciar a simulação dos dois Wokwi.
Expected: cada LCD mostra "Configure o dispositivo" e, em até ~5 s depois da primeira leitura, "Configurado!" e o carrossel com `Ideal 12-18C`. Nenhum alerta toca. Depois:
`curl -s localhost:8000/api/fleet | .venv/Scripts/python -m json.tool` → `fiware_online: true`, 001 e 002 com `status: "ok"`, `seconds_since` abaixo de 10.

- [ ] **Passo 4: alerta por faixa (só a 002), com a faixa entregue na hora**

```bash
curl -s -X PUT localhost:8000/api/devices/vinheria002/triggers \
  -H "Content-Type: application/json" \
  -d '{"temperature":{"min":5,"max":10},"humidity":{"min":50,"max":70},"luminosity":{"min":0,"max":30}}'
```

Expected: 200 com `"device_sync": "enviado"`; o LCD da 002 passa a mostrar `Ideal 5-10C` em segundos; em até ~5 s o Wokwi da 002 pisca a 500 ms com 2 bipes curtos; o da 001 não reage. `GET /api/fleet` → 002 `alerta`, 001 `ok`; `GET "/api/alerts?device_id=vinheria002"` → alerta `temperature` com `closed_at: null`.

- [ ] **Passo 5: volta à faixa**

Run: o mesmo `PUT` com `"temperature":{"min":12,"max":18}`.
Expected: o Wokwi da 002 para em até ~5 s; o alerta aparece com `closed_at` e `duration_seconds`.

- [ ] **Passo 6: comando manual não é desfeito**

Run: `curl -s -X POST localhost:8000/api/devices/vinheria001/commands -H "Content-Type: application/json" -d '{"command":"blink_hum"}'`
Expected: 202. O Wokwi da 001 dá o bipe longo e **continua** por pelo menos 15 s. Depois `{"command":"alert_off"}` → para.

- [ ] **Passo 7: reinício do ESP32 com alerta aberto**

Ação: baixar o máximo de temperatura da 001 (`PUT` como no Passo 4, para a 001) e esperar o alerta tocar. Reiniciar a simulação da 001.
Expected: o LCD mostra "Configure o dispositivo", recebe a faixa (`Ideal 5-10C`) e, logo depois, volta a apitar no padrão de temperatura; `GET /api/alerts?device_id=vinheria001` continua com **um** alerta aberto. Voltar a faixa da 001 ao padrão.

- [ ] **Passo 8: vinheria offline e volta**

Ação: parar a simulação da 002.
Expected: em até ~35 s, `GET /api/fleet` mostra a 002 `offline` com `offline_reason: "sem_leitura"` e `score: null`; há alerta `offline` aberto; `POST .../vinheria002/commands` com `blink_temp` responde **409**.
Ação: religar a 002 (temperatura ~15 °C).
Expected: "Configure o dispositivo" → carrossel; a 002 volta a `ok` e o alerta `offline` fecha.

- [ ] **Passo 9: EC2 fora (simulada)**

```bash
curl -s -X PUT localhost:8000/api/config -H "Content-Type: application/json" -d '{"ec2_ip":"10.255.255.1"}'
```

Expected: em até ~45 s, `GET /api/fleet` mostra `fiware_online: false`, `fiware_offline_since` preenchido e as duas vinherias `offline` com `offline_reason: "fiware"`; `GET "/api/alerts?device_id=fiware"` mostra **um** alerta aberto; nenhum alerta `offline` novo por vinheria.
Run: o mesmo `PUT` com o IP verdadeiro (`3.215.3.216`).
Expected: em até ~10 s, `fiware_online: true`, vinherias `ok`, alerta `fiware` fechado com duração, e nenhum alerta `offline` por vinheria aberto.

- [ ] **Passo 10: backup no desligamento**

Ação: parar o backend com Ctrl+C.
Run: `ls -la ~/SmartSolutions/backups` (ou a pasta do `BACKUP_DIR`).
Expected: um `vinheria-AAAAMMDD-HHMMSS.db` com a hora do desligamento.

- [ ] **Passo 11: restauração automática**

> **Atenção:** mexe no banco real. Siga a ordem exata e não apague nada.

1. Com o backend parado: `cp vinheria.db ~/vinheria-copia-seguranca.db`.
2. `mv vinheria.db vinheria.db.teste`.
3. Subir o backend (Passo 1). Expected: o log mostra `banco ... não existia; restaurado do backup ...`.
4. `curl -s localhost:8000/api/devices | .venv/Scripts/python -m json.tool` → 001 (Vinheria Paulista, São Paulo) e 002 (Vinheria Mineira, Minas Gerais).
5. Parar o backend. **Não apague** `vinheria.db.teste` nem a cópia de segurança; pergunte ao usuário o que fazer com elas.

- [ ] **Passo 12: conferência do Git**

Run (da raiz): `git status --short`
Expected: nada de `.env`, `*.db`, `vinheria.db.teste` ou backups.

Sem commit nesta subtarefa. Relate o resultado de cada passo ao usuário.

---

## Subtarefa 4.17 — Fechamento da documentação

**Files:**
- Modify: `PLANO-CP5-VINHERIA.md`, `docs/specs/task-4-triggers-poller-alertas/plan.md`

- [ ] **Passo 1: marcar a Task 4 como feita no `PLANO-CP5-VINHERIA.md`**

No topo da seção "Task 4", acima do bloco "Planejada em 08/10/2026", acrescentar `> **FEITA em <data>** — executada pelo plano docs/specs/task-4-triggers-poller-alertas/plan.md (commits <primeiro>..<último>). <N> testes passando sem rede. Verificação real: <resumo dos passos 3 a 11 da 4.16, com os números observados>.` Marcar com `[x]` os checkboxes dos passos da Task 4 e registrar qualquer desvio da execução. Na seção "Task 4B", acrescentar `> **FEITA dentro da Task 4 (subtarefa 4.15).**`

- [ ] **Passo 2: registrar o estado no topo deste plano**

Logo abaixo da linha **Spec:**, acrescentar `> **Estado em <data>:** feitas as subtarefas 4.1 a 4.17 ...` com os desvios, no mesmo formato do plano da Task 3.

- [ ] **Passo 3: commit**

```bash
git add PLANO-CP5-VINHERIA.md docs/specs/task-4-triggers-poller-alertas/plan.md
git commit -m "docs: fecha task 4 com motor de alertas, frota, configuracao do ESP32 e backup"
```
