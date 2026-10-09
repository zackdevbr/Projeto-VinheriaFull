"""Testes do motor: vinheria offline, retomada, órfãos e falhas (spec R9)."""
import pytest

from app.services.fiware_errors import FiwareUnavailable
from app.services.trigger_engine import TriggerEngine
from tests.fakes import entidade, instante_de

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"


class _Parar(BaseException):
    """Interrompe o laço do run() no teste (não é capturada como Exception)."""


def comandos(fiware, entity_id=E1):
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def primeira_passada(engine, fiware):
    await engine.tick()
    fiware.comandos.clear()


async def test_sem_leitura_ha_mais_de_offline_seconds_abre_alerta_offline_sem_comando(
        engine, fiware_falso, cadastrar, alert_log, fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]  # leitura de 11:59:58
    await primeira_passada(engine, fiware_falso)
    relogio.avancar(40)  # 42 s sem leitura (limite 30)
    await engine.tick()
    await engine.tick()
    assert fiware_falso.comandos == []
    assert [(a.attr, a.value) for a in alert_log.open_alerts()] == [("offline", None)]
    [status] = fleet.snapshot()
    assert (status.status, status.offline_reason) == ("offline", "sem_leitura")
    assert status.score is None
    assert status.seconds_since == 42


async def test_volta_do_offline_fecha_alerta_e_ressincroniza(engine, fiware_falso, cadastrar,
                                                             alert_log, fleet, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    relogio.avancar(40)
    await engine.tick()
    fiware_falso.entidades = [entidade("001", instante=instante_de(relogio, 1))]
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits", "alert_off"]
    assert alert_log.open_alerts() == []
    assert alert_log.list()[0].duration_seconds == 0
    assert fleet.status_of("vinheria001") == "ok"


async def test_volta_do_offline_com_anomalia_reenvia_blink(engine, fiware_falso, cadastrar,
                                                           alert_log, relogio):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    relogio.avancar(40)  # a mesma leitura velha: offline
    await engine.tick()
    fiware_falso.entidades = [entidade("001", t=21.0, instante=instante_de(relogio, 1))]
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits", "alert_off", "blink_temp"]
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]


async def test_vinheria_recem_cadastrada_sem_leitura_fica_configurando_ate_o_limite(
        engine, fiware_falso, cadastrar, alert_log, fleet, relogio):
    cadastrar("001", created_at=relogio.iso(segundos_atras=10))
    fiware_falso.entidades = []  # ainda sem entidade no Orion
    await engine.tick()
    [status] = fleet.snapshot()
    assert status.status == "configurando"
    assert status.current.temperature is None
    assert status.score is None
    assert alert_log.open_alerts() == []
    relogio.avancar(25)  # 35 s desde o cadastro
    await engine.tick()
    assert [a.attr for a in alert_log.open_alerts()] == ["offline"]


async def test_vinheria_antiga_sem_entidade_fica_offline(engine, fiware_falso, cadastrar,
                                                         alert_log, fleet):
    cadastrar("001")  # cadastrada em 07/10
    fiware_falso.entidades = []
    await engine.tick()
    assert fleet.status_of("vinheria001") == "offline"
    assert [a.attr for a in alert_log.open_alerts()] == ["offline"]
    assert fiware_falso.comandos == []


async def test_falha_no_comando_tenta_de_novo_no_proximo_ciclo(engine, fiware_falso, cadastrar,
                                                               alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.erro_comando = FiwareUnavailable("orion", "sem conexão")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    assert fiware_falso.comandos == []
    fiware_falso.erro_comando = None
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert len(alert_log.open_alerts()) == 1


async def test_alertas_abertos_sao_retomados_apos_reinicio(engine, fiware_falso, cadastrar,
                                                           alert_log):
    cadastrar("001")
    alert_log.open("vinheria001", "temperature", 21.0, "2026-10-08T11:00:00+00:00")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    assert len(alert_log.open_alerts()) == 1
    assert comandos(fiware_falso) == ["set_limits", "alert_off", "blink_temp"]


async def test_alerta_retomado_fecha_quando_volta_a_faixa(engine, fiware_falso, cadastrar,
                                                          alert_log):
    cadastrar("001")
    alert_log.open("vinheria001", "temperature", 21.0, "2026-10-08T11:00:00+00:00")
    fiware_falso.entidades = [entidade("001", t=17.9)]  # dentro; lado desconhecido fecha
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert comandos(fiware_falso) == ["set_limits", "alert_off"]


async def test_vinheria_removida_tem_alertas_fechados(engine, fiware_falso, cadastrar, conn,
                                                      alert_log, fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    with conn:
        conn.execute("DELETE FROM devices WHERE device_id = 'vinheria001'")
    await engine.tick()
    assert alert_log.open_alerts() == []
    assert alert_log.list()[0].closed_at is not None
    assert fleet.snapshot() == []


async def test_run_repete_tick_e_sobrevive_a_erro(registry, limits, alert_log, fiware_falso,
                                                  store, fleet, relogio):
    esperas = []

    async def sleep_falso(segundos):
        esperas.append(segundos)
        if len(esperas) == 3:
            raise _Parar

    motor = TriggerEngine(registry, limits, alert_log, fiware_falso, store, fleet,
                          clock=relogio, sleep=sleep_falso)
    chamadas = []

    async def tick_falso():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("ciclo ruim")

    motor.tick = tick_falso
    with pytest.raises(_Parar):
        await motor.run()
    assert len(chamadas) == 3
    assert esperas == [5, 5, 5]  # poll_seconds padrão
