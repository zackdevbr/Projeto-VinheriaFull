# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

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
