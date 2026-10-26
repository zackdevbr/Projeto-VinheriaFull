# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Regras puras do motor de alertas: tempo, offline, faixa com folga
(histerese) e plano de comandos para o ESP32.

Sem banco e sem rede, para cada decisão ser testada isolada. Quem aplica
as regras a cada ciclo é o TriggerEngine.
"""
from datetime import datetime, timezone

# Ordem canônica dos atributos de sensor
SENSOR_ORDER = ("temperature", "humidity", "luminosity")
# Comando de alerta de cada atributo
BLINK_COMMANDS = {"temperature": "blink_temp", "humidity": "blink_hum",
                  "luminosity": "blink_lux"}
# Ordem de envio dos blinks: o último recebido define o padrão de LED e
# buzzer no ESP32, então a temperatura (a anomalia mais danosa ao vinho)
# vai por último
SEND_ORDER = ("luminosity", "humidity", "temperature")
# Folga para fechar um alerta, por atributo (°C, % e %)
DEFAULT_HYSTERESIS = {"temperature": 0.5, "humidity": 2.0, "luminosity": 2.0}
# A folga nunca passa de 25 % da largura da faixa (faixas estreitas)
MAX_HYSTERESIS_FRACTION = 0.25


def parse_instant(texto) -> datetime | None:
    """Converte o TimeInstant do IoT Agent (ex.: 2026-10-08T11:59:58.000Z).

    Sem fuso, assume UTC. Vazio, inválido ou não texto devolve None.
    """
    if not isinstance(texto, str) or not texto.strip():
        return None
    try:
        instante = datetime.fromisoformat(texto.strip())
    except ValueError:
        return None
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante


def seconds_since(reference: datetime | None, now: datetime) -> int | None:
    """Segundos inteiros desde `reference` (nunca negativo); None sem referência."""
    if reference is None:
        return None
    return max(0, int((now - reference).total_seconds()))


def is_offline(last_seen: datetime | None, created_at: datetime | None,
               now: datetime, offline_seconds: int) -> bool:
    """Offline se a última leitura passou do limite.

    Sem leitura, a referência é o cadastro: vinheria recém-cadastrada tem
    `offline_seconds` para mandar a primeira leitura antes de ficar offline.
    """
    referencia = last_seen or created_at
    if referencia is None:
        return True
    return (now - referencia).total_seconds() > offline_seconds


def direction(value: float, lo: float, hi: float) -> str | None:
    """Lado violado da faixa: "above", "below" ou None (dentro, bordas incluídas)."""
    if value > hi:
        return "above"
    if value < lo:
        return "below"
    return None


def hysteresis_margin(attr: str, lo: float, hi: float,
                      table: dict[str, float] = DEFAULT_HYSTERESIS) -> float:
    """Folga para fechar o alerta: a da tabela, limitada a 25 % da largura."""
    return min(table[attr], MAX_HYSTERESIS_FRACTION * (hi - lo))


def can_close(value: float, lo: float, hi: float, side: str | None, margin: float) -> bool:
    """True se o alerta pode fechar.

    Exige estar dentro da faixa e, do lado que foi violado, afastado da
    borda pela folga. Do lado oposto não há folga: com lux_min = 0, a adega
    escura (luz 0) precisa fechar um alerta de excesso de luz. Lado
    desconhecido (alerta retomado após reinício) fecha ao entrar na faixa.
    """
    if not lo <= value <= hi:
        return False
    if side == "above":
        return value <= hi - margin
    if side == "below":
        return value >= lo + margin
    return True


def command_plan(active) -> list[str]:
    """Comandos que deixam o ESP32 coerente com o conjunto de atributos em alerta.

    O firmware não desliga um atributo só, então o plano recomeça do zero:
    alert_off e um blink por atributo ativo, do menos para o mais prioritário.
    """
    return ["alert_off"] + [BLINK_COMMANDS[attr] for attr in SEND_ORDER if attr in active]
