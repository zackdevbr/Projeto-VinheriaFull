# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Tradução das exceções dos services em respostas HTTP.

FiwareError (falhas do FIWARE), RegistryError (regras do cadastro) e
ChatbotError (falhas do chatbot) viram JSON { "detail", "service" } com um
status coerente, para o front-end mostrar uma mensagem clara em vez de um
erro 500 genérico.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.chat_errors import ChatbotError, ChatbotRateLimited, ChatbotUnavailable
from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)
from app.services.registry_errors import (
    AmbiguousVinheria,
    DeviceAlreadyExists,
    DeviceUnavailable,
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
    """Conflito (cadastro repetido, referência ambígua, vinheria indisponível) dá 409; o resto é 404."""
    if isinstance(erro, (DeviceAlreadyExists, AmbiguousVinheria, DeviceUnavailable)):
        return 409
    return 404


def _status_chatbot(erro: ChatbotError) -> int:
    """Sem chave dá 503, limite do Gemini dá 429, o resto (Gemini ou rede) dá 502."""
    if isinstance(erro, ChatbotUnavailable):
        return 503
    if isinstance(erro, ChatbotRateLimited):
        return 429
    return 502


def register_error_handlers(app: FastAPI) -> None:
    """Registra no app os tradutores de FiwareError, RegistryError e ChatbotError."""

    @app.exception_handler(FiwareError)
    async def _trata_fiware(request: Request, erro: FiwareError) -> JSONResponse:
        return JSONResponse(status_code=_status_para(erro),
                            content={"detail": erro.message, "service": erro.service})

    @app.exception_handler(RegistryError)
    async def _trata_registry(request: Request, erro: RegistryError) -> JSONResponse:
        return JSONResponse(status_code=_status_registry(erro),
                            content={"detail": erro.message, "service": erro.service})

    @app.exception_handler(ChatbotError)
    async def _trata_chatbot(request: Request, erro: ChatbotError) -> JSONResponse:
        return JSONResponse(status_code=_status_chatbot(erro),
                            content={"detail": erro.message, "service": erro.service})
