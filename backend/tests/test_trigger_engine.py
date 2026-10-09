"""Testes do motor de alertas: sensores, comandos e retrato (spec R7)."""
import pytest

from app.models.schemas import AttrLimits, Limits
from app.services.limits import DEFAULT_LIMITS
from tests.fakes import entidade

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"
E2 = "urn:ngsi-ld:Vinheria:002"


def comandos(fiware, entity_id=E1):
    """Nomes dos comandos enviados a uma entidade, na ordem."""
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def primeira_passada(engine, fiware):
    """Roda a ressincronização da partida e limpa os comandos dela."""
    await engine.tick()
    fiware.comandos.clear()


async def test_primeira_passada_sincroniza_faixa_e_desliga_alerta(engine, fiware_falso, cadastrar):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await engine.tick()
    assert fiware_falso.comandos == [(E1, "set_limits", "12;18;50;70;0;30"),
                                     (E1, "alert_off", "")]


async def test_segunda_passada_sem_mudanca_nao_envia_nada(engine, fiware_falso, cadastrar):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    await engine.tick()
    await engine.tick()
    assert fiware_falso.comandos == []


async def test_uma_chamada_list_entities_por_ciclo(engine, fiware_falso, cadastrar):
    for numero in ("001", "002", "003"):
        cadastrar(numero)
    fiware_falso.entidades = [entidade(n) for n in ("001", "002", "003")]
    await engine.tick()
    assert fiware_falso.chamadas_listar == 1


async def test_frota_vazia_nao_chama_fiware(engine, fiware_falso, fleet):
    await engine.tick()
    assert fiware_falso.chamadas_listar == 0
    assert fleet.snapshot() == []


async def test_acima_do_maximo_abre_alerta_e_envia_blink_uma_vez(engine, fiware_falso,
                                                                 cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]  # sem repetição
    assert [(a.attr, a.value) for a in alert_log.open_alerts()] == [("temperature", 21.0)]


async def test_abaixo_do_minimo_abre_alerta(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", h=40.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_hum"]
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", h=51.0)]  # dentro, mas sem folga (min 50 + 2)
    await engine.tick()
    assert fiware_falso.comandos == []
    assert len(alert_log.open_alerts()) == 1
    fiware_falso.entidades = [entidade("001", h=53.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []


async def test_volta_a_faixa_fecha_alerta_e_envia_alert_off(engine, fiware_falso, cadastrar,
                                                           alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=15.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []
    assert alert_log.list()[0].closed_at == "2026-10-08T12:00:00+00:00"


async def test_histerese_segura_alerta_perto_do_limite(engine, fiware_falso, cadastrar,
                                                       alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=17.8)]  # dentro, mas a menos de 0,5 do máximo
    await engine.tick()
    assert fiware_falso.comandos == []
    assert len(alert_log.open_alerts()) == 1
    fiware_falso.entidades = [entidade("001", t=17.4)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]


async def test_histerese_so_vale_do_lado_violado(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", l=40.0)]  # excesso de luz (faixa 0–30)
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", l=0.0)]  # adega escura
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []


async def test_duas_anomalias_temperatura_por_ultimo(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0, h=40.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_hum", "blink_temp"]
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, h=60.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=15.0, h=60.0)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]


async def test_leitura_ausente_nao_muda_estado(engine, fiware_falso, cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=None)]
    await engine.tick()
    assert fiware_falso.comandos == []
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]


async def test_anomalia_numa_vinheria_nao_afeta_outra(engine, fiware_falso, cadastrar, fleet):
    cadastrar("001")
    cadastrar("002", name="Vinheria Mineira", city="Minas Gerais")
    fiware_falso.entidades = [entidade("001"), entidade("002")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001"), entidade("002", t=21.0)]
    await engine.tick()
    assert comandos(fiware_falso, E1) == []
    assert comandos(fiware_falso, E2) == ["alert_off", "blink_temp"]
    assert fleet.status_of("vinheria001") == "ok"
    assert fleet.status_of("vinheria002") == "alerta"


async def test_faixa_nova_vale_no_proximo_ciclo(engine, fiware_falso, cadastrar, limits,
                                                alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    limits.update("vinheria001", DEFAULT_LIMITS.model_copy(
        update={"temperature": AttrLimits(min=12, max=25)}))
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off"]
    assert alert_log.open_alerts() == []


async def test_faixa_pendente_envia_set_limits(engine, fiware_falso, cadastrar, limits):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001")]
    await primeira_passada(engine, fiware_falso)
    limits.update("vinheria001", Limits(temperature=AttrLimits(min=10, max=16),
                                        humidity=DEFAULT_LIMITS.humidity,
                                        luminosity=DEFAULT_LIMITS.luminosity))
    engine.mark_limits_pending("vinheria001")
    await engine.tick()
    assert fiware_falso.comandos == [(E1, "set_limits", "10;16;50;70;0;30")]
    fiware_falso.comandos.clear()
    await engine.tick()
    assert fiware_falso.comandos == []


async def test_retrato_da_frota_tem_valores_score_e_alertas(engine, fiware_falso, cadastrar,
                                                            fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()
    [status] = fleet.snapshot()
    assert (status.device_id, status.name, status.city) == (
        "vinheria001", "Vinheria Paulista", "São Paulo")
    assert status.status == "alerta"
    assert status.offline_reason is None
    assert status.last_seen == "2026-10-08T11:59:58.000Z"
    assert status.seconds_since == 2
    assert (status.current.temperature, status.current.humidity,
            status.current.luminosity) == (21.0, 60.0, 10.0)
    assert status.score == 83.3  # temperatura 50 (3 °C acima numa faixa de 6), demais 100
    assert [(a.attr, a.value, a.since) for a in status.active_alerts] == [
        ("temperature", 21.0, "2026-10-08T12:00:00+00:00")]
    assert fleet.updated_at == "2026-10-08T12:00:00+00:00"
    assert fleet.fiware_online is True
