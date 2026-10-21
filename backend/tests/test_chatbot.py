"""Testes do chatbot: resumo da frota e loop de function calling (spec R6)."""
from datetime import timezone

from app.models.schemas_fleet import ActiveAlert, FleetReport
from app.services.chatbot import resumo_frota
from tests.fakes import status_vinheria


def _status(device_id, status, name, alertas=()):
    return status_vinheria(device_id, status).model_copy(update={
        "name": name, "active_alerts": [ActiveAlert(attr=a, since="2026-10-08T11:00:00+00:00")
                                        for a in alertas]})


def test_resumo_tudo_normal():
    report = FleetReport(fiware_online=True, vinherias=[
        _status("vinheria001", "ok", "Vinheria Paulista"),
        _status("vinheria002", "ok", "Vinheria Mineira")])
    assert resumo_frota(report) == "Situação agora: FIWARE ok; 2 vinherias, todas normais."


def test_resumo_com_alerta_offline_e_configurando():
    report = FleetReport(fiware_online=True, vinherias=[
        _status("vinheria001", "ok", "Vinheria Paulista"),
        _status("vinheria002", "alerta", "Vinheria Mineira", ["temperature", "humidity"]),
        _status("vinheria003", "offline", "Vinheria Sul"),
        _status("vinheria004", "configurando", "Vinheria Norte")])
    assert resumo_frota(report) == (
        "Situação agora: FIWARE ok; 4 vinherias; "
        "vinheria002 (Vinheria Mineira) em alerta de temperatura, umidade; "
        "vinheria003 (Vinheria Sul) offline; "
        "vinheria004 (Vinheria Norte) aguardando a faixa (configurando).")


def test_resumo_fiware_fora():
    report = FleetReport(fiware_online=False, fiware_offline_since="2026-10-08T11:30:00+00:00",
                         vinherias=[_status("vinheria001", "offline", "Vinheria Paulista")])
    assert resumo_frota(report, fuso=timezone.utc) == (
        "Situação agora: FIWARE fora do ar desde 08/10 11:30; "
        "os dados das vinherias podem estar desatualizados.")


def test_resumo_sem_vinherias():
    report = FleetReport(fiware_online=True, vinherias=[])
    assert resumo_frota(report) == "Situação agora: FIWARE ok; nenhuma vinheria cadastrada."
