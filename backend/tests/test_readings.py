"""Testes das leituras: estado atual, histórico normalizado e score (spec R3.3, R8)."""
import httpx
import pytest
import respx
from pydantic import ValidationError

from app.models.schemas import HistoryQuery
from app.services.registry_errors import DeviceNotFound

pytestmark = pytest.mark.anyio

ORION = "http://10.0.0.1:1026"
STH = "http://10.0.0.1:8666"
E1 = "urn:ngsi-ld:Vinheria:001"
ENTIDADE_URL = f"{ORION}/v2/entities/{E1}"


def _sth_url(attr="temperature"):
    return f"{STH}/STH/v1/contextEntities/type/Vinheria/id/{E1}/attributes/{attr}"


def _resposta_sth(valores, attr="temperature"):
    """Resposta no formato do STH-Comet com os valores dados."""
    return {"contextResponses": [{
        "contextElement": {"attributes": [{"name": attr, "values": valores}],
                           "id": E1, "isPattern": False, "type": "Vinheria"},
        "statusCode": {"code": "200", "reasonPhrase": "OK"},
    }]}


def _entidade(**attrs):
    """Entidade em keyValues como o Orion devolve, com atributos de comando junto."""
    return {"id": E1, "type": "Vinheria", "blink_temp": "", "set_limits": "", **attrs}


@respx.mock
async def test_current_converte_valores(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(
        temperature=14.2, humidity="55.5", luminosity=12,
        TimeInstant="2026-10-07T21:00:00.000Z")))
    leitura = await readings.current("vinheria001")
    assert (leitura.temperature, leitura.humidity, leitura.luminosity) == (14.2, 55.5, 12.0)
    assert leitura.time_instant == "2026-10-07T21:00:00.000Z"


@respx.mock
async def test_current_sem_atributos_de_sensor(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade()))
    leitura = await readings.current("vinheria001")
    assert (leitura.temperature, leitura.humidity, leitura.luminosity) == (None, None, None)
    assert leitura.time_instant is None


@pytest.mark.parametrize("valor", ["", " ", True, "abc", "NaN"])
@respx.mock
async def test_current_valor_invalido_vira_nulo(readings, cadastrar, valor):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(
        temperature=valor, humidity=60, luminosity=10)))
    leitura = await readings.current("vinheria001")
    assert leitura.temperature is None
    assert leitura.humidity == 60


@respx.mock
async def test_current_entidade_inexistente_devolve_nulos(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(404, json={"error": "NotFound"}))
    leitura = await readings.current("vinheria001")
    assert leitura.device_id == "vinheria001"
    assert (leitura.temperature, leitura.humidity, leitura.luminosity) == (None, None, None)


@respx.mock
async def test_history_normaliza_pontos(readings, cadastrar):
    cadastrar("001")
    rota = respx.get(_sth_url()).mock(return_value=httpx.Response(200, json=_resposta_sth([
        {"recvTime": "2026-10-07T21:00:00.000Z", "attrType": "Float", "attrValue": "14.2"},
        {"recvTime": "2026-10-07T21:00:02.000Z", "attrType": "Float", "attrValue": 14.3},
    ])))
    pontos = await readings.history("vinheria001", HistoryQuery(attr="temperature", last_n=20))
    assert [p.model_dump() for p in pontos] == [
        {"ts": "2026-10-07T21:00:00.000Z", "value": 14.2},
        {"ts": "2026-10-07T21:00:02.000Z", "value": 14.3},
    ]
    assert rota.calls.last.request.url.params["lastN"] == "20"


@respx.mock
async def test_history_descarta_nao_numericos(readings, cadastrar):
    cadastrar("001")
    respx.get(_sth_url()).mock(return_value=httpx.Response(200, json=_resposta_sth([
        {"recvTime": "2026-10-07T21:00:00.000Z", "attrValue": " "},
        {"recvTime": "2026-10-07T21:00:02.000Z", "attrValue": "14.3"},
    ])))
    pontos = await readings.history("vinheria001", HistoryQuery(attr="temperature", last_n=20))
    assert [p.value for p in pontos] == [14.3]


@respx.mock
async def test_history_repassa_janela_de_datas(readings, cadastrar):
    cadastrar("001")
    rota = respx.get(_sth_url("humidity")).mock(
        return_value=httpx.Response(200, json=_resposta_sth([], "humidity")))
    consulta = HistoryQuery(attr="humidity", date_from="2026-10-07T00:00:00",
                            date_to="2026-10-07T23:59:59")
    assert await readings.history("vinheria001", consulta) == []
    params = rota.calls.last.request.url.params
    assert params["dateFrom"] == "2026-10-07T00:00:00"
    assert params["dateTo"] == "2026-10-07T23:59:59"


@respx.mock
async def test_score_usa_faixa_da_vinheria(readings, cadastrar, conn):
    cadastrar("001")
    with conn:
        conn.execute("UPDATE triggers SET min_value = 18, max_value = 25 "
                     "WHERE device_id = 'vinheria001' AND attr = 'temperature'")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(
        temperature=20, humidity=60, luminosity=10)))
    relatorio = await readings.score("vinheria001")
    assert relatorio.score == 100
    assert relatorio.available is True
    assert relatorio.message is None
    assert (relatorio.limits.temperature.min, relatorio.limits.temperature.max) == (18, 25)


@respx.mock
async def test_score_indisponivel_no_report(readings, cadastrar):
    cadastrar("001")
    respx.get(ENTIDADE_URL).mock(return_value=httpx.Response(200, json=_entidade(temperature=15)))
    relatorio = await readings.score("vinheria001")
    assert relatorio.score is None
    assert relatorio.available is False
    assert relatorio.message == "Score indisponível: aguardando leitura de umidade e luminosidade"
    assert relatorio.attrs.temperature == 100


async def test_readings_device_inexistente_sem_rede(readings):
    with respx.mock() as mock:
        with pytest.raises(DeviceNotFound):
            await readings.current("vinheria009")
        with pytest.raises(DeviceNotFound):
            await readings.history("vinheria009", HistoryQuery(attr="temperature", last_n=5))
        with pytest.raises(DeviceNotFound):
            await readings.score("vinheria009")
    assert mock.calls.call_count == 0


@pytest.mark.parametrize("campos", [
    {"attr": "temperature"},
    {"attr": "temperature", "last_n": 10, "date_from": "2026-10-07T00:00:00"},
])
def test_history_query_exige_um_modo(campos):
    with pytest.raises(ValidationError):
        HistoryQuery(**campos)


def test_history_query_valida_data():
    with pytest.raises(ValidationError):
        HistoryQuery(attr="temperature", date_from="ontem")
