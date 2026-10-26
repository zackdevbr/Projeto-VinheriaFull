# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

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


async def test_run_sobrevive_a_erro_do_sqlite(conn, tmp_path, monkeypatch):
    """Banco travado ou disco cheio (sqlite3.Error) não pode matar o laço de backup."""
    esperas = []

    async def sleep_falso(segundos):
        esperas.append(segundos)
        if len(esperas) == 3:
            raise _Parar

    servico = BackupService(conn, str(tmp_path / "bk"), keep=20, minutes=10, sleep=sleep_falso)

    def falha():
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(servico, "backup_now", falha)
    with pytest.raises(_Parar):
        await servico.run()
    assert len(esperas) == 3


def test_backup_com_falha_nao_deixa_arquivo_na_pasta(conn, tmp_path):
    """Cópia que falha no meio não pode virar o 'backup mais novo' nem sobrar na pasta."""
    class ConexaoQuebrada:
        def backup(self, alvo):
            raise sqlite3.OperationalError("disk I/O error")

    real = conn._conn
    conn._conn = ConexaoQuebrada()
    pasta = tmp_path / "bk"
    servico = BackupService(conn, str(pasta), keep=20, minutes=10, clock=_relogio())
    try:
        with pytest.raises(sqlite3.Error):
            servico.backup_now()
    finally:
        conn._conn = real
    assert list_backups(pasta) == []
    assert list(pasta.iterdir()) == []
