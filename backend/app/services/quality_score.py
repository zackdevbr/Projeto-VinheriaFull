"""
Score de qualidade do ambiente de uma vinheria (RF11).

Cada atributo vale 100 dentro da faixa ideal da vinheria; fora dela, perde
pontos na proporção da distância em relação à largura da faixa, sem ficar
negativo. O score geral é a média dos três. Funções puras: não acessam
banco nem rede.
"""
from app.models.schemas import AttrScores, CurrentReading, Limits

# Ordem e nomes em português usados nas mensagens ao usuário
ATTR_LABELS = {
    "temperature": "temperatura",
    "humidity": "umidade",
    "luminosity": "luminosidade",
}


def attr_score(value: float | None, lo: float, hi: float) -> float | None:
    """Nota de um atributo: 100 na faixa [lo, hi]; fora, cai proporcionalmente.

    Ex.: faixa 12–18 (largura 6) e valor 20 (2 acima) → 100 − 100·2/6 = 66,7.
    """
    if value is None:
        return None
    if lo <= value <= hi:
        return 100.0
    distancia = lo - value if value < lo else value - hi
    return max(0.0, 100.0 - 100.0 * distancia / (hi - lo))


def quality_score(reading: CurrentReading, limits: Limits) -> tuple[float | None, AttrScores]:
    """Score geral (média, 1 casa) e notas por atributo.

    Se qualquer atributo não tiver leitura, o score geral é None: não se
    calcula nota a partir de dado incompleto.
    """
    notas: dict[str, float | None] = {}
    for attr in ATTR_LABELS:
        faixa = getattr(limits, attr)
        notas[attr] = attr_score(getattr(reading, attr), faixa.min, faixa.max)
    arredondadas = AttrScores(**{
        attr: None if nota is None else round(nota, 1) for attr, nota in notas.items()
    })
    if any(nota is None for nota in notas.values()):
        return None, arredondadas
    return round(sum(notas.values()) / len(notas), 1), arredondadas


def unavailable_message(attrs: AttrScores) -> str | None:
    """Mensagem para o painel quando o score não pode ser calculado; None se pode."""
    faltando = [rotulo for attr, rotulo in ATTR_LABELS.items() if getattr(attrs, attr) is None]
    if not faltando:
        return None
    if len(faltando) == 1:
        lista = faltando[0]
    else:
        lista = ", ".join(faltando[:-1]) + " e " + faltando[-1]
    return f"Score indisponível: aguardando leitura de {lista}"
