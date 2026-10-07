"""Testes do FiwareClient contra o IoT Agent (spec R6)."""
import json

import httpx
import pytest
import respx

from app.models.schemas import Device
from app.services.fiware_errors import FiwareConflict

pytestmark = pytest.mark.anyio

IOTA = "http://10.0.0.1:4041"
DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria São Paulo", city="São Paulo")


def _corpo(rota):
    """JSON enviado na última chamada da rota."""
    return json.loads(rota.calls.last.request.content)


@respx.mock
async def test_provision_service_group_envia_body(fiware):
    rota = respx.post(f"{IOTA}/iot/services").mock(return_value=httpx.Response(201))
    await fiware.provision_service_group()
    assert _corpo(rota) == {"services": [{
        "apikey": "TEF",
        "cbroker": "http://10.0.0.1:1026",
        "entity_type": "Thing",
        "resource": "",
        "timestamp": True,
    }]}


@respx.mock
async def test_provision_service_group_aceita_409(fiware):
    respx.post(f"{IOTA}/iot/services").mock(
        return_value=httpx.Response(409, json={"name": "DUPLICATE_GROUP"}))
    await fiware.provision_service_group()


@respx.mock
async def test_provision_device_envia_body(fiware):
    rota = respx.post(f"{IOTA}/iot/devices").mock(return_value=httpx.Response(201))
    await fiware.provision_device(DEVICE)
    device = _corpo(rota)["devices"][0]
    assert device["device_id"] == "vinheria001"
    assert device["entity_name"] == "urn:ngsi-ld:Vinheria:001"
    assert device["entity_type"] == "Vinheria"
    assert device["protocol"] == "PDI-IoTA-UltraLight"
    assert device["transport"] == "MQTT"
    assert device["commands"] == [
        {"name": "blink_temp", "type": "command"},
        {"name": "blink_hum", "type": "command"},
        {"name": "blink_lux", "type": "command"},
        {"name": "alert_off", "type": "command"},
        {"name": "set_limits", "type": "command"},
    ]
    assert device["attributes"] == [
        {"object_id": "t", "name": "temperature", "type": "Float"},
        {"object_id": "h", "name": "humidity", "type": "Float"},
        {"object_id": "l", "name": "luminosity", "type": "Integer"},
    ]


@respx.mock
async def test_provision_device_duplicado_levanta_conflict(fiware):
    respx.post(f"{IOTA}/iot/devices").mock(
        return_value=httpx.Response(409, json={"name": "DUPLICATE_DEVICE_ID"}))
    with pytest.raises(FiwareConflict) as erro:
        await fiware.provision_device(DEVICE)
    assert erro.value.service == "iota"


@respx.mock
async def test_delete_device_remove(fiware):
    rota = respx.delete(f"{IOTA}/iot/devices/vinheria001").mock(return_value=httpx.Response(204))
    await fiware.delete_device("vinheria001")
    assert rota.called


@respx.mock
async def test_delete_device_aceita_404(fiware):
    rota = respx.delete(f"{IOTA}/iot/devices/vinheria001").mock(return_value=httpx.Response(404))
    await fiware.delete_device("vinheria001")
    assert rota.called
