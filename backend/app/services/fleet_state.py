# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""
Retrato da frota em memória: o status de cada vinheria e da EC2 no último
ciclo do poller.

O TriggerEngine escreve a cada ciclo e as rotas leem (GET /api/fleet,
recusa de comando para vinheria offline ou configurando). Tudo roda no loop
de eventos, então não precisa de lock.
"""
from app.models.schemas_fleet import FleetReport, VinheriaStatus


class FleetState:
    """Último VinheriaStatus de cada vinheria e o estado da EC2."""

    def __init__(self):
        self._statuses: dict[str, VinheriaStatus] = {}
        self.updated_at: str | None = None
        self.fiware_online = True
        self.fiware_offline_since: str | None = None

    def replace(self, statuses: list[VinheriaStatus], at: str, fiware_online: bool = True,
                fiware_offline_since: str | None = None) -> None:
        """Troca o retrato inteiro pelo do ciclo atual."""
        self._statuses = {status.device_id: status for status in statuses}
        self.updated_at = at
        self.fiware_online = fiware_online
        self.fiware_offline_since = fiware_offline_since

    def snapshot(self, device_ids: list[str] | None = None) -> list[VinheriaStatus]:
        """Retrato ordenado por id; com `device_ids`, só essas vinherias."""
        itens = sorted(self._statuses.values(), key=lambda status: status.device_id)
        if device_ids is None:
            return itens
        pedidos = set(device_ids)
        return [status for status in itens if status.device_id in pedidos]

    def get(self, device_id: str) -> VinheriaStatus | None:
        """Retrato de uma vinheria no último ciclo, ou None."""
        return self._statuses.get(device_id)

    def status_of(self, device_id: str) -> str | None:
        """Status da vinheria no último ciclo; None se o motor ainda não a avaliou."""
        status = self._statuses.get(device_id)
        return status.status if status else None

    def report(self, device_ids: list[str]) -> FleetReport:
        """Resposta de /api/fleet, só com as vinherias pedidas (as cadastradas)."""
        return FleetReport(fiware_online=self.fiware_online,
                           fiware_offline_since=self.fiware_offline_since,
                           updated_at=self.updated_at,
                           vinherias=self.snapshot(device_ids))
