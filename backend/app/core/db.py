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
import os
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
        Grava num arquivo temporário e só renomeia no fim: se a cópia falhar,
        nada sobra na pasta (um arquivo pela metade viraria o "backup mais
        novo" e seria restaurado depois).
        """
        temporario = destino + ".tmp"
        with self._lock:
            alvo = sqlite3.connect(temporario)
            try:
                self._conn.backup(alvo)
                alvo.close()
                os.replace(temporario, destino)
            except BaseException:
                alvo.close()
                if os.path.exists(temporario):
                    os.remove(temporario)
                raise

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
