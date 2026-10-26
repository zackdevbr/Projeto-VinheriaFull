# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes do contrato e da rota do chatbot (spec R2 e R7)."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.models.schemas_chat import ChatAction, ChatReply, ChatRequest, ChatTurn
from app.services.chat_errors import ChatbotRateLimited, ChatbotUpstreamError


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


class ChatbotFalso:
    def __init__(self, erro=None):
        self.erro = erro
        self.perguntas = []

    async def ask(self, message, history):
        self.perguntas.append((message, history))
        if self.erro:
            raise self.erro
        return ChatReply(reply=f"eco: {message}")


@pytest.fixture
def app(tmp_path):
    return create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "chat.db")))


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


def test_chat_sem_chave_da_503(client):
    resposta = client.post("/api/chat", json={"message": "oi"})
    assert resposta.status_code == 503
    assert resposta.json() == {"detail": "chatbot não configurado: defina GEMINI_API_KEY no backend/.env",
                               "service": "gemini"}


def test_chat_responde_200(client, app):
    app.state.chatbot = ChatbotFalso()
    resposta = client.post("/api/chat", json={"message": "oi", "history": [{"role": "user", "text": "a"}]})
    assert resposta.status_code == 200
    assert resposta.json() == {"reply": "eco: oi", "actions": []}
    assert app.state.chatbot.perguntas[0][1] == [ChatTurn(role="user", text="a")]


def test_chat_valida_entrada(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    longo = [{"role": "user", "text": "a"}] * 21
    assert client.post("/api/chat", json={"message": "oi", "history": longo}).status_code == 422


@pytest.mark.parametrize("erro, status", [
    (ChatbotRateLimited("limite"), 429),
    (ChatbotUpstreamError("falhou"), 502),
])
def test_chat_traduz_erros(client, app, erro, status):
    app.state.chatbot = ChatbotFalso(erro)
    resposta = client.post("/api/chat", json={"message": "oi"})
    assert resposta.status_code == status
    assert resposta.json()["service"] == "gemini"
