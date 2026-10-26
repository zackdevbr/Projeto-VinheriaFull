# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes do retrato da frota em memória (spec R6.2)."""
from tests.fakes import status_vinheria


def test_fleet_comeca_vazio(fleet):
    assert fleet.snapshot() == []
    assert fleet.updated_at is None
    assert fleet.fiware_online is True


def test_fleet_snapshot_ordena_e_filtra(fleet):
    fleet.replace([status_vinheria("vinheria002"), status_vinheria("vinheria001")],
                  "2026-10-08T12:00:00+00:00")
    assert [s.device_id for s in fleet.snapshot()] == ["vinheria001", "vinheria002"]
    assert [s.device_id for s in fleet.snapshot(["vinheria002", "vinheria009"])] \
        == ["vinheria002"]
    assert fleet.updated_at == "2026-10-08T12:00:00+00:00"


def test_fleet_status_of(fleet):
    fleet.replace([status_vinheria("vinheria001", "offline")], "2026-10-08T12:00:00+00:00")
    assert fleet.status_of("vinheria001") == "offline"
    assert fleet.status_of("vinheria002") is None
    assert fleet.get("vinheria001").status == "offline"
    assert fleet.get("vinheria002") is None


def test_fleet_replace_troca_tudo(fleet):
    fleet.replace([status_vinheria("vinheria001")], "t1")
    fleet.replace([status_vinheria("vinheria002")], "t2")
    assert [s.device_id for s in fleet.snapshot()] == ["vinheria002"]


def test_fleet_report(fleet):
    fleet.replace([status_vinheria("vinheria001", "offline"), status_vinheria("vinheria099")],
                  "2026-10-08T12:00:40+00:00", fiware_online=False,
                  fiware_offline_since="2026-10-08T12:00:00+00:00")
    relatorio = fleet.report(["vinheria001"])
    assert relatorio.fiware_online is False
    assert relatorio.fiware_offline_since == "2026-10-08T12:00:00+00:00"
    assert relatorio.updated_at == "2026-10-08T12:00:40+00:00"
    assert [s.device_id for s in relatorio.vinherias] == ["vinheria001"]
