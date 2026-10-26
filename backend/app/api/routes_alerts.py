# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Rota do histórico de alertas (RF10), geral, de uma vinheria ou da EC2 (device_id=fiware)."""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_alert_log
from app.models.schemas_fleet import Alert
from app.services.alert_log import AlertLog

router = APIRouter(prefix="/api/alerts", tags=["alertas"])


@router.get("", response_model=list[Alert])
def list_alerts(device_id: str | None = None,
                limit: int = Query(default=100, ge=1, le=500),
                alerts: AlertLog = Depends(get_alert_log)) -> list[Alert]:
    """Alertas do mais novo para o mais velho, com início, fim e duração."""
    return alerts.list(device_id=device_id, limit=limit)
