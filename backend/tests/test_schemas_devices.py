"""Testes dos schemas de cadastro (spec R1.1)."""
import pytest
from pydantic import ValidationError

from app.models.schemas import Device, DeviceCreate


def test_device_create_aceita_valido():
    dados = DeviceCreate(device_id="vinheria001", name="  Vinheria Paulista ", city=" São Paulo ")
    assert dados.device_id == "vinheria001"
    assert dados.name == "Vinheria Paulista"
    assert dados.city == "São Paulo"


@pytest.mark.parametrize("device_id", ["vinheria1", "Vinheria001", "vinheria0001", "adega001"])
def test_device_create_rejeita_id_fora_do_formato(device_id):
    with pytest.raises(ValidationError):
        DeviceCreate(device_id=device_id, name="Vinheria", city="Cidade")


@pytest.mark.parametrize("campos", [
    {"name": ""},
    {"name": "   "},
    {"name": "x" * 61},
    {"city": "x" * 61},
])
def test_device_create_rejeita_nome_ou_cidade_vazios_ou_longos(campos):
    dados = {"device_id": "vinheria001", "name": "Vinheria", "city": "Cidade", **campos}
    with pytest.raises(ValidationError):
        DeviceCreate(**dados)


def test_device_compativel_sem_created_at():
    device = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                    name="Vinheria", city="Cidade")
    assert device.created_at is None
