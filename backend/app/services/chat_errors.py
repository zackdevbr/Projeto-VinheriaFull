"""
Exceções do chatbot.

Como as do FIWARE e do cadastro, não dependem do FastAPI; a tradução para
resposta HTTP fica em app/api/errors.py (503, 429 e 502).
"""


class ChatbotError(Exception):
    """Falha ao responder pelo Gemini."""
    service = "gemini"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ChatbotUnavailable(ChatbotError):
    """Chatbot sem chave configurada no backend/.env."""


class ChatbotRateLimited(ChatbotError):
    """O Gemini recusou por limite de uso (HTTP 429)."""


class ChatbotUpstreamError(ChatbotError):
    """Outra falha do Gemini ou da rede até ele."""
