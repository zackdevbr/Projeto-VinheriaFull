# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Alertas abertos em memória, sempre espelhados no AlertLog (SQLite).

O motor consulta este estado a cada ciclo para saber o que já está aberto
sem ir ao banco, e de que lado da faixa o valor saiu (para a folga ao
fechar). Abrir e fechar aqui grava no log na mesma hora.
"""
import logging
from dataclasses import dataclass

from app.models.schemas_fleet import ActiveAlert, Alert
from app.services.alert_log import AlertLog
from app.services.trigger_rules import SENSOR_ORDER

log = logging.getLogger(__name__)

OFFLINE = "offline"
# Ordem dos alertas ativos no retrato: sensores na ordem canônica, offline por último
ORDEM_ALERTAS = SENSOR_ORDER + (OFFLINE,)


@dataclass
class OpenAlert:
    """Alerta aberto: id no SQLite, lado violado ("above"/"below"/None), valor e início."""
    alert_id: int
    side: str | None
    value: float | None
    since: str


class AlertTracker:
    """Alertas abertos por (device_id, attr)."""

    def __init__(self, alerts: AlertLog):
        self._alerts = alerts
        self._open: dict[tuple[str, str], OpenAlert] = {}

    def load(self) -> list[Alert]:
        """Retoma os alertas abertos no SQLite (partida do backend).

        O lado violado não fica gravado, então volta como None (desconhecido).
        Devolve os alertas retomados.
        """
        abertos = self._alerts.open_alerts()
        for alerta in abertos:
            self._open[(alerta.device_id, alerta.attr)] = OpenAlert(
                alerta.id, None, alerta.value, alerta.opened_at)
        return abertos

    def get(self, device_id: str, attr: str) -> OpenAlert | None:
        """Alerta aberto daquele atributo, ou None."""
        return self._open.get((device_id, attr))

    def open(self, device_id: str, attr: str, value: float | None, side: str | None,
             when: str) -> None:
        """Abre o alerta (se ainda não estiver aberto) e grava no log."""
        chave = (device_id, attr)
        if chave in self._open:
            return
        alerta = self._alerts.open(device_id, attr, value, when)
        self._open[chave] = OpenAlert(alerta.id, side, value, alerta.opened_at)
        log.info("alerta aberto: %s %s (%s)", device_id, attr, value)

    def close(self, device_id: str, attr: str, when: str) -> None:
        """Fecha o alerta, se estiver aberto."""
        aberto = self._open.pop((device_id, attr), None)
        if aberto is not None:
            self._alerts.close(aberto.alert_id, when)
            log.info("alerta fechado: %s %s", device_id, attr)

    def close_except(self, keep: set[str], when: str) -> None:
        """Fecha os alertas de quem não está em `keep` (vinherias removidas)."""
        for device_id, attr in [chave for chave in self._open if chave[0] not in keep]:
            self.close(device_id, attr, when)

    def active(self, device_id: str) -> list[ActiveAlert]:
        """Alertas ativos da vinheria, sensores na ordem canônica e offline por último."""
        ativos = [ActiveAlert(attr=attr, value=aberto.value, since=aberto.since)
                  for (dono, attr), aberto in self._open.items() if dono == device_id]
        return sorted(ativos, key=lambda alerta: ORDEM_ALERTAS.index(alerta.attr))

    def active_sensors(self, device_id: str) -> frozenset[str]:
        """Atributos de sensor em alerta (o que o ESP32 deve estar mostrando)."""
        return frozenset(attr for attr in SENSOR_ORDER if (device_id, attr) in self._open)
