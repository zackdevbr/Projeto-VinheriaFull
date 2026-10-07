"""Testes da faixa ideal: padrão, validação, SQLite e nomes no Orion (spec R2)."""
import pytest
from pydantic import ValidationError

from app.models.schemas import AttrLimits
from app.services.limits import DEFAULT_LIMITS, limits_to_orion_attrs


def _grava_device(conn, device_id="vinheria001"):
    """Cria a linha em devices (exigida pela chave estrangeira de triggers)."""
    with conn:
        conn.execute(
            "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
            "VALUES (?, ?, 'Vinheria', 'Cidade', '2026-10-07T21:00:00+00:00')",
            (device_id, "urn:ngsi-ld:Vinheria:" + device_id[-3:]),
        )


def test_default_limits_valores():
    assert (DEFAULT_LIMITS.temperature.min, DEFAULT_LIMITS.temperature.max) == (12, 18)
    assert (DEFAULT_LIMITS.humidity.min, DEFAULT_LIMITS.humidity.max) == (50, 70)
    assert (DEFAULT_LIMITS.luminosity.min, DEFAULT_LIMITS.luminosity.max) == (0, 30)


@pytest.mark.parametrize("minimo, maximo", [(18, 12), (15, 15)])
def test_attr_limits_rejeita_min_maior_ou_igual_max(minimo, maximo):
    with pytest.raises(ValidationError):
        AttrLimits(min=minimo, max=maximo)


def test_limits_seed_e_get(conn, limits):
    _grava_device(conn)
    with conn:
        limits.seed_defaults("vinheria001")
    assert conn.execute("SELECT COUNT(*) FROM triggers").fetchone()[0] == 3
    assert limits.get("vinheria001") == DEFAULT_LIMITS


def test_limits_get_sem_linhas_usa_padrao(conn, limits):
    _grava_device(conn)
    with conn:
        conn.execute("INSERT INTO triggers (device_id, attr, min_value, max_value) "
                     "VALUES ('vinheria001', 'temperature', 10, 20)")
    faixa = limits.get("vinheria001")
    assert (faixa.temperature.min, faixa.temperature.max) == (10, 20)
    assert faixa.humidity == DEFAULT_LIMITS.humidity
    assert faixa.luminosity == DEFAULT_LIMITS.luminosity


def test_limits_to_orion_attrs():
    assert limits_to_orion_attrs(DEFAULT_LIMITS) == {
        "temp_min": 12, "temp_max": 18,
        "hum_min": 50, "hum_max": 70,
        "lux_min": 0, "lux_max": 30,
    }
