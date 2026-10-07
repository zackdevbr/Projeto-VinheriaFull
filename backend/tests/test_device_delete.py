"""Testes da remoção de vinheria (spec R6)."""
import httpx
import pytest
import respx

from app.services.fiware_errors import FiwareUnavailable
from app.services.registry_errors import DeviceNotFound

pytestmark = pytest.mark.anyio

IOTA = "http://10.0.0.1:4041"
ORION = "http://10.0.0.1:1026"
E1 = "urn:ngsi-ld:Vinheria:001"


def _mock_remocao(device_status=204, entity_status=404):
    """Rotas da remoção da vinheria001, com uma subscription dela (s1) e uma de outra (s2)."""
    assinaturas = [
        {"id": "s1", "subject": {"entities": [{"id": E1, "type": "Vinheria"}]}},
        {"id": "s2", "subject": {"entities": [{"id": "urn:ngsi-ld:Vinheria:002",
                                               "type": "Vinheria"}]}},
    ]
    respx.get(f"{ORION}/v2/subscriptions").mock(return_value=httpx.Response(200, json=assinaturas))
    respx.delete(f"{ORION}/v2/subscriptions/s1").mock(return_value=httpx.Response(204))
    respx.delete(f"{IOTA}/iot/devices/vinheria001").mock(
        return_value=httpx.Response(device_status))
    respx.delete(f"{ORION}/v2/entities/{E1}").mock(return_value=httpx.Response(entity_status))


def _conta(conn, tabela):
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


@respx.mock
async def test_delete_sequencia_e_remove_local(registry, cadastrar, conn):
    cadastrar("001")
    _mock_remocao()
    await registry.delete("vinheria001")
    assert [(c.request.method, c.request.url.path) for c in respx.calls] == [
        ("GET", "/v2/subscriptions"),
        ("DELETE", "/v2/subscriptions/s1"),
        ("DELETE", "/iot/devices/vinheria001"),
        ("DELETE", f"/v2/entities/{E1}"),
    ]
    assert registry.list() == []
    assert _conta(conn, "triggers") == 0


@respx.mock
async def test_delete_aceita_404_no_fiware(registry, cadastrar):
    cadastrar("001")
    _mock_remocao(device_status=404, entity_status=404)
    await registry.delete("vinheria001")
    assert registry.list() == []


@respx.mock
async def test_delete_mantem_alertas(registry, cadastrar, conn):
    cadastrar("001")
    with conn:
        conn.execute("INSERT INTO alerts (device_id, attr, value, opened_at) "
                     "VALUES ('vinheria001', 'temperature', 25.0, '2026-10-07T21:00:00+00:00')")
    _mock_remocao()
    await registry.delete("vinheria001")
    assert _conta(conn, "alerts") == 1


@respx.mock
async def test_delete_fiware_fora_mantem_cadastro(registry, cadastrar):
    device = cadastrar("001")
    respx.get(f"{ORION}/v2/subscriptions").mock(side_effect=httpx.ConnectError("recusada"))
    with pytest.raises(FiwareUnavailable):
        await registry.delete("vinheria001")
    assert registry.list() == [device]


async def test_delete_inexistente_levanta_not_found_sem_rede(registry):
    with respx.mock() as mock:
        with pytest.raises(DeviceNotFound):
            await registry.delete("vinheria009")
    assert mock.calls.call_count == 0
