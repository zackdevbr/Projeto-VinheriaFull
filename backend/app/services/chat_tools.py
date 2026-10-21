"""
Ferramentas (tools) que o Gemini chama para responder sobre as vinherias.

Cada tool lê os services que já existem (cadastro, frota, histórico,
alertas e faixa) e devolve um dict simples, pronto para virar JSON. Falhas
esperadas (vinheria ambígua ou não encontrada, FIWARE fora, argumento
errado) voltam como {"erro": ...} para o próprio Gemini, que então pergunta
ou explica ao usuário em vez de a requisição falhar.
"""
import inspect
import statistics
from datetime import datetime, timedelta, timezone, tzinfo

from app.models.schemas import Device, HistoryPoint, HistoryQuery
from app.services.chat_stats import (
    NOME_ATRIBUTO,
    UNIDADE,
    estatisticas as calcular_estatisticas,
    filtrar_janela,
    hora_local,
    para_datetime,
)
from app.services.fiware_errors import FiwareError, FiwareNotFound
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound
from app.services.vinheria_resolver import resolve_vinheria

# Atributos aceitos pelas tools (nomes longos do Orion/STH)
ATRIBUTOS = tuple(NOME_ATRIBUTO)
# Pontos pedidos ao STH: os mais novos (a consulta por datas devolveria os mais velhos)
PONTOS_HISTORICO = 500
# Janela aceita pelas tools, em horas
HORAS_MIN, HORAS_MAX = 0.25, 24.0
# Quantos alertas ler do SQLite antes de filtrar pela janela
LIMITE_ALERTAS = 200


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


def horas_validas(valor, padrao: float = 1.0) -> float:
    """Converte a janela pedida pelo Gemini (número ou texto) e recorta em 0,25–24 h."""
    try:
        horas = float(valor)
    except (TypeError, ValueError):
        horas = padrao
    return min(max(horas, HORAS_MIN), HORAS_MAX)


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
            "estatisticas": (self.estatisticas, False),
            "comparar": (self.comparar, False),
            "alertas": (self.alertas, False),
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

    async def _pontos(self, device_id: str, atributo: str, horas: float) -> list[HistoryPoint]:
        """Os 500 pontos mais novos do STH, só os que caem na janela; [] sem dados."""
        consulta = HistoryQuery(attr=atributo, last_n=PONTOS_HISTORICO)
        try:
            pontos = await self._readings.history(device_id, consulta)
        except FiwareNotFound:
            return []
        return filtrar_janela(pontos, horas, self._agora())

    async def estatisticas(self, vinheria: str, atributo: str, horas=1) -> dict:
        """Média, mínimo, máximo, desvio e tendência de um atributo na janela."""
        erro = checar_atributo(atributo)
        if erro:
            return erro
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        horas = horas_validas(horas)
        pontos = await self._pontos(device.device_id, atributo, horas)
        return {"device_id": device.device_id, "name": device.name,
                "atributo": NOME_ATRIBUTO[atributo], "horas_pedidas": horas,
                **calcular_estatisticas(pontos, atributo, horas, self._fuso)}

    async def comparar(self, atributo: str, horas=1) -> dict:
        """Média do atributo em cada vinheria, da maior para a menor (sem dados por último)."""
        erro = checar_atributo(atributo)
        if erro:
            return erro
        horas = horas_validas(horas)
        linhas = []
        for device in self._registry.list():
            linha = {"device_id": device.device_id, "name": device.name, "city": device.city}
            try:
                pontos = await self._pontos(device.device_id, atributo, horas)
            except FiwareError as exc:
                linhas.append({**linha, "media": None, "n": 0,
                               "erro": f"FIWARE indisponível: {exc.message}"})
                continue
            media = round(statistics.fmean(p.value for p in pontos), 1) if pontos else None
            linhas.append({**linha, "media": media, "n": len(pontos)})
        linhas.sort(key=lambda l: (l["media"] is None, -(l["media"] or 0)))
        return {"atributo": NOME_ATRIBUTO[atributo], "unidade": UNIDADE[atributo],
                "horas": horas, "vinherias": linhas}

    async def alertas(self, vinheria: str | None = None, horas=24) -> dict:
        """Alertas abertos nas últimas `horas`, de uma vinheria ou de todas (e da EC2)."""
        device_id = None
        if vinheria:
            device, erro = resolver(self._registry, vinheria)
            if erro:
                return erro
            device_id = device.device_id
        horas = horas_validas(horas, padrao=24.0)
        inicio = self._agora() - timedelta(hours=horas)
        lista = [a for a in self._alerts.list(device_id, limit=LIMITE_ALERTAS)
                 if para_datetime(a.opened_at) >= inicio]
        return {"horas": horas, "alertas": [
            {"device_id": a.device_id, "attr": a.attr, "value": a.value,
             "inicio": hora_local(a.opened_at, self._fuso),
             "fim": hora_local(a.closed_at, self._fuso) if a.closed_at else None,
             "duracao_segundos": a.duration_seconds, "aberto": a.closed_at is None}
            for a in lista]}
