# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Estatísticas das séries do STH-Comet para o chatbot (funções puras).

Calcula média, mínimo, máximo, desvio e tendência de uma lista de pontos
[{ts, value}], e diz quanto da janela pedida os pontos de fato cobrem: a
consulta pega no máximo os 500 pontos mais novos, que podem não chegar ao
começo da janela.
"""
import statistics
from datetime import datetime, timedelta, timezone, tzinfo

from app.models.schemas import HistoryPoint

# Nome em português e unidade de cada atributo, como o bot deve falar
NOME_ATRIBUTO = {"temperature": "temperatura", "humidity": "umidade",
                 "luminosity": "luminosidade"}
UNIDADE = {"temperature": "°C", "humidity": "%", "luminosity": "%"}
# Amplitude (máx − mín) abaixo da qual a série é considerada estável
LIMIAR_ESTAVEL = {"temperature": 1.0, "humidity": 3.0, "luminosity": 5.0}
# Fração mínima da janela pedida que os pontos precisam cobrir
COBERTURA_MINIMA = 0.9


def para_datetime(ts: str) -> datetime:
    """ISO do STH ("...Z") ou do SQLite ("+00:00") para datetime com fuso (UTC se faltar)."""
    instante = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return instante if instante.tzinfo else instante.replace(tzinfo=timezone.utc)


def hora_local(ts: str, fuso: tzinfo | None = None) -> str:
    """Instante no formato DD/MM HH:MM; sem `fuso`, usa o fuso da máquina."""
    return para_datetime(ts).astimezone(fuso).strftime("%d/%m %H:%M")


def filtrar_janela(pontos: list[HistoryPoint], horas: float, agora: datetime) -> list[HistoryPoint]:
    """Só os pontos das últimas `horas` antes de `agora`."""
    inicio = agora - timedelta(hours=horas)
    return [ponto for ponto in pontos if para_datetime(ponto.ts) >= inicio]


def tendencia(pontos: list[HistoryPoint], atributo: str) -> str:
    """"estável", "subindo" ou "caindo".

    Estável quando a amplitude fica abaixo do limiar do atributo; senão, o
    sinal da inclinação da reta de mínimos quadrados (valor × tempo) decide.
    """
    if len(pontos) < 2:
        return "estável"
    valores = [ponto.value for ponto in pontos]
    if max(valores) - min(valores) < LIMIAR_ESTAVEL[atributo]:
        return "estável"
    inicio = para_datetime(pontos[0].ts)
    segundos = [(para_datetime(ponto.ts) - inicio).total_seconds() for ponto in pontos]
    if len(set(segundos)) < 2:
        return "estável"
    inclinacao = statistics.linear_regression(segundos, valores).slope
    return "subindo" if inclinacao > 0 else "caindo"


def estatisticas(pontos: list[HistoryPoint], atributo: str, horas_pedidas: float,
                 fuso: tzinfo | None = None) -> dict:
    """Resumo numérico da série, pronto para o Gemini citar; {"n": 0} sem pontos."""
    if not pontos:
        return {"n": 0}
    ordenados = sorted(pontos, key=lambda ponto: para_datetime(ponto.ts))
    valores = [ponto.value for ponto in ordenados]
    coberto = (para_datetime(ordenados[-1].ts) - para_datetime(ordenados[0].ts)).total_seconds() / 3600
    return {
        "n": len(valores),
        "media": round(statistics.fmean(valores), 1),
        "minimo": round(min(valores), 1),
        "maximo": round(max(valores), 1),
        "desvio": round(statistics.stdev(valores), 1) if len(valores) >= 2 else None,
        "inicio": hora_local(ordenados[0].ts, fuso),
        "fim": hora_local(ordenados[-1].ts, fuso),
        "periodo_coberto_horas": round(coberto, 1),
        "janela_completa": coberto >= COBERTURA_MINIMA * horas_pedidas,
        "tendencia": tendencia(ordenados, atributo),
        "unidade": UNIDADE[atributo],
    }
