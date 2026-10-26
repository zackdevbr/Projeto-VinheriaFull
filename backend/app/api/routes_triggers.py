# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Rotas de controle de uma vinheria: faixa ideal (RF06) e alertas
disparados à mão pelo painel (RF09).
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_control
from app.models.schemas import Limits
from app.models.schemas_fleet import CommandRequest, CommandResult, LimitsUpdate
from app.services.device_control import DeviceControl

router = APIRouter(prefix="/api/devices", tags=["faixa e comandos"])


@router.get("/{device_id}/triggers", response_model=Limits)
def read_triggers(device_id: str, control: DeviceControl = Depends(get_control)) -> Limits:
    """Faixa ideal atual da vinheria."""
    return control.get_limits(device_id)


@router.put("/{device_id}/triggers", response_model=LimitsUpdate)
async def write_triggers(device_id: str, limits: Limits,
                         control: DeviceControl = Depends(get_control)) -> LimitsUpdate:
    """Salva a faixa (Orion e SQLite) e manda ao ESP32 na hora; offline fica pendente."""
    return await control.update_limits(device_id, limits)


@router.post("/{device_id}/commands", response_model=CommandResult, status_code=202)
async def post_command(device_id: str, body: CommandRequest,
                       control: DeviceControl = Depends(get_control)) -> CommandResult:
    """Dispara ou desliga um alerta à mão; offline ou configurando responde 409."""
    await control.send_command(device_id, body.command)
    return CommandResult(device_id=device_id, command=body.command)
