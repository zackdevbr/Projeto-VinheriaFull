"""
Chatbot multi-vinheria (Task 7A) com Google Gemini e function calling.

A cada pergunta, o backend acrescenta uma linha com a situação da frota
(para o bot avisar sozinho de vinheria em alerta ou offline), manda ao
Gemini a conversa e as declarações das tools e executa as tools que ele
pedir, até a resposta final ou o limite de chamadas. Nada é executado no
FIWARE por aqui: as ações viram propostas que o painel confirma.
"""
import asyncio
import logging
from datetime import tzinfo

from google import genai
from google.genai import errors, types

from app.models.schemas_chat import ChatAction, ChatReply, ChatTurn
from app.models.schemas_fleet import FleetReport
from app.services.chat_declarations import declaracoes
from app.services.chat_errors import ChatbotRateLimited, ChatbotUnavailable, ChatbotUpstreamError
from app.services.chat_stats import NOME_ATRIBUTO, hora_local

log = logging.getLogger(__name__)

# Chamadas ao modelo por pergunta (cada pedido de tool gasta uma)
MAX_CHAMADAS = 5
# O Gemini devolve 503 ("alta demanda") em picos passageiros: espera, em segundos,
# antes de cada nova tentativa (uma tupla vazia desliga a nova tentativa)
ESPERAS_503 = (1.0, 2.0)
SEM_CONCLUSAO = "Não consegui concluir a consulta. Tente reformular a pergunta."
SEM_RESPOSTA = "Não encontrei uma resposta. Tente reformular a pergunta."
# Resumo quando há vinherias cadastradas mas o poller ainda não fez o primeiro ciclo
SEM_CICLO = "Situação agora: FIWARE ok; ainda sem leitura do poller (aguardando o primeiro ciclo)."

INSTRUCAO_BASE = """Você é o assistente da Smart Solutions, que monitora vinherias.
Regras:
- Responda sempre em português do Brasil, de forma curta e direta.
- Use só os dados devolvidos pelas ferramentas. Nunca invente número, vinheria ou horário.
- Cite números com unidade (°C para temperatura, % para umidade e luminosidade) e o período a que se referem.
- Se uma estatística vier com janela_completa falso, diga que os dados cobrem só o período_coberto_horas.
- Se uma ferramenta devolver "erro" com "opcoes", pergunte ao usuário qual das vinherias ele quis dizer.
- Quando houver temperatura, umidade ou luz fora da faixa, recomende uma ação prática de vinheria (ex.: ajustar a climatização, ligar o umidificador, apagar ou cobrir a iluminação).
- Cada mensagem do usuário começa com a situação da frota entre colchetes. Se ela citar vinheria em alerta ou offline, ou o FIWARE fora do ar, avise isso no início da resposta, mesmo que o usuário não tenha perguntado.
- Escreva em texto simples, sem markdown: nada de asteriscos, títulos ou tabelas; para listas, use linhas começando com hífen."""

# Regras extras do bloco B (ações com confirmação)
INSTRUCAO_ACOES = """
- Você pode propor ações com propor_comando e propor_faixa, mas só quando o usuário pedir uma ação. Nunca proponha por iniciativa própria; no máximo, sugira em texto.
- As ações NÃO são executadas por você: elas aparecem num cartão e só acontecem quando o usuário clicar em Confirmar. Diga isso na resposta, sem afirmar que a ação já foi feita.
- Se a proposta voltar com "erro", explique o motivo ao usuário."""


def resumo_frota(report: FleetReport, fuso: tzinfo | None = None) -> str:
    """Uma linha em português com a situação da EC2 e das vinherias com problema."""
    if not report.fiware_online:
        desde = (f" desde {hora_local(report.fiware_offline_since, fuso)}"
                 if report.fiware_offline_since else "")
        return (f"Situação agora: FIWARE fora do ar{desde}; "
                "os dados das vinherias podem estar desatualizados.")
    total = len(report.vinherias)
    if total == 0:
        return "Situação agora: FIWARE ok; nenhuma vinheria cadastrada."
    problemas = []
    for status in report.vinherias:
        rotulo = f"{status.device_id} ({status.name})"
        if status.status == "alerta":
            atributos = ", ".join(NOME_ATRIBUTO.get(a.attr, a.attr) for a in status.active_alerts)
            problemas.append(f"{rotulo} em alerta de {atributos or 'faixa'}")
        elif status.status == "offline":
            problemas.append(f"{rotulo} offline")
        elif status.status == "configurando":
            problemas.append(f"{rotulo} aguardando a faixa (configurando)")
    plural = "vinheria" if total == 1 else "vinherias"
    if not problemas:
        return f"Situação agora: FIWARE ok; {total} {plural}, todas normais."
    return f"Situação agora: FIWARE ok; {total} {plural}; " + "; ".join(problemas) + "."


