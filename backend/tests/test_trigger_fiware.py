"""Testes do motor: EC2/FIWARE fora do ar (spec R10)."""
import pytest

from app.services.fiware_errors import FiwareUnavailable
from tests.fakes import entidade, instante_de

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
FORA = FiwareUnavailable("orion", "sem conexão")


def comandos(fiware, entity_id=E1):
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def derrubar_ec2(engine, fiware, relogio):
    """Primeira falha agora (12:00:00) e outra 31 s depois: EC2 fora."""
    fiware.erro_listar = FORA
    await engine.tick()
    relogio.avancar(31)
    await engine.tick()


async def test_falha_curta_do_fiware_mantem_retrato(engine, fiware_falso, cadastrar, alert_log,
                                                    fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    fiware_falso.comandos.clear()
    antes = fleet.snapshot()
    fiware_falso.erro_listar = FORA
    await engine.tick()
    relogio.avancar(20)
    await engine.tick()
    assert fleet.snapshot() == antes
    assert fleet.fiware_online is True
    assert alert_log.open_alerts() == []
    assert fiware_falso.comandos == []


async def test_ec2_fora_marca_offline_com_um_alerta(engine, fiware_falso, cadastrar, alert_log,
                                                    fleet, relogio):
    cadastrar("001")
    cadastrar("002", name="Vinheria Mineira", city="Minas Gerais")
    fiware_falso.entidades = [entidade("001"), entidade("002")]
    await engine.tick()
    fiware_falso.comandos.clear()
    await derrubar_ec2(engine, fiware_falso, relogio)
    assert fleet.fiware_online is False
    assert fleet.fiware_offline_since == "2026-10-08T12:00:00+00:00"
    statuses = fleet.snapshot()
    assert [(s.status, s.offline_reason) for s in statuses] == [("offline", "fiware")] * 2
    assert statuses[0].current.temperature == 15.0  # último valor conhecido
    assert statuses[0].score is None
    abertos = alert_log.open_alerts()
    assert [(a.device_id, a.attr) for a in abertos] == [("fiware", "offline")]
    assert abertos[0].opened_at == "2026-10-08T12:00:00+00:00"
    assert fiware_falso.comandos == []


async def test_ec2_volta_fecha_alerta_e_ressincroniza(engine, fiware_falso, cadastrar,
                                                      alert_log, fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    fiware_falso.comandos.clear()
    await derrubar_ec2(engine, fiware_falso, relogio)
    fiware_falso.erro_listar = None
    fiware_falso.entidades = [entidade("001", instante=instante_de(relogio, 1))]
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert alert_log.list(device_id="fiware")[0].duration_seconds == 31
    assert fleet.fiware_online is True
    assert fleet.status_of("vinheria001") == "ok"
    assert comandos(fiware_falso) == ["set_limits", "alert_off"]


async def test_leitura_velha_logo_apos_a_volta_nao_abre_offline(engine, fiware_falso,
                                                                cadastrar, alert_log, fleet,
                                                                relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]  # leitura de 11:59:58
    await engine.tick()
    await derrubar_ec2(engine, fiware_falso, relogio)
    fiware_falso.erro_listar = None  # EC2 voltou, mas o ESP32 ainda não publicou
    await engine.tick()
    [status] = fleet.snapshot()
    assert (status.status, status.offline_reason) == ("offline", "sem_leitura")
    assert alert_log.open_alerts() == []
    relogio.avancar(31)  # passou a carência e a leitura não veio
    await engine.tick()
    assert [(a.device_id, a.attr) for a in alert_log.open_alerts()] == [
        ("vinheria001", "offline")]


async def test_alerta_da_ec2_retomado_apos_reinicio_fecha_quando_volta(engine, fiware_falso,
                                                                      cadastrar, alert_log,
                                                                      fleet):
    cadastrar("001")
    alert_log.open("fiware", "offline", None, "2026-10-08T11:50:00+00:00")
    fiware_falso.erro_listar = FORA
    await engine.tick()
    assert fleet.fiware_online is False  # segue fora desde 11:50
    assert fleet.fiware_offline_since == "2026-10-08T11:50:00+00:00"
    fiware_falso.erro_listar = None
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert fleet.fiware_online is True


async def test_alerta_da_ec2_fecha_mesmo_sem_nenhuma_vinheria_cadastrada(engine, fiware_falso,
                                                                         alert_log, fleet):
    alert_log.open("fiware", "offline", None, "2026-10-08T11:50:00+00:00")
    fiware_falso.erro_listar = FORA
    await engine.tick()
    assert fleet.fiware_online is False  # segue fora e o painel sabe, mesmo sem vinherias
    fiware_falso.erro_listar = None
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert fleet.fiware_online is True
