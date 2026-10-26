# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes do motor: ESP32 sem faixa recebe na hora e não dispara alerta (spec R8)."""
import pytest

from app.services.fiware_errors import FiwareUnavailable
from tests.fakes import entidade

pytestmark = pytest.mark.anyio

E1 = "urn:ngsi-ld:Vinheria:001"


def comandos(fiware, entity_id=E1):
    return [comando for entidade_id, comando, _ in fiware.comandos if entidade_id == entity_id]


async def test_sem_configuracao_recebe_faixa_na_hora_e_nao_avalia(engine, fiware_falso,
                                                                  cadastrar, alert_log, fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0, c=0)]  # fora da faixa, mas sem configurar
    await engine.tick()
    assert fiware_falso.comandos == [(E1, "set_limits", "12,18,50,70,0,30")]
    assert alert_log.open_alerts() == []
    assert fleet.status_of("vinheria001") == "configurando"
    fiware_falso.comandos.clear()
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]  # ainda c=0: manda de novo


async def test_configured_ausente_conta_como_nao_configurado(engine, fiware_falso, cadastrar,
                                                             fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", c=None)]  # firmware antigo, sem o atributo c
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]
    assert fleet.status_of("vinheria001") == "configurando"


async def test_apos_configurar_sincroniza_alerta_sem_reenviar_faixa(engine, fiware_falso,
                                                                    cadastrar, alert_log):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0, c=0)]
    await engine.tick()
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, c=1)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert [a.attr for a in alert_log.open_alerts()] == ["temperature"]


async def test_reinicio_do_esp32_reenvia_faixa_e_depois_o_alerta(engine, fiware_falso,
                                                                 cadastrar, alert_log, fleet):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", t=21.0)]
    await engine.tick()  # faixa + alerta de temperatura
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, c=0)]  # ESP32 reiniciou
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]
    assert fleet.status_of("vinheria001") == "configurando"
    assert len(alert_log.open_alerts()) == 1
    fiware_falso.comandos.clear()
    fiware_falso.entidades = [entidade("001", t=21.0, c=1)]
    await engine.tick()
    assert comandos(fiware_falso) == ["alert_off", "blink_temp"]
    assert len(alert_log.open_alerts()) == 1


async def test_falha_ao_enviar_faixa_tenta_no_proximo_ciclo(engine, fiware_falso, cadastrar):
    cadastrar("001")
    fiware_falso.entidades = [entidade("001", c=0)]
    fiware_falso.erro_comando = FiwareUnavailable("orion", "sem conexão")
    await engine.tick()
    assert fiware_falso.comandos == []
    fiware_falso.erro_comando = None
    await engine.tick()
    assert comandos(fiware_falso) == ["set_limits"]
