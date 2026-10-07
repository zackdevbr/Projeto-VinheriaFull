"""Fixtures compartilhadas pelos testes do backend."""
import pytest


@pytest.fixture
def anyio_backend():
    """Roda os testes assíncronos (marcados com anyio) no asyncio."""
    return "asyncio"
