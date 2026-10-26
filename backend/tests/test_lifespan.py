# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

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


def test_erro_do_sqlite_no_backup_final_nao_impede_fechar_o_banco(tmp_path, monkeypatch):
    import sqlite3

    import pytest

    app = create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "v.db"),
                              backup_dir=str(tmp_path / "bk")))

    def falha():
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(app.state.backup, "backup_now", falha)
    with TestClient(app) as cliente:
        cliente.get("/api/config")
    with pytest.raises(sqlite3.ProgrammingError):  # conexão fechada
        app.state.conn.execute("SELECT 1")
