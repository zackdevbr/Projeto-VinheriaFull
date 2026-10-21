"""Testes do contrato e da rota do chatbot (spec R2 e R7)."""
import pytest
from pydantic import ValidationError

from app.models.schemas_chat import ChatAction, ChatReply, ChatRequest, ChatTurn


def test_chat_request_aceita_mensagem_e_historico():
    pedido = ChatRequest(message="  Como está a 001?  ",
                         history=[{"role": "user", "text": "oi"}, {"role": "model", "text": "olá"}])
    assert pedido.message == "Como está a 001?"
    assert pedido.history[1] == ChatTurn(role="model", text="olá")


@pytest.mark.parametrize("dados", [
    {"message": ""},
    {"message": "   "},
    {"message": "x" * 1001},
    {"message": "oi", "history": [{"role": "user", "text": "a"}] * 21},
    {"message": "oi", "history": [{"role": "system", "text": "a"}]},
])
def test_chat_request_rejeita_entrada_invalida(dados):
    with pytest.raises(ValidationError):
        ChatRequest(**dados)


def test_chat_reply_comeca_sem_acoes():
    assert ChatReply(reply="ok").actions == []


def test_chat_action_de_comando():
    acao = ChatAction(kind="command", device_id="vinheria002", name="Vinheria Mineira",
                      summary="Piscar a luz", command="blink_lux")
    assert acao.limits is None
