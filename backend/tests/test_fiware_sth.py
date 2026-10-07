"""Testes do FiwareClient contra o STH-Comet (spec R8)."""
import httpx
import pytest
import respx

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
URL = ("http://10.0.0.1:8666/STH/v1/contextEntities/type/Vinheria"
       f"/id/{E1}/attributes/temperature")
VALORES = [
    {"recvTime": "2026-10-05T22:00:00.000Z", "attrType": "Float", "attrValue": "14.2"},
    {"recvTime": "2026-10-05T22:00:02.000Z", "attrType": "Float", "attrValue": "14.3"},
]


def _resposta_sth(valores):
    """Monta uma resposta no formato do STH-Comet com os valores dados."""
    return {"contextResponses": [{
        "contextElement": {
            "attributes": [{"name": "temperature", "values": valores}],
            "id": E1, "isPattern": False, "type": "Vinheria",
        },
        "statusCode": {"code": "200", "reasonPhrase": "OK"},
    }]}


@respx.mock
async def test_query_history_last_n(fiware):
    rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_resposta_sth(VALORES)))
    assert await fiware.query_history("Vinheria", E1, "temperature", last_n=30) == VALORES
    params = rota.calls.last.request.url.params
    assert params["lastN"] == "30"
    assert rota.calls.last.request.headers["fiware-service"] == "smart"


@respx.mock
async def test_query_history_por_datas(fiware):
    rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_resposta_sth(VALORES)))
    await fiware.query_history("Vinheria", E1, "temperature",
                               date_from="2026-10-05T00:00:00", date_to="2026-10-05T23:59:59")
    params = rota.calls.last.request.url.params
    assert params["dateFrom"] == "2026-10-05T00:00:00"
    assert params["dateTo"] == "2026-10-05T23:59:59"
    assert params["hLimit"] == "500"
    assert params["hOffset"] == "0"
    assert "lastN" not in params


async def test_query_history_sem_janela_falha(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.query_history("Vinheria", E1, "temperature")
    assert mock.calls.call_count == 0


async def test_query_history_dois_modos_falha(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.query_history("Vinheria", E1, "temperature",
                                       last_n=10, date_from="2026-10-05T00:00:00")
    assert mock.calls.call_count == 0


@respx.mock
async def test_query_history_sem_dados_devolve_lista_vazia(fiware):
    respx.get(URL).mock(return_value=httpx.Response(200, json=_resposta_sth([])))
    assert await fiware.query_history("Vinheria", E1, "temperature", last_n=30) == []


@respx.mock
async def test_query_history_resposta_sem_entidade_devolve_lista_vazia(fiware):
    respx.get(URL).mock(return_value=httpx.Response(200, json={"contextResponses": []}))
    assert await fiware.query_history("Vinheria", E1, "temperature", last_n=30) == []
