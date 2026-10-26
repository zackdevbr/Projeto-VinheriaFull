# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes das estatísticas do chatbot (spec R3)."""
from datetime import datetime, timedelta, timezone

from app.models.schemas import HistoryPoint
from app.services.chat_stats import estatisticas, filtrar_janela, tendencia

AGORA = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


def pontos(valores, passo_min=1.0, fim=AGORA, formato_z=True):
    """Série do mais velho ao mais novo, o último em `fim`."""
    n = len(valores)
    serie = []
    for i, valor in enumerate(valores):
        instante = fim - timedelta(minutes=passo_min * (n - 1 - i))
        ts = instante.isoformat()
        serie.append(HistoryPoint(ts=ts.replace("+00:00", "Z") if formato_z else ts, value=valor))
    return serie


def test_estatisticas_basicas():
    r = estatisticas(pontos([14, 15, 16]), "temperature", 1, fuso=timezone.utc)
    assert (r["n"], r["media"], r["minimo"], r["maximo"], r["desvio"]) == (3, 15.0, 14, 16, 1.0)
    assert r["unidade"] == "°C"
    assert (r["inicio"], r["fim"]) == ("08/10 11:58", "08/10 12:00")
    assert r["tendencia"] == "subindo"


def test_estatisticas_sem_pontos():
    assert estatisticas([], "humidity", 1) == {"n": 0}


def test_estatisticas_um_ponto():
    r = estatisticas(pontos([60]), "humidity", 1)
    assert r["desvio"] is None
    assert r["tendencia"] == "estável"
    assert r["unidade"] == "%"


def test_estatisticas_ordenam_pontos_fora_de_ordem():
    serie = pontos([20, 18, 16])
    assert estatisticas(list(reversed(serie)), "temperature", 1)["tendencia"] == "caindo"


def test_janela_completa_e_incompleta():
    cheia = pontos([14] * 61, passo_min=1)        # 60 min cobertos
    curta = pontos([14] * 51, passo_min=1)        # 50 min cobertos (< 90 % de 1 h)
    assert estatisticas(cheia, "temperature", 1)["janela_completa"] is True
    assert estatisticas(curta, "temperature", 1)["janela_completa"] is False
    assert estatisticas(curta, "temperature", 1)["periodo_coberto_horas"] == 0.8


def test_tendencia_estavel_abaixo_do_limiar():
    assert tendencia(pontos([14, 14.5, 14.9]), "temperature") == "estável"
    assert tendencia(pontos([50, 52]), "humidity") == "estável"
    assert tendencia(pontos([10, 14]), "luminosity") == "estável"


def test_tendencia_acima_do_limiar():
    assert tendencia(pontos([50, 54]), "humidity") == "subindo"
    assert tendencia(pontos([30, 20]), "luminosity") == "caindo"


def test_filtrar_janela_aceita_z_e_offset():
    velhos = pontos([1], fim=AGORA - timedelta(minutes=90))
    novos_z = pontos([2], fim=AGORA - timedelta(minutes=30))
    novos_offset = pontos([3], fim=AGORA, formato_z=False)
    filtrados = filtrar_janela(velhos + novos_z + novos_offset, 1, AGORA)
    assert [p.value for p in filtrados] == [2, 3]
