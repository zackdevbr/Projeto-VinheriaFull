"""
Rotas de dados de uma vinheria: estado atual, histórico e score de qualidade.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_readings
from app.models.schemas import CurrentReading, HistoryPoint, HistoryQuery, ScoreReport
from app.services.readings import ReadingsService

router = APIRouter(prefix="/api/devices", tags=["dados"])


@router.get("/{device_id}/current", response_model=CurrentReading)
async def read_current(device_id: str,
                       readings: ReadingsService = Depends(get_readings)) -> CurrentReading:
    """Valores atuais; null quando a vinheria ainda não mandou leitura."""
    return await readings.current(device_id)


@router.get("/{device_id}/history", response_model=list[HistoryPoint])
async def read_history(device_id: str, query: Annotated[HistoryQuery, Query()],
                       readings: ReadingsService = Depends(get_readings)) -> list[HistoryPoint]:
    """Histórico de um atributo: last_n (1–500) ou date_from/date_to."""
    return await readings.history(device_id, query)


@router.get("/{device_id}/score", response_model=ScoreReport)
async def read_score(device_id: str,
                     readings: ReadingsService = Depends(get_readings)) -> ScoreReport:
    """Score de qualidade (0–100); se indisponível, traz o motivo em `message`."""
    return await readings.score(device_id)
