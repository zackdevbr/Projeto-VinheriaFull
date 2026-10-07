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
