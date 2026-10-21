"""Testes das tools de leitura do chatbot (spec R4)."""
from datetime import timedelta, timezone

import pytest

from app.models.schemas import HistoryPoint
from app.models.schemas_fleet import ActiveAlert, SensorValues
from app.services.chat_tools import ChatTools
from app.services.fiware_errors import FiwareUnavailable
from tests.fakes import status_vinheria

pytestmark = pytest.mark.anyio


class ReadingsFalso:
    """Substitui o ReadingsService: devolve séries por (device_id, atributo)."""

    def __init__(self):
        self.series = {}
        self.erro = None
        self.pedidos = []

    async def history(self, device_id, query):
        self.pedidos.append((device_id, query))
        if self.erro:
            raise self.erro
        return list(self.series.get((device_id, query.attr), []))


def serie(relogio, valores, passo_min=1.0):
    """Pontos do mais velho ao mais novo, o último no instante do relógio."""
    n = len(valores)
    return [HistoryPoint(ts=(relogio.agora - timedelta(minutes=passo_min * (n - 1 - i)))
                         .strftime("%Y-%m-%dT%H:%M:%S.000Z"), value=v)
            for i, v in enumerate(valores)]


@pytest.fixture
def readings_falso():
    return ReadingsFalso()


@pytest.fixture
def tools(registry, readings_falso, fleet, alert_log, limits, relogio):
    return ChatTools(registry, readings_falso, fleet, alert_log, limits,
                     agora=relogio, fuso=timezone.utc)


@pytest.fixture
def duas(cadastrar):
    """vinheria001 em São Paulo e vinheria002 em Belo Horizonte."""
    cadastrar("001", "Vinheria Paulista", "São Paulo")
    cadastrar("002", "Vinheria Mineira", "Belo Horizonte")


def retrato(fleet, relogio, *statuses):
    fleet.replace(list(statuses), at=relogio.iso())


async def test_vinheria_ambigua_devolve_opcoes(tools, duas):
    r = await tools.executar("estado_atual", {"vinheria": "vinheria"}, [])
    assert "erro" in r
    assert [o["device_id"] for o in r["opcoes"]] == ["vinheria001", "vinheria002"]


async def test_vinheria_nao_encontrada(tools, duas):
    r = await tools.executar("estado_atual", {"vinheria": "Recife"}, [])
    assert "erro" in r and "opcoes" not in r


async def test_listar_vinherias_com_status(tools, duas, fleet, relogio):
    retrato(fleet, relogio, status_vinheria("vinheria001", "alerta"))
    r = await tools.executar("listar_vinherias", {}, [])
    assert r["fiware_online"] is True
    assert [(v["device_id"], v["status"]) for v in r["vinherias"]] == [
        ("vinheria001", "alerta"), ("vinheria002", "aguardando")]
    assert r["vinherias"][0]["name"] == "Vinheria Paulista"


async def test_listar_sem_vinherias(tools):
    assert (await tools.executar("listar_vinherias", {}, []))["vinherias"] == []


async def test_estado_atual_sem_retrato(tools, duas):
    r = await tools.executar("estado_atual", {"vinheria": "São Paulo"}, [])
    assert "poller" in r["erro"]


async def test_estado_atual_com_retrato(tools, duas, fleet, relogio):
    status = status_vinheria("vinheria001", "alerta").model_copy(update={
        "seconds_since": 4, "score": 72.5,
        "current": SensorValues(temperature=21.3, humidity=60, luminosity=10),
        "active_alerts": [ActiveAlert(attr="temperature", value=21.3,
                                      since="2026-10-08T11:50:00+00:00")]})
    retrato(fleet, relogio, status)
    r = await tools.executar("estado_atual", {"vinheria": "sao paulo"}, [])
    assert (r["device_id"], r["status"], r["temperatura"], r["score"]) == (
        "vinheria001", "alerta", 21.3, 72.5)
    assert r["visto_ha_segundos"] == 4
    assert r["alertas_ativos"] == [{"atributo": "temperatura", "valor": 21.3, "desde": "08/10 11:50"}]


async def test_limites_padrao(tools, duas):
    r = await tools.executar("limites", {"vinheria": "vinheria002"}, [])
    assert r["temperatura"] == {"min": 12, "max": 18, "unidade": "°C"}
    assert r["luminosidade"]["max"] == 30


async def test_tool_desconhecida(tools):
    assert "erro" in await tools.executar("apagar_tudo", {}, [])


async def test_argumentos_invalidos(tools, duas):
    r = await tools.executar("estado_atual", {"cidade": "SP"}, [])
    assert "argumentos inválidos" in r["erro"]


async def test_fiware_fora_vira_erro(tools, duas, readings_falso):
    readings_falso.erro = FiwareUnavailable("sth", "sem resposta")
    r = await tools.executar("estatisticas", {"vinheria": "001", "atributo": "temperature"}, [])
    assert r == {"erro": "FIWARE indisponível: sem resposta"}
