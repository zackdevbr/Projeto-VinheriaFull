"""Testes da base do FiwareClient: URLs, headers, erros, leituras e saúde.

Cobre a spec R4, R5.1, R5.2, R7.2, R7.3 e R9. Nenhum teste acessa a rede:
o respx intercepta as requisições do httpx.
"""
import httpx
import pytest
import respx

from app.models.schemas import ConfigUpdate
from app.services.fiware_errors import FiwareError, FiwareNotFound, FiwareUnavailable

pytestmark = pytest.mark.anyio

ORION = "http://10.0.0.1:1026"
IOTA = "http://10.0.0.1:4041"
STH = "http://10.0.0.1:8666"
ENTIDADE = "urn:ngsi-ld:Vinheria:001"


def test_urls_usam_config_atual(fiware, store):
    assert fiware.orion_url("/v2/entities") == f"{ORION}/v2/entities"
    assert fiware.iota_url("/iot/devices") == f"{IOTA}/iot/devices"
    assert fiware.sth_url("/version") == f"{STH}/version"
    store.update(ConfigUpdate(ec2_ip="20.0.0.2", orion_port=2026))
    assert fiware.orion_url("/v2/entities") == "http://20.0.0.2:2026/v2/entities"
    assert fiware.iota_url("/iot/devices") == "http://20.0.0.2:4041/iot/devices"


def test_sem_ip_configurado_levanta_unavailable(fiware_sem_ip):
    with pytest.raises(FiwareUnavailable) as erro:
        fiware_sem_ip.orion_url("/version")
    assert "FIWARE_HOST" in erro.value.message


@respx.mock
async def test_requests_levam_headers_fiware(fiware):
    rota = respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(
        return_value=httpx.Response(200, json={"id": ENTIDADE}))
    await fiware.get_entity(ENTIDADE)
    headers = rota.calls.last.request.headers
    assert headers["fiware-service"] == "smart"
    assert headers["fiware-servicepath"] == "/"


@respx.mock
async def test_get_entity_usa_key_values(fiware):
    entidade = {"id": ENTIDADE, "type": "Vinheria", "temperature": 14.2}
    rota = respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(
        return_value=httpx.Response(200, json=entidade))
    assert await fiware.get_entity(ENTIDADE) == entidade
    assert rota.calls.last.request.url.params["options"] == "keyValues"


@respx.mock
async def test_get_entity_inexistente_levanta_not_found(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(
        return_value=httpx.Response(404, json={"error": "NotFound"}))
    with pytest.raises(FiwareNotFound) as erro:
        await fiware.get_entity(ENTIDADE)
    assert erro.value.status_code == 404
    assert erro.value.service == "orion"


@respx.mock
async def test_list_entities_uma_chamada(fiware):
    frota = [
        {"id": ENTIDADE, "type": "Vinheria", "TimeInstant": "2026-10-05T22:00:00.000Z"},
        {"id": "urn:ngsi-ld:Vinheria:002", "type": "Vinheria"},
    ]
    rota = respx.get(f"{ORION}/v2/entities").mock(return_value=httpx.Response(200, json=frota))
    resultado = await fiware.list_entities()
    assert [e["id"] for e in resultado] == [ENTIDADE, "urn:ngsi-ld:Vinheria:002"]
    assert resultado[0]["TimeInstant"] == "2026-10-05T22:00:00.000Z"
    assert rota.call_count == 1
    params = rota.calls.last.request.url.params
    assert params["type"] == "Vinheria"
    assert params["options"] == "keyValues"
    assert params["limit"] == "1000"


@respx.mock
async def test_timeout_vira_unavailable(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(side_effect=httpx.ConnectTimeout("tempo"))
    with pytest.raises(FiwareUnavailable) as erro:
        await fiware.get_entity(ENTIDADE)
    assert erro.value.service == "orion"


@respx.mock
async def test_conexao_recusada_vira_unavailable(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(side_effect=httpx.ConnectError("recusada"))
    with pytest.raises(FiwareUnavailable):
        await fiware.get_entity(ENTIDADE)


@respx.mock
async def test_status_500_vira_fiware_error(fiware):
    respx.get(f"{ORION}/v2/entities/{ENTIDADE}").mock(return_value=httpx.Response(500, text="falhou"))
    with pytest.raises(FiwareError) as erro:
        await fiware.get_entity(ENTIDADE)
    assert erro.value.status_code == 500
    assert not isinstance(erro.value, FiwareUnavailable)


def _mock_saude(iota=None):
    """Registra no respx as três rotas de saúde; `iota` pode trocar a do IoT Agent."""
    respx.get(f"{ORION}/version").mock(return_value=httpx.Response(200, json={}))
    rota_iota = respx.get(f"{IOTA}/iot/about")
    if iota is None:
        rota_iota.mock(return_value=httpx.Response(200, json={}))
    else:
        rota_iota.mock(side_effect=iota)
    respx.get(f"{STH}/version").mock(return_value=httpx.Response(200, json={}))


@respx.mock
async def test_health_tudo_ok(fiware):
    _mock_saude()
    relatorio = await fiware.health()
    assert relatorio.ok is True
    assert relatorio.ec2_ip == "10.0.0.1"
    assert relatorio.orion.ok and relatorio.iota.ok and relatorio.sth.ok
    assert relatorio.orion.status_code == 200
    assert relatorio.orion.latency_ms is not None


@respx.mock
async def test_health_um_servico_fora(fiware):
    _mock_saude(iota=httpx.ConnectError("recusada"))
    relatorio = await fiware.health()
    assert relatorio.ok is False
    assert relatorio.orion.ok and relatorio.sth.ok
    assert relatorio.iota.ok is False
    assert relatorio.iota.error


async def test_health_sem_ip(fiware_sem_ip):
    with respx.mock() as mock:
        relatorio = await fiware_sem_ip.health()
    assert mock.calls.call_count == 0
    assert relatorio.ok is False
    assert relatorio.ec2_ip == ""
    for servico in (relatorio.orion, relatorio.iota, relatorio.sth):
        assert servico.ok is False
        assert "FIWARE_HOST" in servico.error
