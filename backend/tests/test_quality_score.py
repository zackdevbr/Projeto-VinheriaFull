"""Testes do score de qualidade do ambiente (spec R3)."""
import pytest

from app.models.schemas import AttrScores, CurrentReading
from app.services.limits import DEFAULT_LIMITS
from app.services.quality_score import attr_score, quality_score, unavailable_message


def _leitura(temperature=15.0, humidity=60.0, luminosity=10.0):
    """Leitura sintética; por padrão, tudo dentro da faixa padrão."""
    return CurrentReading(device_id="vinheria001", temperature=temperature,
                          humidity=humidity, luminosity=luminosity)


@pytest.mark.parametrize("valor", [12, 15, 18])
def test_attr_score_dentro_da_faixa(valor):
    assert attr_score(valor, 12, 18) == 100


def test_attr_score_acima_do_maximo():
    assert attr_score(20, 12, 18) == pytest.approx(66.6667, abs=1e-3)


def test_attr_score_abaixo_do_minimo():
    assert attr_score(9, 12, 18) == pytest.approx(50.0)


def test_attr_score_nao_fica_negativo():
    assert attr_score(40, 12, 18) == 0


def test_attr_score_valor_nulo():
    assert attr_score(None, 12, 18) is None


def test_quality_score_tudo_ok():
    nota, notas = quality_score(_leitura(), DEFAULT_LIMITS)
    assert nota == 100
    assert notas == AttrScores(temperature=100, humidity=100, luminosity=100)


def test_quality_score_exemplo_do_prd():
    nota, notas = quality_score(_leitura(temperature=20.0), DEFAULT_LIMITS)
    assert nota == 88.9
    assert notas.temperature == 66.7


def test_quality_score_nulo_se_faltar_atributo():
    nota, notas = quality_score(_leitura(humidity=None), DEFAULT_LIMITS)
    assert nota is None
    assert notas.humidity is None
    assert notas.temperature == 100


@pytest.mark.parametrize("notas, esperado", [
    (AttrScores(temperature=100, humidity=None, luminosity=None),
     "Score indisponível: aguardando leitura de umidade e luminosidade"),
    (AttrScores(),
     "Score indisponível: aguardando leitura de temperatura, umidade e luminosidade"),
])
def test_score_indisponivel_traz_mensagem(notas, esperado):
    assert unavailable_message(notas) == esperado


def test_score_disponivel_sem_mensagem():
    assert unavailable_message(AttrScores(temperature=100, humidity=80, luminosity=100)) is None
