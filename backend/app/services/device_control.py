# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Controle de uma vinheria pelo painel: faixa ideal (RF06) e alertas
disparados à mão (RF09).

A faixa vai primeiro para o Orion e só depois para o SQLite: se o FIWARE
falha, nada muda e o usuário tenta de novo. Em seguida o set_limits sai na
hora para o ESP32; se a vinheria está offline ou o envio falha, o motor é
avisado e manda no próximo ciclo em que ela estiver online.
"""
import logging

from app.models.schemas import Limits
from app.models.schemas_fleet import LimitsUpdate
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fiware_errors import FiwareError
from app.services.fleet_state import FleetState
from app.services.limits import LimitsStore, limits_to_command_value, limits_to_orion_attrs
from app.services.registry_errors import DeviceUnavailable

log = logging.getLogger(__name__)


class DeviceControl:
    """Faixa ideal e comandos manuais de uma vinheria."""

    def __init__(self, registry: DeviceRegistry, limits: LimitsStore, fiware: FiwareClient,
                 fleet: FleetState, engine):
        # engine: qualquer objeto com mark_limits_pending (o TriggerEngine)
        self._registry = registry
        self._limits = limits
        self._fiware = fiware
        self._fleet = fleet
        self._engine = engine

    def get_limits(self, device_id: str) -> Limits:
        """Faixa atual; DeviceNotFound se a vinheria não está cadastrada."""
        self._registry.get(device_id)
        return self._limits.get(device_id)

    async def update_limits(self, device_id: str, limits: Limits) -> LimitsUpdate:
        """Publica a faixa no Orion, grava no SQLite e manda o set_limits na hora."""
        device = self._registry.get(device_id)
        await self._fiware.update_attrs(device.entity_id, limits_to_orion_attrs(limits))
        self._limits.update(device_id, limits)
        enviado = False
        if self._fleet.status_of(device_id) != "offline":
            try:
                await self._fiware.send_command(device.entity_id, "set_limits",
                                                limits_to_command_value(limits))
                enviado = True
            except FiwareError as exc:
                log.warning("set_limits para %s falhou (%s); o poller tenta de novo",
                            device_id, exc.message)
        if not enviado:
            self._engine.mark_limits_pending(device_id)
        return LimitsUpdate(device_id=device_id, limits=self._limits.get(device_id),
                            device_sync="enviado" if enviado else "pendente")

    async def send_command(self, device_id: str, command: str) -> None:
        """Envia um alerta manual; offline ou configurando recusa com DeviceUnavailable."""
        device = self._registry.get(device_id)
        status = self._fleet.status_of(device_id)
        if status == "offline":
            raise DeviceUnavailable(f"{device_id} está offline e não recebe comandos")
        if status == "configurando":
            raise DeviceUnavailable(
                f"{device_id} ainda não recebeu a faixa ideal e não aceita alertas")
        await self._fiware.send_command(device.entity_id, command)
