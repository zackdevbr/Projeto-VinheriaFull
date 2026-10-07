"""
Ponto de entrada do backend FastAPI (Smart Solutions).

create_app() monta a aplicação: lê a configuração, abre o SQLite, cria o
cliente FIWARE e os services de cadastro e leituras, e registra CORS,
tradução de erros e rotas. Os testes chamam create_app() com Settings
próprios; o uvicorn usa o objeto `app` do fim do arquivo
(uvicorn app.main:app --reload, rodando de dentro de backend/).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_config, routes_data, routes_devices
from app.api.errors import register_error_handlers
from app.core.config import ConfigStore, Settings, load_settings
from app.core.db import connect
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.limits import LimitsStore
from app.services.readings import ReadingsService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida do app: no desligamento, fecha o pool HTTP e o SQLite."""
    yield
    await app.state.fiware.aclose()
    app.state.conn.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação com todas as dependências ligadas."""
    settings = settings or load_settings()
    conn = connect(settings.database_path)
    store = ConfigStore(conn, settings)

    app = FastAPI(
        title="Smart Solutions — API de Vinherias",
        description="Backend do monitoramento de vinherias integrado ao FIWARE.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.conn = conn
    app.state.config_store = store
    fiware = FiwareClient(store, settings)
    limits = LimitsStore(conn)
    registry = DeviceRegistry(conn, fiware, limits)
    app.state.fiware = fiware
    app.state.limits = limits
    app.state.registry = registry
    app.state.readings = ReadingsService(registry, fiware, limits)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(routes_config.router)
    app.include_router(routes_devices.router)
    app.include_router(routes_data.router)
    return app


def __getattr__(nome: str):
    """Cria o `app` global só no primeiro acesso (PEP 562).

    O uvicorn pede `app.main:app` e dispara a criação; importar o módulo nos
    testes só para usar `create_app` não abre banco nem lê o .env.
    """
    if nome == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")
