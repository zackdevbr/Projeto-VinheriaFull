# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes do cache em memória do histórico usado pelo chatbot."""
from datetime import timezone

import pytest

from app.services.fiware_errors import FiwareNotFound
from app.services.history_cache import HistoryCache
from tests.fakes import ReadingsFalso, serie

pytestmark = pytest.mark.anyio

ATRIBUTO = "temperature"
DEVICE = "vinheria001"


@pytest.fixture
def readings():
    return ReadingsFalso()


@pytest.fixture
def cache(readings, relogio):
    return HistoryCache(readings, horas_max=2.0, agora=relogio)


def _iso(instante):
    return instante.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def test_primeira_consulta_busca_a_janela_maxima(cache, readings, relogio):
    readings.series[(DEVICE, ATRIBUTO)] = serie(relogio, [15] * 10)
    await cache.pontos(DEVICE, ATRIBUTO, horas=1)
    consulta = readings.pedidos[0][1]
    assert consulta.last_n is None
    assert consulta.date_from == "2026-10-08T10:00:00.000Z"
    assert consulta.date_to == "2026-10-08T12:00:00.000Z"


async def test_segunda_consulta_busca_so_o_que_chegou_depois(cache, readings, relogio):
    readings.series[(DEVICE, ATRIBUTO)] = serie(relogio, [15, 16, 17])
    await cache.pontos(DEVICE, ATRIBUTO, horas=1)
    ultimo = readings.series[(DEVICE, ATRIBUTO)][-1].ts

    relogio.avancar(60)
    # o STH devolve o último ponto de novo (dateFrom é inclusivo) e mais um novo
    readings.series[(DEVICE, ATRIBUTO)] = serie(relogio, [17, 18])
    pontos = await cache.pontos(DEVICE, ATRIBUTO, horas=1)

    assert readings.pedidos[1][1].date_from == ultimo
    assert readings.pedidos[1][1].date_to == _iso(relogio.agora)
    assert [p.value for p in pontos] == [15, 16, 17, 18]


async def test_descarta_pontos_mais_velhos_que_a_janela_maxima(cache, readings, relogio):
    # 200 pontos de 1 em 1 min: os 79 mais velhos passam de 2 h
    readings.series[(DEVICE, ATRIBUTO)] = serie(relogio, list(range(200)))
    pontos = await cache.pontos(DEVICE, ATRIBUTO, horas=2)
    assert len(pontos) == 121
    assert pontos[0].value == 79


async def test_devolve_so_a_janela_pedida(cache, readings, relogio):
    readings.series[(DEVICE, ATRIBUTO)] = serie(relogio, list(range(100)))
    pontos = await cache.pontos(DEVICE, ATRIBUTO, horas=1)
    assert len(pontos) == 61
    assert pontos[-1].value == 99


async def test_sem_dados_no_sth_devolve_lista_vazia(cache, readings):
    readings.erro = FiwareNotFound("sth", "sem dados")
    assert await cache.pontos(DEVICE, ATRIBUTO, horas=1) == []
