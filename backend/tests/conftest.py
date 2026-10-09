"""Fixtures compartilhadas pelos testes do backend."""
import pytest

from app.core.config import ConfigStore, Settings
from app.core.db import connect
from app.models.schemas import Device
from app.services.alert_log import AlertLog
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fleet_state import FleetState
from app.services.limits import LimitsStore
from app.services.readings import ReadingsService
from app.services.trigger_engine import TriggerEngine
from tests.fakes import FiwareFalso, Relogio


@pytest.fixture
def anyio_backend():
    """Roda os testes assíncronos (marcados com anyio) no asyncio."""
    return "asyncio"


@pytest.fixture
def settings(tmp_path):
    """Settings de teste: IP fictício e banco num diretório temporário."""
    return Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "teste.db"))


@pytest.fixture
def conn(settings):
    """Conexão SQLite já com o schema criado."""
    conexao = connect(settings.database_path)
    yield conexao
    conexao.close()


@pytest.fixture
def store(conn, settings):
    """ConfigStore sobre o banco de teste."""
    return ConfigStore(conn, settings)


@pytest.fixture
def fiware(store, settings):
    """FiwareClient apontando para o IP fictício 10.0.0.1 (respx intercepta)."""
    return FiwareClient(store, settings)


@pytest.fixture
def fiware_sem_ip(tmp_path):
    """FiwareClient de um backend iniciado sem FIWARE_HOST."""
    settings = Settings(fiware_host="", database_path=str(tmp_path / "sem_ip.db"))
    conexao = connect(settings.database_path)
    yield FiwareClient(ConfigStore(conexao, settings), settings)
    conexao.close()


@pytest.fixture
def limits(conn):
    """LimitsStore sobre o banco de teste."""
    return LimitsStore(conn)


@pytest.fixture
def registry(conn, fiware, limits):
    """DeviceRegistry com FIWARE interceptado pelo respx e banco de teste."""
    return DeviceRegistry(conn, fiware, limits)


@pytest.fixture
def cadastrar(conn, limits):
    """Grava vinherias direto no SQLite, sem FIWARE (para testes de leitura e remoção)."""
    def _cadastrar(numero="001", name="Vinheria Paulista", city="São Paulo",
                   created_at="2026-10-07T21:00:00+00:00"):
        device = Device(device_id=f"vinheria{numero}",
                        entity_id=f"urn:ngsi-ld:Vinheria:{numero}",
                        name=name, city=city, created_at=created_at)
        with conn:
            conn.execute(
                "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (device.device_id, device.entity_id, device.name, device.city,
                 device.created_at),
            )
            limits.seed_defaults(device.device_id)
        return device
    return _cadastrar


@pytest.fixture
def readings(registry, fiware, limits):
    """ReadingsService com FIWARE interceptado pelo respx."""
    return ReadingsService(registry, fiware, limits)


@pytest.fixture
def alert_log(conn):
    """AlertLog sobre o banco de teste."""
    return AlertLog(conn)


@pytest.fixture
def fleet():
    """Retrato da frota vazio."""
    return FleetState()


@pytest.fixture
def fiware_falso():
    """FIWARE falso para o motor e o controle (sem respx)."""
    return FiwareFalso()


@pytest.fixture
def relogio():
    """Relógio parado em 2026-10-08 12:00:00 UTC, avançado pelo teste."""
    return Relogio()


@pytest.fixture
def engine(registry, limits, alert_log, fiware_falso, store, fleet, relogio):
    """TriggerEngine com FIWARE falso, banco de teste e relógio controlado."""
    return TriggerEngine(registry, limits, alert_log, fiware_falso, store, fleet, clock=relogio)
