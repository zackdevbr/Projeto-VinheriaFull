"""
Tradução das exceções do FIWARE em respostas HTTP.

Os services levantam FiwareError e suas subclasses; aqui elas viram JSON
{ "detail", "service" } com um status coerente, para o front-end mostrar
uma mensagem clara em vez de um erro 500 genérico.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
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


def register_error_handlers(app: FastAPI) -> None:
    """Registra no app o tradutor de FiwareError."""

    @app.exception_handler(FiwareError)
    async def _trata_fiware(request: Request, erro: FiwareError) -> JSONResponse:
        return JSONResponse(status_code=_status_para(erro),
                            content={"detail": erro.message, "service": erro.service})
