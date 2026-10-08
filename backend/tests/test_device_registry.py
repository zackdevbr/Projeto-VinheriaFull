"""Testes do cadastro com provisionamento, listagem e consulta (spec R1.2, R4, R5)."""
import json
from datetime import datetime

import httpx
import pytest
import respx

from app.models.schemas import DeviceCreate
from app.services.device_registry import entity_id_for
from app.services.fiware_errors import FiwareError
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import DeviceAlreadyExists, DeviceNotFound

pytestmark = pytest.mark.anyio

IOTA = "http://10.0.0.1:4041"
ORION = "http://10.0.0.1:1026"
E1 = "urn:ngsi-ld:Vinheria:001"
NOVA = DeviceCreate(device_id="vinheria001", name="Vinheria Paulista", city="São Paulo")
CRIADA = httpx.Response(201, headers={"Location": "/v2/subscriptions/abc"})


def _mock_cadastro(numero="001", device_existente=False, subscricao=None, faixa=None):
    """Registra no respx todas as rotas do cadastro de uma vinheria.

    `subscricao` e `faixa` permitem trocar a resposta (ou side_effect) do
    POST de subscriptions e do POST da faixa no Orion.
    """
    respx.post(f"{IOTA}/iot/services").mock(return_value=httpx.Response(201))
    respx.delete(f"{IOTA}/iot/devices/vinheria{numero}").mock(
        return_value=httpx.Response(204 if device_existente else 404))
    respx.post(f"{IOTA}/iot/devices").mock(return_value=httpx.Response(201))
    respx.get(f"{ORION}/v2/subscriptions").mock(return_value=httpx.Response(200, json=[]))
    rota_sub = respx.post(f"{ORION}/v2/subscriptions")
    if subscricao is None:
        rota_sub.mock(return_value=CRIADA)
    else:
        rota_sub.mock(side_effect=subscricao)
    rota_faixa = respx.post(f"{ORION}/v2/op/update")
    if faixa is None:
        rota_faixa.mock(return_value=httpx.Response(204))
    else:
        rota_faixa.mock(side_effect=faixa)


def _chamadas():
    """(método, caminho) de todas as chamadas interceptadas, em ordem."""
    return [(c.request.method, c.request.url.path) for c in respx.calls]


def _conta(conn, tabela):
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_entity_id_for_deriva_urn():
    assert entity_id_for("vinheria001") == "urn:ngsi-ld:Vinheria:001"
    assert entity_id_for("vinheria042") == "urn:ngsi-ld:Vinheria:042"


async def test_create_id_ja_cadastrado_levanta_conflito_sem_rede(registry, cadastrar):
    cadastrar("001")
    with respx.mock() as mock:
        with pytest.raises(DeviceAlreadyExists):
            await registry.create(NOVA)
    assert mock.calls.call_count == 0


@respx.mock
async def test_create_sequencia_completa_no_fiware(registry):
    _mock_cadastro()
    await registry.create(NOVA)
    assert _chamadas() == [
        ("POST", "/iot/services"),
        ("DELETE", "/iot/devices/vinheria001"),
        ("POST", "/iot/devices"),
        ("GET", "/v2/subscriptions"),
        ("POST", "/v2/subscriptions"),
        ("POST", "/v2/subscriptions"),
        ("POST", "/v2/subscriptions"),
        ("POST", "/v2/op/update"),
    ]
    assinados = [
        json.loads(c.request.content)["subject"]["condition"]["attrs"][0]
        for c in respx.calls
        if c.request.method == "POST" and c.request.url.path == "/v2/subscriptions"
    ]
    assert assinados == ["temperature", "humidity", "luminosity"]
    faixa = json.loads(respx.calls[-1].request.content)
    assert faixa == {"actionType": "append", "entities": [{
        "id": E1, "type": "Vinheria",
        "temp_min": {"type": "Number", "value": 12},
        "temp_max": {"type": "Number", "value": 18},
        "hum_min": {"type": "Number", "value": 50},
        "hum_max": {"type": "Number", "value": 70},
        "lux_min": {"type": "Number", "value": 0},
        "lux_max": {"type": "Number", "value": 30},
    }]}


@respx.mock
async def test_create_grava_device_e_faixa_padrao(registry, conn, limits):
    _mock_cadastro()
    device = await registry.create(NOVA)
    assert device.entity_id == E1
    assert registry.list() == [device]
    assert datetime.fromisoformat(device.created_at).tzinfo is not None
    assert _conta(conn, "triggers") == 3
    assert limits.get("vinheria001") == DEFAULT_LIMITS


@respx.mock
async def test_create_falha_no_fiware_nao_grava_nada(registry, conn):
    _mock_cadastro(subscricao=[httpx.Response(500, text="falhou")])
    with pytest.raises(FiwareError):
        await registry.create(NOVA)
    assert registry.list() == []
    assert _conta(conn, "triggers") == 0


@respx.mock
async def test_create_repetido_apos_falha_funciona(registry):
    _mock_cadastro(subscricao=[httpx.Response(500, text="falhou"), CRIADA, CRIADA, CRIADA])
    with pytest.raises(FiwareError):
        await registry.create(NOVA)
    device = await registry.create(NOVA)
    assert registry.list() == [device]


@respx.mock
async def test_create_reprovisiona_device_existente(registry):
    _mock_cadastro(device_existente=True)
    await registry.create(NOVA)
    chamadas = _chamadas()
    remocao = chamadas.index(("DELETE", "/iot/devices/vinheria001"))
    provisionamento = chamadas.index(("POST", "/iot/devices"))
    assert remocao < provisionamento
    comandos = [
        c["name"]
        for c in json.loads(respx.calls[provisionamento].request.content)["devices"][0]["commands"]
    ]
    assert "set_limits" in comandos


@respx.mock
async def test_create_dois_devices_duas_sequencias(registry):
    _mock_cadastro("001")
    _mock_cadastro("002")
    await registry.create(NOVA)
    await registry.create(DeviceCreate(device_id="vinheria002", name="Adega Carioca",
                                       city="Rio de Janeiro"))
    assert _chamadas().count(("POST", "/iot/devices")) == 2
    assert _chamadas().count(("POST", "/v2/subscriptions")) == 6
    assert [d.device_id for d in registry.list()] == ["vinheria001", "vinheria002"]


@respx.mock
async def test_create_corrida_vira_conflito(registry, conn):
    def _outro_cadastro_chega_antes(request):
        """Simula outro cadastro do mesmo id gravando no SQLite no meio do nosso."""
        with conn:
            conn.execute(
                "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
                "VALUES ('vinheria001', ?, 'Outra', 'Outra', '2026-10-07T21:00:00+00:00')",
                (E1,),
            )
        return httpx.Response(204)

    _mock_cadastro(faixa=_outro_cadastro_chega_antes)
    with pytest.raises(DeviceAlreadyExists):
        await registry.create(NOVA)


def test_list_ordenado_por_id(registry, cadastrar):
    cadastrar("003", "Cave Campinas", "Campinas")
    cadastrar("001")
    assert [d.device_id for d in registry.list()] == ["vinheria001", "vinheria003"]


def test_get_inexistente_levanta_not_found(registry):
    with pytest.raises(DeviceNotFound):
        registry.get("vinheria009")


def test_detail_inclui_faixa(registry, cadastrar):
    cadastrar("001")
    detalhe = registry.detail("vinheria001")
    assert detalhe.name == "Vinheria Paulista"
    assert detalhe.limits == DEFAULT_LIMITS
