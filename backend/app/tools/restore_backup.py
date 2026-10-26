# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

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
