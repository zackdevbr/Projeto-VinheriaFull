# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes das rotas de faixa, comandos, alertas e frota (spec R12).

Faixa e comandos usam um DeviceControl falso (o contrato HTTP é o que
importa aqui); alertas e frota usam as peças reais do app, com o cadastro
falso.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.schemas import Device
from app.models.schemas_fleet import LimitsUpdate
from app.services.fiware_errors import FiwareUnavailable
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import DeviceNotFound, DeviceUnavailable
from tests.fakes import status_vinheria

DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria Paulista", city="São Paulo",
                created_at="2026-10-07T21:00:00+00:00")
FAIXA = {"temperature": {"min": 10, "max": 16},
         "humidity": {"min": 55, "max": 75},
         "luminosity": {"min": 0, "max": 20}}


class ControlFalso:
    """Substitui o DeviceControl nos testes de rota."""

    def __init__(self):
        self.faixas = {}
        self.comandos = []
        self.erro = None

    def get_limits(self, device_id):
        if device_id != DEVICE.device_id:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        return DEFAULT_LIMITS

    async def update_limits(self, device_id, limits):
        if self.erro:
            raise self.erro
        self.faixas[device_id] = limits
        return LimitsUpdate(device_id=device_id, limits=limits, device_sync="enviado")

    async def send_command(self, device_id, command):
        if self.erro:
            raise self.erro
        self.comandos.append((device_id, command))


class RegistryFalso:
    """Só a listagem, usada pela rota da frota."""

    def list(self):
        return [DEVICE]


@pytest.fixture
def app(tmp_path):
    aplicacao = create_app(Settings(fiware_host="10.0.0.1",
                                    database_path=str(tmp_path / "rotas.db")))
    aplicacao.state.control = ControlFalso()
    aplicacao.state.registry = RegistryFalso()
    return aplicacao


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


def test_get_triggers_200(client):
    resposta = client.get("/api/devices/vinheria001/triggers")
    assert resposta.status_code == 200
    assert resposta.json() == DEFAULT_LIMITS.model_dump()


def test_get_triggers_404(client):
    resposta = client.get("/api/devices/vinheria009/triggers")
    assert resposta.status_code == 404
    assert resposta.json()["service"] == "registry"


def test_put_triggers_200(client, app):
    resposta = client.put("/api/devices/vinheria001/triggers", json=FAIXA)
    assert resposta.status_code == 200
    assert resposta.json() == {"device_id": "vinheria001", "limits": FAIXA,
                               "device_sync": "enviado"}
    assert app.state.control.faixas["vinheria001"].temperature.max == 16


def test_put_triggers_min_maior_que_max_422(client, app):
    invertida = {**FAIXA, "temperature": {"min": 18, "max": 12}}
    assert client.put("/api/devices/vinheria001/triggers", json=invertida).status_code == 422
    incompleta = {"temperature": FAIXA["temperature"], "humidity": FAIXA["humidity"]}
    assert client.put("/api/devices/vinheria001/triggers", json=incompleta).status_code == 422
    assert app.state.control.faixas == {}


def test_put_triggers_fiware_fora_503(client, app):
    app.state.control.erro = FiwareUnavailable("orion", "sem conexão")
    resposta = client.put("/api/devices/vinheria001/triggers", json=FAIXA)
    assert resposta.status_code == 503
    assert resposta.json()["service"] == "orion"


def test_post_command_202(client, app):
    resposta = client.post("/api/devices/vinheria001/commands", json={"command": "blink_hum"})
    assert resposta.status_code == 202
    assert resposta.json() == {"device_id": "vinheria001", "command": "blink_hum"}
    assert app.state.control.comandos == [("vinheria001", "blink_hum")]


def test_post_command_invalido_422(client, app):
    for comando in ("set_limits", "tocar_musica"):
        resposta = client.post("/api/devices/vinheria001/commands", json={"command": comando})
        assert resposta.status_code == 422
    assert app.state.control.comandos == []


def test_post_command_indisponivel_409(client, app):
    app.state.control.erro = DeviceUnavailable("vinheria001 está offline e não recebe comandos")
    resposta = client.post("/api/devices/vinheria001/commands", json={"command": "blink_temp"})
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "vinheria001 está offline e não recebe comandos",
                               "service": "registry"}


def test_get_alerts_lista_e_filtra(client, app):
    a1 = app.state.alerts.open("vinheria001", "temperature", 21.0, "2026-10-08T12:00:00+00:00")
    a2 = app.state.alerts.open("fiware", "offline", None, "2026-10-08T12:01:00+00:00")
    todos = client.get("/api/alerts").json()
    assert [a["id"] for a in todos] == [a2.id, a1.id]
    assert todos[0]["value"] is None
    so_001 = client.get("/api/alerts", params={"device_id": "vinheria001"}).json()
    assert [a["id"] for a in so_001] == [a1.id]
    so_ec2 = client.get("/api/alerts", params={"device_id": "fiware"}).json()
    assert [a["id"] for a in so_ec2] == [a2.id]
    assert len(client.get("/api/alerts", params={"limit": 1}).json()) == 1


def test_get_alerts_limit_invalido_422(client):
    assert client.get("/api/alerts", params={"limit": 0}).status_code == 422
    assert client.get("/api/alerts", params={"limit": 501}).status_code == 422


def test_get_fleet_so_vinherias_cadastradas(client, app):
    app.state.fleet.replace([status_vinheria("vinheria001", "ok"),
                             status_vinheria("vinheria099", "alerta")],
                            "2026-10-08T12:00:00+00:00")
    resposta = client.get("/api/fleet")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["fiware_online"] is True
    assert corpo["updated_at"] == "2026-10-08T12:00:00+00:00"
    assert [s["device_id"] for s in corpo["vinherias"]] == ["vinheria001"]
    assert corpo["vinherias"][0]["status"] == "ok"


def test_get_fleet_ec2_offline(client, app):
    app.state.fleet.replace([status_vinheria("vinheria001", "offline")],
                            "2026-10-08T12:00:40+00:00", fiware_online=False,
                            fiware_offline_since="2026-10-08T12:00:00+00:00")
    corpo = client.get("/api/fleet").json()
    assert corpo["fiware_online"] is False
    assert corpo["fiware_offline_since"] == "2026-10-08T12:00:00+00:00"
