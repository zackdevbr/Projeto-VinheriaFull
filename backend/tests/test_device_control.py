"""Testes do controle da vinheria: faixa na hora e comandos manuais (spec R11)."""
import pytest

from app.models.schemas import AttrLimits, Limits
from app.services.device_control import DeviceControl
from app.services.fiware_errors import FiwareUnavailable
from app.services.limits import DEFAULT_LIMITS
from app.services.registry_errors import DeviceNotFound, DeviceUnavailable
from tests.fakes import status_vinheria

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
NOVA = Limits(temperature=AttrLimits(min=10, max=16),
              humidity=AttrLimits(min=55, max=75),
              luminosity=AttrLimits(min=0, max=20))
T0 = "2026-10-08T12:00:00+00:00"


class MotorFalso:
    """Registra os pedidos de set_limits pendente."""

    def __init__(self):
        self.pendentes = []

    def mark_limits_pending(self, device_id):
        self.pendentes.append(device_id)


@pytest.fixture
def motor_falso():
    return MotorFalso()


@pytest.fixture
def control(registry, limits, fiware_falso, fleet, motor_falso):
    return DeviceControl(registry, limits, fiware_falso, fleet, motor_falso)


async def test_update_limits_publica_grava_e_envia_na_hora(control, cadastrar, fiware_falso,
                                                           limits, motor_falso):
    cadastrar("001")
    resultado = await control.update_limits("vinheria001", NOVA)
    assert (resultado.device_id, resultado.limits, resultado.device_sync) == (
        "vinheria001", NOVA, "enviado")
    assert fiware_falso.atualizacoes == [(E1, {"temp_min": 10, "temp_max": 16,
                                               "hum_min": 55, "hum_max": 75,
                                               "lux_min": 0, "lux_max": 20})]
    assert fiware_falso.comandos == [(E1, "set_limits", "10,16,55,75,0,20")]
    assert limits.get("vinheria001") == NOVA
    assert motor_falso.pendentes == []


async def test_update_limits_offline_fica_pendente(control, cadastrar, fiware_falso, fleet,
                                                   limits, motor_falso):
    cadastrar("001")
    fleet.replace([status_vinheria("vinheria001", "offline")], T0)
    resultado = await control.update_limits("vinheria001", NOVA)
    assert resultado.device_sync == "pendente"
    assert fiware_falso.comandos == []
    assert limits.get("vinheria001") == NOVA
    assert motor_falso.pendentes == ["vinheria001"]


async def test_update_limits_falha_no_envio_fica_pendente(control, cadastrar, fiware_falso,
                                                          limits, motor_falso):
    cadastrar("001")
    fiware_falso.erro_comando = FiwareUnavailable("orion", "sem conexão")
    resultado = await control.update_limits("vinheria001", NOVA)
    assert resultado.device_sync == "pendente"
    assert limits.get("vinheria001") == NOVA
    assert motor_falso.pendentes == ["vinheria001"]


async def test_update_limits_fiware_fora_nao_grava(control, cadastrar, fiware_falso, limits,
                                                   motor_falso):
    cadastrar("001")
    fiware_falso.erro_update = FiwareUnavailable("orion", "sem conexão")
    with pytest.raises(FiwareUnavailable):
        await control.update_limits("vinheria001", NOVA)
    assert limits.get("vinheria001") == DEFAULT_LIMITS
    assert fiware_falso.comandos == []
    assert motor_falso.pendentes == []


async def test_update_limits_inexistente_sem_rede(control, fiware_falso):
    with pytest.raises(DeviceNotFound):
        await control.update_limits("vinheria009", NOVA)
    assert fiware_falso.atualizacoes == []


def test_get_limits(control, cadastrar):
    cadastrar("001")
    assert control.get_limits("vinheria001") == DEFAULT_LIMITS


def test_get_limits_inexistente(control):
    with pytest.raises(DeviceNotFound):
        control.get_limits("vinheria009")


async def test_send_command_envia(control, cadastrar, fiware_falso):
    cadastrar("001")
    await control.send_command("vinheria001", "blink_hum")
    assert fiware_falso.comandos == [(E1, "blink_hum", "")]


async def test_send_command_offline_recusa(control, cadastrar, fiware_falso, fleet):
    cadastrar("001")
    fleet.replace([status_vinheria("vinheria001", "offline")], T0)
    with pytest.raises(DeviceUnavailable, match="offline"):
        await control.send_command("vinheria001", "blink_temp")
    assert fiware_falso.comandos == []


async def test_send_command_configurando_recusa(control, cadastrar, fiware_falso, fleet):
    cadastrar("001")
    fleet.replace([status_vinheria("vinheria001", "configurando")], T0)
    with pytest.raises(DeviceUnavailable, match="faixa"):
        await control.send_command("vinheria001", "blink_temp")
    assert fiware_falso.comandos == []


async def test_send_command_inexistente_sem_rede(control, fiware_falso):
    with pytest.raises(DeviceNotFound):
        await control.send_command("vinheria009", "alert_off")
    assert fiware_falso.comandos == []
