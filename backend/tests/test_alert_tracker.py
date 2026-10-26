# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

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
