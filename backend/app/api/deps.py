# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Dependências do FastAPI.

As rotas recebem os services por injeção, lidos de app.state, em vez de
importar instâncias globais. Assim os testes trocam qualquer peça sem
mexer nas rotas.
"""
from fastapi import Request

from app.core.config import ConfigStore
from app.services.alert_log import AlertLog
from app.services.chatbot import Chatbot
from app.services.device_control import DeviceControl
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fleet_state import FleetState
from app.services.readings import ReadingsService


def get_config_store(request: Request) -> ConfigStore:
    """ConfigStore da aplicação."""
    return request.app.state.config_store


def get_fiware(request: Request) -> FiwareClient:
    """Cliente FIWARE da aplicação."""
    return request.app.state.fiware


def get_registry(request: Request) -> DeviceRegistry:
    """Cadastro de vinherias da aplicação."""
    return request.app.state.registry


def get_readings(request: Request) -> ReadingsService:
    """Serviço de leituras da aplicação."""
    return request.app.state.readings


def get_alert_log(request: Request) -> AlertLog:
    """Log de alertas da aplicação."""
    return request.app.state.alerts


def get_fleet(request: Request) -> FleetState:
    """Retrato da frota da aplicação."""
    return request.app.state.fleet


def get_control(request: Request) -> DeviceControl:
    """Controle de faixa e comandos da aplicação."""
    return request.app.state.control


def get_chatbot(request: Request) -> Chatbot:
    """Chatbot da aplicação."""
    return request.app.state.chatbot
