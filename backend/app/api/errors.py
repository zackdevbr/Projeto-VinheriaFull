"""
Tradução das exceções dos services em respostas HTTP.

FiwareError (falhas do FIWARE) e RegistryError (regras do cadastro) viram
JSON { "detail", "service" } com um status coerente, para o front-end
mostrar uma mensagem clara em vez de um erro 500 genérico.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)
from app.services.registry_errors import (
    AmbiguousVinheria,
    DeviceAlreadyExists,
    RegistryError,
)


def _status_para(erro: FiwareError) -> int:
    """Status HTTP da resposta para cada tipo de falha do FIWARE."""
    if isinstance(erro, FiwareUnavailable):
        return 503
    if isinstance(erro, FiwareNotFound):
        return 404
    if isinstance(erro, FiwareConflict):
        return 409
    return 502


def _status_registry(erro: RegistryError) -> int:
    """Conflito de cadastro ou referência ambígua dão 409; o resto é 'não encontrado'."""
    if isinstance(erro, (DeviceAlreadyExists, AmbiguousVinheria)):
        return 409
    return 404


def register_error_handlers(app: FastAPI) -> None:
    """Registra no app os tradutores de FiwareError e RegistryError."""

    @app.exception_handler(FiwareError)
    async def _trata_fiware(request: Request, erro: FiwareError) -> JSONResponse:
        return JSONResponse(status_code=_status_para(erro),
                            content={"detail": erro.message, "service": erro.service})

    @app.exception_handler(RegistryError)
    async def _trata_registry(request: Request, erro: RegistryError) -> JSONResponse:
        return JSONResponse(status_code=_status_registry(erro),
                            content={"detail": erro.message, "service": erro.service})
