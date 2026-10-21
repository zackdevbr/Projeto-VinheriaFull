"""
Modelos do chatbot (Task 7A): pedido do painel, turno do histórico,
resposta do assistente e ação proposta.

O backend não guarda a conversa: o painel manda o histórico (só texto) a
cada pergunta. As ações propostas nunca são executadas aqui; o painel
executa pelas rotas de faixa e de comando depois do Confirmar.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import Limits
from app.models.schemas_fleet import ManualCommand

# Quantos turnos anteriores o painel pode mandar junto com a pergunta
MAX_HISTORICO = 20


class ChatTurn(BaseModel):
    """Um turno anterior da conversa: do usuário ou do modelo."""
    role: Literal["user", "model"]
    text: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """Pergunta do painel com o histórico da conversa."""
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORICO)


class ChatAction(BaseModel):
    """Ação proposta pelo assistente, aguardando o Confirmar do usuário.

    kind="command" traz `command`; kind="limits" traz a faixa completa
    (`limits`) já com a mudança, pronta para o PUT /triggers.
    """
    kind: Literal["command", "limits"]
    device_id: str
    name: str
    summary: str
    command: ManualCommand | None = None
    limits: Limits | None = None


class ChatReply(BaseModel):
    """Resposta do assistente e as ações que ele propôs nesta pergunta."""
    reply: str
    actions: list[ChatAction] = Field(default_factory=list)
