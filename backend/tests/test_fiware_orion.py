"""Testes do FiwareClient contra o Orion: escrita e remoção (spec R7)."""
import json

import httpx
import pytest
import respx

pytestmark = pytest.mark.anyio

ORION = "http://10.0.0.1:1026"
E1 = "urn:ngsi-ld:Vinheria:001"
E2 = "urn:ngsi-ld:Vinheria:002"


def _corpo(rota):
    """JSON enviado na última chamada da rota."""
    return json.loads(rota.calls.last.request.content)


@respx.mock
async def test_subscribe_attr_envia_body_e_devolve_id(fiware):
    rota = respx.post(f"{ORION}/v2/subscriptions").mock(
        return_value=httpx.Response(201, headers={"Location": "/v2/subscriptions/abc123"}))
    assert await fiware.subscribe_attr(E1, "temperature") == "abc123"
    corpo = _corpo(rota)
    assert corpo["subject"] == {
        "entities": [{"id": E1, "type": "Vinheria"}],
        "condition": {"attrs": ["temperature"]},
    }
    assert corpo["notification"] == {
        "http": {"url": "http://sth-comet:8666/notify"},
        "attrs": ["temperature"],
        "attrsFormat": "legacy",
    }


async def test_subscribe_attr_rejeita_atributo_invalido(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.subscribe_attr(E1, "t")
    assert mock.calls.call_count == 0


@respx.mock
async def test_send_command_envia_patch(fiware):
    rota = respx.patch(f"{ORION}/v2/entities/{E2}/attrs").mock(return_value=httpx.Response(204))
    await fiware.send_command(E2, "blink_temp")
    assert _corpo(rota) == {"blink_temp": {"type": "command", "value": ""}}


@respx.mock
async def test_send_command_set_limits_com_valor(fiware):
    rota = respx.patch(f"{ORION}/v2/entities/{E1}/attrs").mock(return_value=httpx.Response(204))
    await fiware.send_command(E1, "set_limits", "12;18;50;70;0;30")
    assert _corpo(rota) == {"set_limits": {"type": "command", "value": "12;18;50;70;0;30"}}


async def test_send_command_rejeita_comando_invalido(fiware):
    with respx.mock() as mock:
        with pytest.raises(ValueError):
            await fiware.send_command(E1, "explodir")
    assert mock.calls.call_count == 0


@respx.mock
async def test_update_attrs_usa_op_update_append(fiware):
    rota = respx.post(f"{ORION}/v2/op/update").mock(return_value=httpx.Response(204))
    await fiware.update_attrs(E1, {"temp_min": 12, "temp_max": 18.5})
    assert _corpo(rota) == {"actionType": "append", "entities": [{
        "id": E1, "type": "Vinheria",
        "temp_min": {"type": "Number", "value": 12},
        "temp_max": {"type": "Number", "value": 18.5},
    }]}


@respx.mock
async def test_delete_entity_remove(fiware):
    rota = respx.delete(f"{ORION}/v2/entities/{E1}").mock(return_value=httpx.Response(204))
    await fiware.delete_entity(E1)
    assert rota.called


@respx.mock
async def test_delete_entity_aceita_404(fiware):
    rota = respx.delete(f"{ORION}/v2/entities/{E1}").mock(return_value=httpx.Response(404))
    await fiware.delete_entity(E1)
    assert rota.called


@respx.mock
async def test_delete_subscriptions_apaga_so_as_da_entidade(fiware):
    assinaturas = [
        {"id": "s1", "subject": {"entities": [{"id": E1, "type": "Vinheria"}]}},
        {"id": "s2", "subject": {"entities": [{"id": E2, "type": "Vinheria"}]}},
        {"id": "s3", "subject": {"entities": [{"id": E1, "type": "Vinheria"}]}},
        {"id": "s4", "subject": {"entities": [{"idPattern": ".*"}]}},
    ]
    listagem = respx.get(f"{ORION}/v2/subscriptions").mock(
        return_value=httpx.Response(200, json=assinaturas))
    apaga_s1 = respx.delete(f"{ORION}/v2/subscriptions/s1").mock(return_value=httpx.Response(204))
    apaga_s3 = respx.delete(f"{ORION}/v2/subscriptions/s3").mock(return_value=httpx.Response(204))
    assert await fiware.delete_subscriptions(E1) == 2
    assert apaga_s1.called and apaga_s3.called
    assert listagem.calls.last.request.url.params["limit"] == "1000"
