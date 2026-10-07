"""Fixtures compartilhadas pelos testes do backend."""
import pytest

from app.core.config import ConfigStore, Settings
from app.core.db import connect
from app.services.fiware_client import FiwareClient
from app.services.limits import LimitsStore


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
