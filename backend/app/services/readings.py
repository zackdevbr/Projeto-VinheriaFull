"""
Leituras de uma vinheria: estado atual (Orion), histórico (STH-Comet) e score.

Normaliza o que vem do FIWARE: valores viram float (ou None quando ausentes
ou inválidos) e o histórico vira [{ts, value}]. Vinheria recém-cadastrada
ainda não tem atributos de sensor no Orion; isso aparece como None, não
como erro.
"""
import math

from app.models.schemas import CurrentReading, HistoryPoint, HistoryQuery, ScoreReport
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fiware_constants import ENTITY_TYPE
from app.services.fiware_errors import FiwareNotFound
from app.services.limits import LimitsStore
from app.services.quality_score import quality_score, unavailable_message


def deslocamentos_paginas(total: int, pagina: int, max_paginas: int) -> list[int]:
    """hOffsets das páginas a buscar para cobrir `total` pontos.

    Até `max_paginas` páginas cobrem tudo (0, pagina, 2*pagina...); acima disso,
    `max_paginas` páginas espaçadas igualmente do início ao fim da janela.
    """
    if total <= 0:
        return []
    if total <= pagina * max_paginas:
        return list(range(0, total, pagina))
    passo = (total - pagina) / (max_paginas - 1)
    return [round(i * passo) for i in range(max_paginas)]


def to_float(valor) -> float | None:
    """Converte um valor do FIWARE para float; None se ausente ou inválido.

    O Orion pode mandar número, texto ("14.2"), vazio (" ") ou outro tipo;
    booleanos, NaN e infinito também viram None.
    """
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if math.isnan(numero) or math.isinf(numero):
        return None
    return numero


def _to_configured(valor) -> bool | None:
    """Atributo configured do ESP32: 1 -> True, 0 -> False, ausente ou inválido -> None."""
    numero = to_float(valor)
    if numero is None:
        return None
    return numero == 1


def reading_from_entity(device_id: str, entidade: dict) -> CurrentReading:
    """Converte uma entidade do Orion (keyValues) no estado atual da vinheria.

    Usada na consulta de uma vinheria e pelo poller da frota. Entidade vazia
    ({}) vira todos os valores None.
    """
    instante = entidade.get("TimeInstant")
    return CurrentReading(
        device_id=device_id,
        temperature=to_float(entidade.get("temperature")),
        humidity=to_float(entidade.get("humidity")),
        luminosity=to_float(entidade.get("luminosity")),
        time_instant=instante if isinstance(instante, str) and instante.strip() else None,
        configured=_to_configured(entidade.get("configured")),
    )


class ReadingsService:
    """Consulta de estado atual, histórico e score por vinheria."""

    def __init__(self, registry: DeviceRegistry, fiware: FiwareClient, limits: LimitsStore):
        self._registry = registry
        self._fiware = fiware
        self._limits = limits

    async def current(self, device_id: str) -> CurrentReading:
        """Estado atual no Orion; sem entidade ou sem leitura, valores None."""
        device = self._registry.get(device_id)
        try:
            entidade = await self._fiware.get_entity(device.entity_id)
        except FiwareNotFound:
            entidade = {}
        return reading_from_entity(device.device_id, entidade)

    async def history(self, device_id: str, query: HistoryQuery) -> list[HistoryPoint]:
        """Histórico de um atributo, normalizado e sem pontos inválidos."""
        device = self._registry.get(device_id)
        brutos = await self._fiware.query_history(
            ENTITY_TYPE, device.entity_id, query.attr,
            last_n=query.last_n, date_from=query.date_from, date_to=query.date_to,
        )
        pontos = []
        for ponto in brutos:
            valor = to_float(ponto.get("attrValue"))
            instante = ponto.get("recvTime")
            if valor is not None and isinstance(instante, str):
                pontos.append(HistoryPoint(ts=instante, value=valor))
        return pontos

    async def score(self, device_id: str) -> ScoreReport:
        """Score atual com a faixa daquela vinheria e, se indisponível, o motivo."""
        leitura = await self.current(device_id)
        limites = self._limits.get(device_id)
        nota, notas = quality_score(leitura, limites)
        return ScoreReport(
            device_id=device_id,
            score=nota,
            available=nota is not None,
            message=unavailable_message(notas),
            attrs=notas,
            limits=limites,
        )
