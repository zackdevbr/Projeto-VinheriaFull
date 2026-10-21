"""
Rota do chatbot: recebe a pergunta e o histórico do painel e devolve a
resposta do assistente com as ações propostas (que o painel confirma).
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_chatbot
from app.models.schemas_chat import ChatReply, ChatRequest
from app.services.chatbot import Chatbot

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatReply)
async def chat(pedido: ChatRequest, chatbot: Chatbot = Depends(get_chatbot)) -> ChatReply:
    """Pergunta em linguagem natural; a vinheria é resolvida pelo próprio texto."""
    return await chatbot.ask(pedido.message, pedido.history)
