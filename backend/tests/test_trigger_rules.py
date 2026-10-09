"""Testes das regras puras do motor de alertas (spec R5)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.trigger_rules import (
    can_close,
    command_plan,
    direction,
    hysteresis_margin,
    is_offline,
    parse_instant,
    seconds_since,
)

UTC = timezone.utc
MEIO_DIA = datetime(2026, 10, 8, 12, 0, 0, tzinfo=UTC)


def test_parse_instant_formatos():
    esperado = datetime(2026, 10, 8, 11, 59, 58, tzinfo=UTC)
    assert parse_instant("2026-10-08T11:59:58.000Z") == esperado
    assert parse_instant("2026-10-08T11:59:58+00:00") == esperado
    assert parse_instant("2026-10-08T11:59:58") == esperado  # sem fuso = UTC


@pytest.mark.parametrize("texto", [None, "", "   ", "ontem", 123])
def test_parse_instant_invalido(texto):
    assert parse_instant(texto) is None


def test_seconds_since():
    assert seconds_since(MEIO_DIA - timedelta(seconds=4), MEIO_DIA) == 4
    assert seconds_since(MEIO_DIA + timedelta(seconds=3), MEIO_DIA) == 0  # relógio adiantado
    assert seconds_since(None, MEIO_DIA) is None


def test_is_offline_pela_leitura():
    visto = MEIO_DIA
    assert is_offline(visto, None, MEIO_DIA + timedelta(seconds=30), 30) is False
    assert is_offline(visto, None, MEIO_DIA + timedelta(seconds=31), 30) is True


def test_is_offline_sem_leitura_usa_cadastro():
    cadastro = MEIO_DIA
    assert is_offline(None, cadastro, MEIO_DIA + timedelta(seconds=10), 30) is False
    assert is_offline(None, cadastro, MEIO_DIA + timedelta(seconds=31), 30) is True
    assert is_offline(None, None, MEIO_DIA, 30) is True


def test_direction():
    assert direction(19, 12, 18) == "above"
    assert direction(11, 12, 18) == "below"
    assert direction(12, 12, 18) is None
    assert direction(18, 12, 18) is None
    assert direction(15, 12, 18) is None


def test_hysteresis_margin_limitada_pela_largura():
    assert hysteresis_margin("temperature", 12, 18) == 0.5
    assert hysteresis_margin("humidity", 50, 70) == 2.0
    assert hysteresis_margin("luminosity", 0, 30) == 2.0
    assert hysteresis_margin("temperature", 15, 16) == 0.25


def test_can_close_respeita_lado():
    assert can_close(17.6, 12, 18, "above", 0.5) is False
    assert can_close(17.5, 12, 18, "above", 0.5) is True
    assert can_close(12.1, 12, 18, "above", 0.5) is True    # folga só do lado violado
    assert can_close(12.4, 12, 18, "below", 0.5) is False
    assert can_close(12.5, 12, 18, "below", 0.5) is True
    assert can_close(18.0, 12, 18, None, 0.5) is True       # lado desconhecido
    assert can_close(18.1, 12, 18, None, 0.5) is False
    assert can_close(11.0, 12, 18, "above", 0.5) is False   # passou para o outro lado


def test_command_plan():
    assert command_plan(set()) == ["alert_off"]
    assert command_plan({"temperature"}) == ["alert_off", "blink_temp"]
    assert command_plan({"temperature", "humidity", "luminosity"}) == [
        "alert_off", "blink_lux", "blink_hum", "blink_temp"]
    assert command_plan(frozenset({"luminosity", "humidity"})) == [
        "alert_off", "blink_lux", "blink_hum"]
