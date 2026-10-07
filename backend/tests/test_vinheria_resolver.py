"""Testes do resolver de vinheria por id, nome ou cidade (spec R7)."""
import pytest

from app.models.schemas import Device
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound
from app.services.vinheria_resolver import resolve_vinheria


def _device(numero, name, city):
    return Device(device_id=f"vinheria{numero}", entity_id=f"urn:ngsi-ld:Vinheria:{numero}",
                  name=name, city=city)


FROTA = [
    _device("001", "Vinheria Paulista", "São Paulo"),
    _device("002", "Adega Carioca", "Rio de Janeiro"),
    _device("003", "Cave Campinas", "Campinas"),
    _device("004", "Empório do Sul", "São Paulo do Sul"),
]


@pytest.mark.parametrize("texto", ["sao paulo", "SÃO  PAULO", "  são paulo "])
def test_resolve_ignora_acento_e_caixa(texto):
    assert resolve_vinheria(texto, FROTA).device_id == "vinheria001"


def test_resolve_por_id():
    assert resolve_vinheria("Vinheria002", FROTA).device_id == "vinheria002"


def test_resolve_por_cidade_exata():
    assert resolve_vinheria("Campinas", FROTA).device_id == "vinheria003"


def test_resolve_prefere_igualdade_a_trecho():
    # "são paulo do sul" contém "são paulo", mas a igualdade com a cidade da 001 vence
    assert resolve_vinheria("São Paulo", FROTA).device_id == "vinheria001"
    assert resolve_vinheria("são paulo do sul", FROTA).device_id == "vinheria004"


def test_resolve_por_trecho():
    # "carioca" aparece só no nome da 002; ("rio" casaria também "empório")
    assert resolve_vinheria("carioca", FROTA).device_id == "vinheria002"


def test_resolve_trecho_em_varias_e_ambiguo():
    with pytest.raises(AmbiguousVinheria) as erro:
        resolve_vinheria("rio", FROTA)
    assert [d.device_id for d in erro.value.options] == ["vinheria002", "vinheria004"]


def test_resolve_ambiguo():
    with pytest.raises(AmbiguousVinheria) as erro:
        resolve_vinheria("vinheria", FROTA)
    assert [d.device_id for d in erro.value.options] == [
        "vinheria001", "vinheria002", "vinheria003", "vinheria004"]


def test_resolve_nao_encontrado():
    with pytest.raises(VinheriaNotFound):
        resolve_vinheria("Recife", FROTA)


@pytest.mark.parametrize("texto", ["", "   "])
def test_resolve_texto_vazio(texto):
    with pytest.raises(VinheriaNotFound):
        resolve_vinheria(texto, FROTA)