def _conteudo(role: str, texto: str) -> types.Content:
    """Um turno de texto no formato do SDK."""
    return types.Content(role=role, parts=[types.Part.from_text(text=texto)])


class Chatbot:
    """Responde perguntas sobre as vinherias usando o Gemini e as tools."""

    def __init__(self, tools, registry, fleet, settings, client=None,
                 com_acoes: bool = False, fuso: tzinfo | None = None,
                 esperas: tuple[float, ...] = ESPERAS_503):
        # client: genai.Client real (criado na primeira pergunta) ou falso nos testes
        self._tools = tools
        self._registry = registry
        self._fleet = fleet
        self._settings = settings
        self._client = client
        self._com_acoes = com_acoes
        self._fuso = fuso
        self._esperas = esperas

    def _cliente(self):
        """Cliente do Gemini; sem chave no .env, o chat fica indisponível."""
        if not self._settings.gemini_api_key:
            raise ChatbotUnavailable(
                "chatbot não configurado: defina GEMINI_API_KEY no backend/.env")
        if self._client is None:
            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    def _config(self) -> types.GenerateContentConfig:
        """Instrução de sistema, tools declaradas e chamada automática desligada (o loop é nosso)."""
        return types.GenerateContentConfig(
            system_instruction=INSTRUCAO_BASE + (INSTRUCAO_ACOES if self._com_acoes else ""),
            tools=[types.Tool(function_declarations=declaracoes(self._com_acoes))],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def _resumo(self) -> str:
        """Situação atual da frota, só com as vinherias cadastradas."""
        ids = [device.device_id for device in self._registry.list()]
        report = self._fleet.report(ids)
        if ids and not report.vinherias and report.fiware_online:
            return SEM_CICLO
        return resumo_frota(report, self._fuso)

    async def _gerar(self, cliente, contents: list, config):
        """Uma chamada ao modelo, com as falhas traduzidas para ChatbotError.

        Um 503 (pico de demanda do Gemini) é tentado de novo depois das
        esperas configuradas. A mensagem de erro nunca inclui a chave nem o
        corpo da requisição.
        """
        esperas = list(self._esperas)
        while True:
            try:
                return await cliente.aio.models.generate_content(
                    model=self._settings.gemini_model, contents=contents, config=config)
            except errors.APIError as exc:
                if exc.code == 503 and esperas:
                    espera = esperas.pop(0)
                    log.warning("Gemini respondeu 503; nova tentativa em %.1f s", espera)
                    await asyncio.sleep(espera)
                    continue
                if exc.code == 429:
                    raise ChatbotRateLimited(
                        "limite de uso do Gemini atingido, aguarde alguns segundos") from exc
                log.warning("Gemini respondeu HTTP %s", exc.code)
                raise ChatbotUpstreamError(f"falha ao consultar o Gemini (HTTP {exc.code})") from exc
            except Exception as exc:  # rede caída, DNS, timeout: o SDK não padroniza essas falhas
                log.warning("sem conexão com o Gemini: %s", type(exc).__name__)
                raise ChatbotUpstreamError(
                    "falha ao consultar o Gemini: sem conexão com a internet?") from exc

    async def ask(self, message: str, history: list[ChatTurn]) -> ChatReply:
        """Responde a pergunta, executando as tools que o Gemini pedir (no máximo 5 chamadas)."""
        cliente = self._cliente()
        contents = [_conteudo(turno.role, turno.text) for turno in history]
        contents.append(_conteudo("user", f"[{self._resumo()}]\n\n{message}"))
        propostas: list[ChatAction] = []
        config = self._config()
        for _ in range(MAX_CHAMADAS):
            resposta = await self._gerar(cliente, contents, config)
            chamadas = resposta.function_calls or []
            if not chamadas:
                texto = (resposta.text or "").strip()
                return ChatReply(reply=texto or SEM_RESPOSTA, actions=propostas)
            contents.append(resposta.candidates[0].content)
            partes = []
            for chamada in chamadas:
                resultado = await self._tools.executar(chamada.name, dict(chamada.args or {}), propostas)
                partes.append(types.Part.from_function_response(name=chamada.name, response=resultado))
            contents.append(types.Content(role="user", parts=partes))
        return ChatReply(reply=SEM_CONCLUSAO, actions=propostas)
