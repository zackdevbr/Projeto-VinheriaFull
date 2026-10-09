"""
Log de alertas (RF10): cada alerta tem vinheria, atributo, valor, início,
fim e duração.

O alerta abre quando um atributo sai da faixa (ou a vinheria, ou a EC2,
fica offline) e fecha quando volta. As linhas ficam no SQLite mesmo depois
que a vinheria é removida, para o histórico não se perder.
"""
from datetime import datetime

from app.core.db import Database
from app.models.schemas_fleet import Alert


def _duracao(opened_at: str, closed_at: str | None) -> int | None:
    """Segundos entre abertura e fechamento; None enquanto aberto."""
    if closed_at is None:
        return None
    delta = datetime.fromisoformat(closed_at) - datetime.fromisoformat(opened_at)
    return max(0, int(delta.total_seconds()))


def _linha_para_alert(linha) -> Alert:
    """Converte uma linha da tabela alerts no modelo Alert."""
    return Alert(id=linha["id"], device_id=linha["device_id"], attr=linha["attr"],
                 value=linha["value"], opened_at=linha["opened_at"],
                 closed_at=linha["closed_at"],
                 duration_seconds=_duracao(linha["opened_at"], linha["closed_at"]))


class AlertLog:
    """Gravação e consulta do histórico de alertas."""

    def __init__(self, db: Database):
        self._db = db

    def open(self, device_id: str, attr: str, value: float | None, opened_at: str) -> Alert:
        """Abre um alerta e devolve o registro com o id gerado."""
        with self._db:
            resultado = self._db.execute(
                "INSERT INTO alerts (device_id, attr, value, opened_at) VALUES (?, ?, ?, ?)",
                (device_id, attr, value, opened_at),
            )
        return Alert(id=resultado.lastrowid, device_id=device_id, attr=attr, value=value,
                     opened_at=opened_at)

    def close(self, alert_id: int, closed_at: str) -> None:
        """Fecha um alerta aberto; alerta já fechado não muda."""
        with self._db:
            self._db.execute(
                "UPDATE alerts SET closed_at = ? WHERE id = ? AND closed_at IS NULL",
                (closed_at, alert_id),
            )

    def open_alerts(self) -> list[Alert]:
        """Alertas ainda abertos, na ordem em que abriram (usado na partida do poller)."""
        linhas = self._db.execute("SELECT * FROM alerts WHERE closed_at IS NULL ORDER BY id")
        return [_linha_para_alert(linha) for linha in linhas]

    def list(self, device_id: str | None = None, limit: int = 100) -> list[Alert]:
        """Histórico do mais novo para o mais velho, opcionalmente de uma vinheria só."""
        if device_id is None:
            linhas = self._db.execute(
                "SELECT * FROM alerts ORDER BY opened_at DESC, id DESC LIMIT ?", (limit,))
        else:
            linhas = self._db.execute(
                "SELECT * FROM alerts WHERE device_id = ? "
                "ORDER BY opened_at DESC, id DESC LIMIT ?", (device_id, limit))
        return [_linha_para_alert(linha) for linha in linhas]
