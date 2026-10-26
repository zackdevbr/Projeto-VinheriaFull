# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

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
