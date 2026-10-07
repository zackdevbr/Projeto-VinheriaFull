"""Testes da API de configuração e da tradução de erros (spec R5.3 e R10)."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.schemas import HealthReport, ServiceHealth
from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)


@pytest.fixture
def app(tmp_path):
    """App de teste com IP fictício e banco temporário."""
    return create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "api.db")))


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


class FiwareFalso:
    """Substitui o FiwareClient nos testes de rota (sem rede)."""

    async def health(self):
        ok = ServiceHealth(ok=True, status_code=200, latency_ms=12)
        return HealthReport(ok=True, ec2_ip="10.0.0.1", orion=ok, iota=ok, sth=ok)

    async def aclose(self):
        pass


def test_get_config(client):
    resposta = client.get("/api/config")
    assert resposta.status_code == 200
    assert resposta.json() == {
        "ec2_ip": "10.0.0.1", "orion_port": 1026, "iota_port": 4041,
        "sth_port": 8666, "poll_seconds": 5, "offline_seconds": 30,
    }


def test_get_config_sem_ip(tmp_path):
    app = create_app(Settings(fiware_host="", database_path=str(tmp_path / "sem_ip.db")))
    with TestClient(app) as cliente:
        resposta = cliente.get("/api/config")
    assert resposta.status_code == 200
    assert resposta.json()["ec2_ip"] == ""


def test_put_config_atualiza_e_normaliza(client):
    resposta = client.put("/api/config",
                          json={"ec2_ip": " http://20.0.0.2:1026/ ", "poll_seconds": 10})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ec2_ip"] == "20.0.0.2"
    assert corpo["poll_seconds"] == 10
    assert corpo["orion_port"] == 1026
    assert client.get("/api/config").json()["ec2_ip"] == "20.0.0.2"


def test_put_config_invalido_devolve_422(client):
    assert client.put("/api/config", json={"ec2_ip": "   "}).status_code == 422
    assert client.put("/api/config", json={"orion_port": 70000}).status_code == 422
    assert client.get("/api/config").json()["ec2_ip"] == "10.0.0.1"


def test_get_health(app):
    app.state.fiware = FiwareFalso()
    with TestClient(app) as cliente:
        resposta = cliente.get("/api/config/health")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ok"] is True
    assert corpo["orion"]["latency_ms"] == 12


@pytest.mark.parametrize("erro, status", [
    (FiwareUnavailable("orion", "sem conexão"), 503),
    (FiwareNotFound("orion", "não existe", 404), 404),
    (FiwareConflict("iota", "já existe", 409), 409),
    (FiwareError("sth", "quebrou", 500), 502),
])
def test_handler_traduz_erros_fiware(app, erro, status):
    async def rota_que_falha():
        raise erro

    app.add_api_route("/teste-erro", rota_que_falha)
    with TestClient(app) as cliente:
        resposta = cliente.get("/teste-erro")
    assert resposta.status_code == status
    assert resposta.json() == {"detail": erro.message, "service": erro.service}


def test_cors_libera_front(client):
    resposta = client.options("/api/config", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resposta.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_importar_main_nao_cria_banco_nem_app(tmp_path, monkeypatch):
    """O app global só nasce quando o uvicorn o pede (import sem efeito colateral)."""
    import app.main as main

    banco = tmp_path / "lazy.db"
    monkeypatch.setattr(main, "load_settings",
                        lambda: Settings(fiware_host="10.0.0.1", database_path=str(banco)))
    monkeypatch.delitem(main.__dict__, "app", raising=False)
    assert not banco.exists()
    criado = main.app  # primeiro acesso cria
    assert banco.exists()
    assert main.app is criado  # e fica guardado
    criado.state.conn.close()
