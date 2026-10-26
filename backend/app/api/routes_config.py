# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Rotas de configuração: ver e trocar o IP do FIWARE e os intervalos em
runtime, e testar a saúde dos componentes no IP atual.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_config_store, get_fiware
from app.core.config import ConfigStore
from app.models.schemas import ConfigUpdate, HealthReport, RuntimeConfig
from app.services.fiware_client import FiwareClient

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=RuntimeConfig)
def read_config(store: ConfigStore = Depends(get_config_store)) -> RuntimeConfig:
    """Configuração em uso agora."""
    return store.get()


@router.put("", response_model=RuntimeConfig)
def write_config(changes: ConfigUpdate,
                 store: ConfigStore = Depends(get_config_store)) -> RuntimeConfig:
    """Atualiza só os campos enviados; vale na hora, sem reiniciar."""
    return store.update(changes)


@router.get("/health", response_model=HealthReport)
async def read_health(fiware: FiwareClient = Depends(get_fiware)) -> HealthReport:
    """Testa Orion, IoT Agent e STH-Comet no IP configurado."""
    return await fiware.health()
