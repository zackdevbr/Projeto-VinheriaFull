"""
Rotas do cadastro de vinherias: cadastrar (com provisionamento no FIWARE),
listar, consultar com a faixa ideal e remover.
"""
from fastapi import APIRouter, Depends, Response

from app.api.deps import get_registry
from app.models.schemas import Device, DeviceCreate, DeviceDetail
from app.services.device_registry import DeviceRegistry

router = APIRouter(prefix="/api/devices", tags=["vinherias"])


@router.post("", response_model=Device, status_code=201)
async def create_device(data: DeviceCreate,
                        registry: DeviceRegistry = Depends(get_registry)) -> Device:
    """Cadastra a vinheria e a provisiona no FIWARE (re-provisiona se já existir lá)."""
    return await registry.create(data)


@router.get("", response_model=list[Device])
def list_devices(registry: DeviceRegistry = Depends(get_registry)) -> list[Device]:
    """Vinherias cadastradas, ordenadas pelo id."""
    return registry.list()


@router.get("/{device_id}", response_model=DeviceDetail)
def read_device(device_id: str,
                registry: DeviceRegistry = Depends(get_registry)) -> DeviceDetail:
    """Uma vinheria com a faixa ideal configurada."""
    return registry.detail(device_id)


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: str,
                        registry: DeviceRegistry = Depends(get_registry)) -> Response:
    """Remove a vinheria do FIWARE e do cadastro local (o histórico do STH fica)."""
    await registry.delete(device_id)
    return Response(status_code=204)
