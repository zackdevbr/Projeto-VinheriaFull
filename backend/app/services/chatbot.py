# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

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
# Tempo máximo de cada chamada ao Gemini, em milissegundos (o padrão do SDK é muito longo)
TIMEOUT_GEMINI_MS = 30000
# Teto de tokens da resposta: as respostas são curtas (economiza a cota do plano gratuito)
MAX_SAIDA_TOKENS = 500
SEM_CONCLUSAO = "Não consegui concluir a consulta. Tente reformular a pergunta."
SEM_RESPOSTA = "Não encontrei uma resposta. Tente reformular a pergunta."
# Resumo quando há vinherias cadastradas mas o poller ainda não fez o primeiro ciclo
SEM_CICLO = "Situação agora: FIWARE ok; ainda sem leitura do poller (aguardando o primeiro ciclo)."

INSTRUCAO_BASE = """Você é o assistente da Smart Solutions, que monitora vinherias. Responda em português, curto e direto, em texto simples (sem markdown; listas com hífen).
- Use só os dados do contexto e das ferramentas; nunca invente número, vinheria ou horário. Cite unidade (°C, %) e o período.
- Cada mensagem do usuário traz entre colchetes a situação da frota e as leituras atuais. Para o estado de agora, responda com elas, sem ferramentas. Se houver vinheria em alerta ou offline, ou FIWARE fora do ar, avise no início, mesmo sem ser perguntado.
- Use ferramentas só para histórico (estatisticas, comparar), alertas passados, faixa ideal ou ações.
- Se janela_completa for falso, diga que os dados cobrem só periodo_coberto_horas h.
- Se a ferramenta devolver "erro" com "opcoes", pergunte qual vinheria o usuário quis dizer.
- Valor fora da faixa: recomende uma ação prática de vinheria."""

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


def _num(valor) -> str:
    """Número sem ".0" sobrando; "n/d" quando falta a leitura."""
    return "n/d" if valor is None else f"{valor:g}"


def leituras_frota(report: FleetReport) -> str:
    """Leituras atuais das vinherias online numa linha.

    Com isto no contexto, o estado de agora se responde sem ferramenta: uma
    requisição por pergunta em vez de duas ou mais (a cota gratuita do Gemini
    é por requisição). Vazio com a EC2 fora ou sem vinheria online.
    """
    if not report.fiware_online:
        return ""
    itens = []
    for status in report.vinherias:
        if status.status == "offline":
            continue
        atual = status.current
        score = f", score {_num(status.score)}" if status.score is not None else ""
        itens.append(f"{status.device_id} ({status.name}, {status.city}): {_num(atual.temperature)} °C, "
                     f"{_num(atual.humidity)} %, luz {_num(atual.luminosity)} %{score}")
    return ("Leituras agora: " + "; ".join(itens) + ".") if itens else ""


def _espera_sugerida(exc: errors.APIError) -> float | None:
    """Segundos que o Google manda esperar num 429 (RetryInfo.retryDelay, ex.: "31781s")."""
    corpo = exc.details if isinstance(exc.details, dict) else {}
    for item in (corpo.get("error") or {}).get("details") or []:
        atraso = item.get("retryDelay") if isinstance(item, dict) else None
        if isinstance(atraso, str) and atraso.endswith("s"):
            try:
                return float(atraso[:-1])
            except ValueError:
                return None
    return None


def _duracao(segundos: float) -> str:
    """Ex.: 31781 -> "8 h 49 min"; 150 -> "3 min"."""
    minutos = max(1, round(segundos / 60))
    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto} min" if horas else f"{minutos} min"


def _mensagem_429(exc: errors.APIError) -> str:
    """Espera curta pede paciência; cota diária esgotada diz quanto falta e como contornar."""
    espera = _espera_sugerida(exc)
    if espera is None or espera < 120:
        return "limite de uso do Gemini atingido, aguarde alguns segundos"
    return (f"cota do Gemini esgotada; volta em cerca de {_duracao(espera)}. "
            "Troque o modelo em GEMINI_MODEL (backend/.env) ou ative a cobrança da chave")


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
            # Sem retry interno do SDK (attempts=1): quem repete o 503 é o _gerar, com
            # espera curta; senão uma pergunta poderia levar minutos
            opcoes = types.HttpOptions(timeout=TIMEOUT_GEMINI_MS,
                                       retry_options=types.HttpRetryOptions(attempts=1))
            self._client = genai.Client(api_key=self._settings.gemini_api_key, http_options=opcoes)
        return self._client

    def _config(self) -> types.GenerateContentConfig:
        """Instrução de sistema, tools declaradas e chamada automática desligada (o loop é nosso)."""
        return types.GenerateContentConfig(
            system_instruction=INSTRUCAO_BASE + (INSTRUCAO_ACOES if self._com_acoes else ""),
            tools=[types.Tool(function_declarations=declaracoes(self._com_acoes))],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            # Pensamento mínimo e teto de saída: menos tokens e menos latência
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
            max_output_tokens=MAX_SAIDA_TOKENS,
        )

    def _contexto(self) -> str:
        """Situação da frota e leituras atuais, só das vinherias cadastradas."""
        ids = [device.device_id for device in self._registry.list()]
        report = self._fleet.report(ids)
        if ids and not report.vinherias and report.fiware_online:
            return SEM_CICLO
        leituras = leituras_frota(report)
        return resumo_frota(report, self._fuso) + (f" {leituras}" if leituras else "")

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
                    raise ChatbotRateLimited(_mensagem_429(exc)) from exc
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
        contents.append(_conteudo("user", f"[{self._contexto()}]\n\n{message}"))
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
