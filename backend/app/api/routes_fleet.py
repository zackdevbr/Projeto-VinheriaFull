"""Rota da visão geral da frota (RF12): estado da EC2 e de todas as vinherias."""
from fastapi import APIRouter, Depends

from app.api.deps import get_fleet, get_registry
from app.models.schemas_fleet import FleetReport
from app.services.device_registry import DeviceRegistry
from app.services.fleet_state import FleetState

router = APIRouter(prefix="/api/fleet", tags=["frota"])


@router.get("", response_model=FleetReport)
async def read_fleet(fleet: FleetState = Depends(get_fleet),
                     registry: DeviceRegistry = Depends(get_registry)) -> FleetReport:
    """Retrato do último ciclo do poller, só das vinherias ainda cadastradas.

    Uma vinheria recém-cadastrada aparece no ciclo seguinte (até poll_seconds).
    """
    return fleet.report([device.device_id for device in registry.list()])
