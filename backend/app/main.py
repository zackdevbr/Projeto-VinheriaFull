"""
Ponto de entrada do backend FastAPI (Smart Solutions).

create_app() monta a aplicação: lê a configuração, restaura o banco de um
backup se o arquivo sumiu, abre o SQLite, cria o cliente FIWARE e os
services (cadastro, leituras, alertas, frota, motor, controle e backup) e
registra CORS, tradução de erros e rotas. O lifespan sobe o poller e o
backup em fundo quando Settings.run_background está ligado. Os testes
chamam create_app() com Settings próprios; o uvicorn usa o objeto `app` do
fim do arquivo (uvicorn app.main:app --reload, rodando de dentro de
backend/).
"""
import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_alerts,
    routes_config,
    routes_data,
    routes_devices,
    routes_fleet,
    routes_triggers,
)
from app.api.errors import register_error_handlers
from app.core.backup import BackupService, restore_if_missing
from app.core.config import ConfigStore, Settings, load_settings
from app.core.db import connect
from app.services.alert_log import AlertLog
from app.services.device_control import DeviceControl
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fleet_state import FleetState
from app.services.limits import LimitsStore
from app.services.readings import ReadingsService
from app.services.trigger_engine import TriggerEngine

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida do app.

    Na partida, com run_background ligado, sobe o poller (TriggerEngine) e
    o backup periódico. No desligamento, cancela as tarefas, grava o backup
    final e fecha o pool HTTP e o SQLite.
    """
    tarefas = []
    if app.state.settings.run_background:
        tarefas.append(asyncio.create_task(app.state.engine.run()))
        if app.state.backup.enabled:
            tarefas.append(asyncio.create_task(app.state.backup.run()))
    yield
    for tarefa in tarefas:
        tarefa.cancel()
    for tarefa in tarefas:
        with suppress(asyncio.CancelledError):
            await tarefa
    try:
        app.state.backup.backup_now()
    except (OSError, sqlite3.Error):
        log.exception("falha ao gravar o backup final do banco")
    await app.state.fiware.aclose()
    app.state.conn.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação com todas as dependências ligadas."""
    settings = settings or load_settings()
    # Banco apagado por engano ou máquina nova: volta do backup mais recente
    restore_if_missing(settings.database_path, settings.backup_dir)
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
    alerts = AlertLog(conn)
    fleet = FleetState()
    engine = TriggerEngine(registry, limits, alerts, fiware, store, fleet)
    app.state.alerts = alerts
    app.state.fleet = fleet
    app.state.engine = engine
    app.state.control = DeviceControl(registry, limits, fiware, fleet, engine)
    app.state.backup = BackupService(conn, settings.backup_dir, settings.backup_keep,
                                     settings.backup_minutes)

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
    app.include_router(routes_triggers.router)
    app.include_router(routes_alerts.router)
    app.include_router(routes_fleet.router)
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
