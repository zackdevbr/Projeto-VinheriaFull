"""
Ferramentas (tools) que o Gemini chama para responder sobre as vinherias.

Cada tool lê os services que já existem (cadastro, frota, histórico,
alertas e faixa) e devolve um dict simples, pronto para virar JSON. Falhas
esperadas (vinheria ambígua ou não encontrada, FIWARE fora, argumento
errado) voltam como {"erro": ...} para o próprio Gemini, que então pergunta
ou explica ao usuário em vez de a requisição falhar.
"""
import inspect
from datetime import datetime, timezone, tzinfo

from app.models.schemas import Device
from app.services.chat_stats import NOME_ATRIBUTO, UNIDADE, hora_local
from app.services.fiware_errors import FiwareError
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound
from app.services.vinheria_resolver import resolve_vinheria

# Atributos aceitos pelas tools (nomes longos do Orion/STH)
ATRIBUTOS = tuple(NOME_ATRIBUTO)


def agora_utc() -> datetime:
    """Relógio padrão das tools (os testes injetam um relógio parado)."""
    return datetime.now(timezone.utc)


def resolver(registry, texto) -> tuple[Device | None, dict | None]:
    """Resolve o texto livre em vinheria; em falha, devolve o erro pronto para o Gemini."""
    try:
        return resolve_vinheria(str(texto or ""), registry.list()), None
    except AmbiguousVinheria as exc:
        opcoes = [{"device_id": d.device_id, "name": d.name, "city": d.city} for d in exc.options]
        return None, {"erro": exc.message, "opcoes": opcoes}
    except VinheriaNotFound as exc:
        return None, {"erro": exc.message}


def checar_atributo(atributo) -> dict | None:
    """Erro para o Gemini quando o atributo não é um dos três sensores."""
    if atributo in ATRIBUTOS:
        return None
    return {"erro": f"atributo inválido: {atributo}; use temperature, humidity ou luminosity"}


def _faixa(limites, atributo: str) -> dict:
    """Faixa de um atributo com a unidade, no formato que o bot cita."""
    faixa = getattr(limites, atributo)
    return {"min": faixa.min, "max": faixa.max, "unidade": UNIDADE[atributo]}


class ChatTools:
    """Tools de leitura do chatbot e o despacho por nome."""

    def __init__(self, registry, readings, fleet, alerts, limits,
                 agora=agora_utc, fuso: tzinfo | None = None):
        self._registry = registry
        self._readings = readings
        self._fleet = fleet
        self._alerts = alerts
        self._limits = limits
        self._agora = agora
        self._fuso = fuso
        # nome da tool -> (função, se recebe a lista de propostas da pergunta)
        self._tabela = {
            "listar_vinherias": (self.listar_vinherias, False),
            "estado_atual": (self.estado_atual, False),
            "limites": (self.limites, False),
        }

    def registrar(self, nome: str, funcao, recebe_propostas: bool = False) -> None:
        """Acrescenta uma tool (as de ação, do bloco B, chegam por aqui)."""
        self._tabela[nome] = (funcao, recebe_propostas)

    def nomes(self) -> set[str]:
        """Nomes das tools disponíveis (conferidos contra as declarações)."""
        return set(self._tabela)

    async def executar(self, nome: str, args: dict, propostas: list) -> dict:
        """Executa a tool pedida pelo Gemini; qualquer falha esperada vira {"erro"}."""
        if nome not in self._tabela:
            return {"erro": f"ferramenta desconhecida: {nome}"}
        funcao, recebe_propostas = self._tabela[nome]
        argumentos = dict(args or {})
        if recebe_propostas:
            argumentos["propostas"] = propostas
        try:
            inspect.signature(funcao).bind(**argumentos)
        except TypeError as exc:
            return {"erro": f"argumentos inválidos para {nome}: {exc}"}
        try:
            return await funcao(**argumentos)
        except FiwareError as exc:
            return {"erro": f"FIWARE indisponível: {exc.message}"}

    async def listar_vinherias(self) -> dict:
        """Todas as cadastradas, com o status do último ciclo do poller."""
        vinherias = []
        for device in self._registry.list():
            status = self._fleet.get(device.device_id)
            vinherias.append({
                "device_id": device.device_id, "name": device.name, "city": device.city,
                "status": status.status if status else "aguardando",
                "offline_reason": status.offline_reason if status else None,
            })
        return {"fiware_online": self._fleet.fiware_online, "vinherias": vinherias}

    async def estado_atual(self, vinheria: str) -> dict:
        """Valores atuais, score, "visto há" e alertas ativos de uma vinheria."""
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        status = self._fleet.get(device.device_id)
        if status is None:
            return {"erro": "ainda sem leitura do poller, tente em alguns segundos"}
        atual = status.current
        return {
            "device_id": device.device_id, "name": device.name, "city": device.city,
            "status": status.status, "offline_reason": status.offline_reason,
            "visto_ha_segundos": status.seconds_since,
            "temperatura": atual.temperature, "umidade": atual.humidity,
            "luminosidade": atual.luminosity,
            "unidades": {"temperatura": "°C", "umidade": "%", "luminosidade": "%"},
            "score": status.score,
            "alertas_ativos": [
                {"atributo": NOME_ATRIBUTO.get(a.attr, a.attr), "valor": a.value,
                 "desde": hora_local(a.since, self._fuso)}
                for a in status.active_alerts],
        }

    async def limites(self, vinheria: str) -> dict:
        """Faixa ideal da vinheria (a mesma que dispara os alertas)."""
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        limites = self._limits.get(device.device_id)
        return {"device_id": device.device_id, "name": device.name,
                **{NOME_ATRIBUTO[a]: _faixa(limites, a) for a in ATRIBUTOS}}
