"""
Dependências do FastAPI.

As rotas recebem o ConfigStore e o FiwareClient por injeção, lidos de
app.state, em vez de importar instâncias globais. Assim os testes trocam
qualquer peça sem mexer nas rotas.
"""
from fastapi import Request

from app.core.config import ConfigStore
from app.services.fiware_client import FiwareClient


def get_config_store(request: Request) -> ConfigStore:
    """ConfigStore da aplicação."""
    return request.app.state.config_store


def get_fiware(request: Request) -> FiwareClient:
    """Cliente FIWARE da aplicação."""
    return request.app.state.fiware
