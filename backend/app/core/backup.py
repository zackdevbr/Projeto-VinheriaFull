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
import sqlite3
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
        """Laço em fundo: um backup a cada `minutes`. Falha de disco ou do SQLite não para o laço."""
        while True:
            await self._sleep(self._minutes * 60)
            try:
                self.backup_now()
            except (OSError, sqlite3.Error):
                log.exception("falha ao gravar o backup do banco; tento de novo no próximo intervalo")
