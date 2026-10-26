"""Testes das tools de leitura do chatbot (spec R4)."""
from datetime import timedelta, timezone

import pytest

from app.models.schemas import HistoryPoint
from app.models.schemas_fleet import ActiveAlert, SensorValues
from app.services.chat_tools import ChatTools
from app.services.fiware_errors import FiwareUnavailable
from tests.fakes import ReadingsFalso, serie, status_vinheria

pytestmark = pytest.mark.anyio


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


from app.services.fiware_errors import FiwareNotFound  # noqa: E402


async def test_estatisticas_da_ultima_hora(tools, duas, readings_falso, relogio):
    # 90 pontos de 1 em 1 min: os 30 mais velhos ficam fora da janela de 1 h
    readings_falso.series[("vinheria001", "temperature")] = serie(relogio, [30] * 29 + [14, 15, 16] * 20 + [15])
    r = await tools.executar("estatisticas", {"vinheria": "São Paulo", "atributo": "temperature"}, [])
    assert (r["device_id"], r["atributo"], r["horas_pedidas"]) == ("vinheria001", "temperatura", 1.0)
    assert (r["n"], r["media"], r["minimo"], r["maximo"]) == (61, 15.0, 14, 16)
    # consulta por datas: as 2 h que terminam no relógio (o cache enche a janela máxima)
    consulta = readings_falso.pedidos[0][1]
    assert consulta.last_n is None
    assert (consulta.date_from, consulta.date_to) == (
        "2026-10-08T10:00:00.000Z", "2026-10-08T12:00:00.000Z")


async def test_estatisticas_sem_dados_no_sth(tools, duas, readings_falso):
    readings_falso.erro = FiwareNotFound("sth", "sem dados")
    r = await tools.executar("estatisticas", {"vinheria": "001", "atributo": "humidity"}, [])
    assert r["n"] == 0


@pytest.mark.parametrize("horas, esperado", [("2", 2.0), (0, 0.25), (100, 2.0), ("abc", 1.0)])
async def test_estatisticas_recortam_horas(tools, duas, horas, esperado):
    r = await tools.executar("estatisticas",
                             {"vinheria": "001", "atributo": "humidity", "horas": horas}, [])
    assert r["horas_pedidas"] == esperado


async def test_estatisticas_atributo_invalido(tools, duas):
    r = await tools.executar("estatisticas", {"vinheria": "001", "atributo": "pressao"}, [])
    assert "atributo inválido" in r["erro"]


async def test_comparar_ordena_pela_media(tools, duas, cadastrar, readings_falso, relogio):
    cadastrar("003", "Vinheria Sul", "Porto Alegre")
    readings_falso.series[("vinheria001", "humidity")] = serie(relogio, [55, 57])
    readings_falso.series[("vinheria002", "humidity")] = serie(relogio, [70, 72])
    r = await tools.executar("comparar", {"atributo": "humidity"}, [])
    assert r["unidade"] == "%"
    assert [(v["device_id"], v["media"]) for v in r["vinherias"]] == [
        ("vinheria002", 71.0), ("vinheria001", 56.0), ("vinheria003", None)]


async def test_comparar_isola_falha_de_uma_vinheria(tools, duas, readings_falso, relogio):
    original = readings_falso.history

    async def falha_na_002(device_id, query):
        if device_id == "vinheria002":
            raise FiwareUnavailable("sth", "timeout")
        return await original(device_id, query)

    readings_falso.history = falha_na_002
    readings_falso.series[("vinheria001", "temperature")] = serie(relogio, [14])
    r = await tools.executar("comparar", {"atributo": "temperature"}, [])
    assert r["vinherias"][0]["media"] == 14.0
    assert r["vinherias"][1]["erro"] == "FIWARE indisponível: timeout"


async def test_alertas_filtra_janela_e_vinheria(tools, duas, alert_log, relogio):
    alert_log.open("vinheria001", "temperature", 21.0, relogio.iso(segundos_atras=3600))
    antigo = alert_log.open("vinheria002", "humidity", 80.0, relogio.iso(segundos_atras=30 * 3600))
    alert_log.close(antigo.id, relogio.iso(segundos_atras=29 * 3600))
    alert_log.open("fiware", "offline", None, relogio.iso(segundos_atras=600))
    todos = await tools.executar("alertas", {}, [])
    assert [a["device_id"] for a in todos["alertas"]] == ["fiware", "vinheria001"]
    assert todos["alertas"][1]["aberto"] is True
    so_001 = await tools.executar("alertas", {"vinheria": "São Paulo"}, [])
    assert [a["device_id"] for a in so_001["alertas"]] == ["vinheria001"]
