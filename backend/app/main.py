"""
Ponto de entrada do backend FastAPI (Smart Solutions).

create_app() monta a aplicação: lê a configuração, abre o SQLite, cria o
cliente FIWARE e registra CORS, tradução de erros e rotas. Os testes chamam
create_app() com Settings próprios; o uvicorn usa o objeto `app` do fim do
arquivo (uvicorn app.main:app --reload, rodando de dentro de backend/).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_config
from app.api.errors import register_error_handlers
from app.core.config import ConfigStore, Settings, load_settings
from app.core.db import connect
from app.services.fiware_client import FiwareClient


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
    app.state.fiware = FiwareClient(store, settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(routes_config.router)
    return app


app = create_app()
