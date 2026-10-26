# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Cache em memória do histórico usado pelo chatbot.

Guarda, por vinheria e atributo, os pontos das últimas `horas_max` horas e,
a cada consulta, busca no STH-Comet só o que chegou depois do último ponto
guardado. Evita repetir a paginação inteira a cada pergunta. O cache vive
no processo: reiniciar o backend o esvazia, e a próxima pergunta o refaz.
"""
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.models.schemas import HistoryPoint, HistoryQuery
from app.services.chat_stats import filtrar_janela, para_datetime
from app.services.fiware_errors import FiwareNotFound


def _iso_utc(instante: datetime) -> str:
    """Instante em UTC no formato do STH (2026-10-08T12:00:00.000Z)."""
    return instante.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class HistoryCache:
    """Pontos recentes de cada (vinheria, atributo), atualizados de forma incremental."""

    def __init__(self, readings, horas_max: float, agora: Callable[[], datetime]):
        self._readings = readings
        self._horas_max = horas_max
        self._agora = agora
        self._series: dict[tuple[str, str], list[HistoryPoint]] = {}

    async def pontos(self, device_id: str, atributo: str, horas: float) -> list[HistoryPoint]:
        """Pontos das últimas `horas` (até `horas_max`), atualizando o cache antes."""
        agora = self._agora()
        chave = (device_id, atributo)
        guardados = self._series.get(chave, [])
        if guardados:
            desde = para_datetime(guardados[-1].ts)
            desde_iso = guardados[-1].ts
        else:
            desde = agora - timedelta(hours=self._horas_max)
            desde_iso = _iso_utc(desde)
        novos = await self._buscar(device_id, atributo, desde_iso, _iso_utc(agora))
        # dateFrom é inclusivo: o último ponto guardado volta na resposta
        if guardados:
            novos = [ponto for ponto in novos if para_datetime(ponto.ts) > desde]
        self._series[chave] = filtrar_janela(guardados + novos, self._horas_max, agora)
        return filtrar_janela(self._series[chave], horas, agora)

    async def _buscar(self, device_id: str, atributo: str,
                      desde: str, ate: str) -> list[HistoryPoint]:
        """Histórico por datas no STH; sem dados lá, lista vazia."""
        consulta = HistoryQuery(attr=atributo, date_from=desde, date_to=ate)
        try:
            return await self._readings.history(device_id, consulta)
        except FiwareNotFound:
            return []
