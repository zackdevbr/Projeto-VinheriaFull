# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes das tools de proposta do chatbot (spec R11): propõem, nunca executam."""
import pytest

from app.services.chat_acoes import ChatAcoes
from app.services.chat_tools import ChatTools
from tests.fakes import status_vinheria

pytestmark = pytest.mark.anyio


@pytest.fixture
def tools(registry, fleet, alert_log, limits, cadastrar, fiware_falso):
    cadastrar("001", "Vinheria Paulista", "São Paulo")
    cadastrar("002", "Vinheria Mineira", "Belo Horizonte")
    chat_tools = ChatTools(registry, None, fleet, alert_log, limits)
    ChatAcoes(registry, fleet, limits).registrar_em(chat_tools)
    return chat_tools


def com_status(fleet, relogio, device_id, status):
    fleet.replace([status_vinheria(device_id, status)], at=relogio.iso())


async def test_propor_comando(tools, fleet, relogio):
    com_status(fleet, relogio, "vinheria002", "ok")
    propostas = []
    r = await tools.executar("propor_comando", {"vinheria": "Mineira", "comando": "blink_lux"}, propostas)
    assert r["aguardando_confirmacao"] is True
    assert [(p.kind, p.device_id, p.command) for p in propostas] == [("command", "vinheria002", "blink_lux")]
    assert propostas[0].summary == "Piscar o alerta de luminosidade (blink_lux) na Vinheria Mineira"


@pytest.mark.parametrize("status", ["offline", "configurando"])
async def test_propor_comando_recusa_indisponivel(tools, fleet, relogio, status):
    com_status(fleet, relogio, "vinheria001", status)
    propostas = []
    r = await tools.executar("propor_comando", {"vinheria": "001", "comando": "alert_off"}, propostas)
    assert "erro" in r and propostas == []


async def test_propor_comando_invalido(tools):
    propostas = []
    r = await tools.executar("propor_comando", {"vinheria": "001", "comando": "set_limits"}, propostas)
    assert "comando inválido" in r["erro"] and propostas == []


async def test_propor_faixa_so_maximo(tools, limits):
    propostas = []
    r = await tools.executar("propor_faixa",
                             {"vinheria": "São Paulo", "atributo": "temperature", "maximo": 20}, propostas)
    assert r["aguardando_confirmacao"] is True
    proposta = propostas[0]
    assert proposta.kind == "limits"
    assert (proposta.limits.temperature.min, proposta.limits.temperature.max) == (12, 20)
    assert proposta.limits.humidity == limits.get("vinheria001").humidity
    assert proposta.summary == "Temperatura máx. 18 → 20 °C na Vinheria Paulista"
    assert limits.get("vinheria001").temperature.max == 18  # nada gravado


async def test_propor_faixa_min_e_max(tools):
    propostas = []
    await tools.executar("propor_faixa", {"vinheria": "002", "atributo": "humidity",
                                          "minimo": 45, "maximo": "75"}, propostas)
    assert propostas[0].summary == "Umidade mín. 50 → 45 %, máx. 70 → 75 % na Vinheria Mineira"


@pytest.mark.parametrize("args", [
    {"atributo": "temperature"},                          # sem minimo nem maximo
    {"atributo": "temperature", "minimo": 19},            # 19 >= máx atual 18
    {"atributo": "temperature", "maximo": "muito"},       # não numérico
    {"atributo": "pressao", "maximo": 3},                 # atributo inválido
])
async def test_propor_faixa_invalida(tools, args):
    propostas = []
    r = await tools.executar("propor_faixa", {"vinheria": "001", **args}, propostas)
    assert "erro" in r and propostas == []


async def test_propostas_nao_tocam_o_fiware(tools, fiware_falso, fleet, relogio):
    com_status(fleet, relogio, "vinheria001", "ok")
    await tools.executar("propor_comando", {"vinheria": "001", "comando": "blink_temp"}, [])
    await tools.executar("propor_faixa", {"vinheria": "001", "atributo": "luminosity", "maximo": 40}, [])
    assert fiware_falso.comandos == [] and fiware_falso.atualizacoes == []
