"""Testes das rotas de vinherias e de dados (spec R9).

As rotas são testadas com services falsos: aqui importa o contrato HTTP
(status, formato, tradução de erros). A lógica está coberta nos testes
de cada service.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.schemas import (
    AttrScores,
    CurrentReading,
    Device,
    DeviceDetail,
    HistoryPoint,
    ScoreReport,
)
from app.services.fiware_errors import FiwareUnavailable
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import (
    AmbiguousVinheria,
    DeviceAlreadyExists,
    DeviceNotFound,
    VinheriaNotFound,
)

DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria Paulista", city="São Paulo",
                created_at="2026-10-07T21:00:00+00:00")
INSTANTE = "2026-10-07T21:00:00.000Z"


class RegistryFalso:
    """Substitui o DeviceRegistry nos testes de rota."""

    def __init__(self):
        self.criados = []
        self.removidos = []
        self.erro = None

    async def create(self, data):
        if self.erro:
            raise self.erro
        self.criados.append(data)
        return DEVICE.model_copy(update={"device_id": data.device_id, "name": data.name,
                                         "city": data.city})

    def list(self):
        return [DEVICE]

    def detail(self, device_id):
        if device_id != DEVICE.device_id:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        return DeviceDetail(**DEVICE.model_dump(), limits=DEFAULT_LIMITS)

    async def delete(self, device_id):
        if device_id != DEVICE.device_id:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        self.removidos.append(device_id)


class ReadingsFalso:
    """Substitui o ReadingsService nos testes de rota."""

    def __init__(self):
        self.consultas = []

    async def current(self, device_id):
        return CurrentReading(device_id=device_id, temperature=14.5, humidity=60.0,
                              luminosity=10.0, time_instant=INSTANTE)

    async def history(self, device_id, query):
        self.consultas.append(query)
        return [HistoryPoint(ts=INSTANTE, value=14.5)]

    async def score(self, device_id):
        return ScoreReport(device_id=device_id, score=100.0, available=True, message=None,
                           attrs=AttrScores(temperature=100, humidity=100, luminosity=100),
                           limits=DEFAULT_LIMITS)


@pytest.fixture
def app(tmp_path):
    aplicacao = create_app(Settings(fiware_host="10.0.0.1",
                                    database_path=str(tmp_path / "rotas.db")))
    aplicacao.state.registry = RegistryFalso()
    aplicacao.state.readings = ReadingsFalso()
    return aplicacao


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


def test_post_device_201(client, app):
    resposta = client.post("/api/devices", json={
        "device_id": "vinheria003", "name": " Cave Campinas ", "city": "Campinas"})
    assert resposta.status_code == 201
    assert resposta.json()["device_id"] == "vinheria003"
    assert app.state.registry.criados[0].name == "Cave Campinas"


def test_post_device_invalido_422(client, app):
    assert client.post("/api/devices", json={
        "device_id": "vinheria1", "name": "X", "city": "Y"}).status_code == 422
    assert client.post("/api/devices", json={
        "device_id": "vinheria003", "name": "", "city": "Y"}).status_code == 422
    assert app.state.registry.criados == []


def test_post_device_fiware_fora_503(client, app):
    app.state.registry.erro = FiwareUnavailable("iota", "sem conexão")
    resposta = client.post("/api/devices", json={
        "device_id": "vinheria003", "name": "Cave", "city": "Campinas"})
    assert resposta.status_code == 503
    assert resposta.json() == {"detail": "sem conexão", "service": "iota"}


def test_get_devices_lista(client):
    resposta = client.get("/api/devices")
    assert resposta.status_code == 200
    assert [d["device_id"] for d in resposta.json()] == ["vinheria001"]


def test_get_device_detalhe(client):
    resposta = client.get("/api/devices/vinheria001")
    assert resposta.status_code == 200
    assert resposta.json()["limits"]["temperature"] == {"min": 12.0, "max": 18.0}
    inexistente = client.get("/api/devices/vinheria009")
    assert inexistente.status_code == 404
    assert inexistente.json()["service"] == "registry"


def test_delete_device_204(client, app):
    resposta = client.delete("/api/devices/vinheria001")
    assert resposta.status_code == 204
    assert app.state.registry.removidos == ["vinheria001"]
    assert client.delete("/api/devices/vinheria009").status_code == 404


def test_get_current(client):
    resposta = client.get("/api/devices/vinheria001/current")
    assert resposta.status_code == 200
    assert resposta.json()["temperature"] == 14.5
    assert resposta.json()["time_instant"] == INSTANTE


def test_get_history_last_n(client, app):
    resposta = client.get("/api/devices/vinheria001/history?attr=temperature&last_n=20")
    assert resposta.status_code == 200
    assert resposta.json() == [{"ts": INSTANTE, "value": 14.5}]
    consulta = app.state.readings.consultas[0]
    assert (consulta.attr, consulta.last_n) == ("temperature", 20)


def test_get_history_por_datas(client, app):
    resposta = client.get("/api/devices/vinheria001/history?attr=humidity"
                          "&date_from=2026-10-07T00:00:00&date_to=2026-10-07T23:59:59")
    assert resposta.status_code == 200
    consulta = app.state.readings.consultas[0]
    assert (consulta.date_from, consulta.date_to) == ("2026-10-07T00:00:00", "2026-10-07T23:59:59")


@pytest.mark.parametrize("query", [
    "attr=temperature",
    "attr=temperature&last_n=10&date_from=2026-10-07T00:00:00",
    "attr=pressure&last_n=10",
    "attr=temperature&last_n=0",
    "attr=temperature&last_n=501",
    "attr=temperature&date_from=ontem",
])
def test_get_history_janela_invalida_422(client, query):
    assert client.get(f"/api/devices/vinheria001/history?{query}").status_code == 422


def test_get_score(client):
    resposta = client.get("/api/devices/vinheria001/score")
    assert resposta.status_code == 200
    assert resposta.json()["available"] is True
    assert resposta.json()["score"] == 100.0


@pytest.mark.parametrize("erro, status", [
    (DeviceNotFound("não existe"), 404),
    (VinheriaNotFound("ninguém"), 404),
    (DeviceAlreadyExists("já existe"), 409),
    (AmbiguousVinheria("várias", []), 409),
])
def test_handler_traduz_erros_de_dominio(app, erro, status):
    async def rota_que_falha():
        raise erro

    app.add_api_route("/teste-erro-registry", rota_que_falha)
    with TestClient(app) as cliente:
        resposta = cliente.get("/teste-erro-registry")
    assert resposta.status_code == status
    assert resposta.json() == {"detail": erro.message, "service": "registry"}
