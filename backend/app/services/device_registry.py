"""
Cadastro de vinherias: SQLite local + provisionamento no FIWARE.

O FIWARE vem primeiro e o SQLite por último. Cada etapa no FIWARE pode ser
repetida sem efeito colateral (409/404 aceitos, subscriptions recriadas),
então, se algo falha no meio, nada fica gravado localmente e basta tentar
de novo. Device que já existe no IoT Agent é removido e provisionado de
novo, para ganhar a configuração completa (inclusive set_limits): o IoT
Agent não deixa acrescentar comandos a um device existente.
"""
import sqlite3
from datetime import datetime, timezone

from app.models.schemas import Device, DeviceCreate, DeviceDetail
from app.services.fiware_client import FiwareClient
from app.services.fiware_constants import ATRIBUTOS_LONGOS
from app.services.limits import DEFAULT_LIMITS, LimitsStore, limits_to_orion_attrs
from app.services.registry_errors import DeviceAlreadyExists, DeviceNotFound

ENTITY_PREFIX = "urn:ngsi-ld:Vinheria:"


def entity_id_for(device_id: str) -> str:
    """Deriva o id da entidade no Orion: vinheria001 -> urn:ngsi-ld:Vinheria:001."""
    return ENTITY_PREFIX + device_id.removeprefix("vinheria")


def _linha_para_device(linha: sqlite3.Row) -> Device:
    """Converte uma linha da tabela devices no modelo Device."""
    return Device(device_id=linha["device_id"], entity_id=linha["entity_id"],
                  name=linha["name"], city=linha["city"], created_at=linha["created_at"])


class DeviceRegistry:
    """Cadastro, consulta e remoção das vinherias."""

    def __init__(self, conn: sqlite3.Connection, fiware: FiwareClient, limits: LimitsStore):
        self._conn = conn
        self._fiware = fiware
        self._limits = limits

    async def create(self, data: DeviceCreate) -> Device:
        """Provisiona a vinheria no FIWARE e só então grava device e faixa no SQLite."""
        if self._exists(data.device_id):
            raise DeviceAlreadyExists(f"{data.device_id} já está cadastrada")
        device = Device(
            device_id=data.device_id,
            entity_id=entity_id_for(data.device_id),
            name=data.name,
            city=data.city,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        await self._fiware.provision_service_group()
        # Remove antes de provisionar: re-provisiona quem já existe (adoção)
        await self._fiware.delete_device(device.device_id)
        await self._fiware.provision_device(device)
        # Recria as subscriptions do STH sem deixar duplicatas
        await self._fiware.delete_subscriptions(device.entity_id)
        for attr in ATRIBUTOS_LONGOS:
            await self._fiware.subscribe_attr(device.entity_id, attr)
        # A entidade já existe logo após o provisionamento (fato F1 da spec)
        await self._fiware.update_attrs(device.entity_id, limits_to_orion_attrs(DEFAULT_LIMITS))
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (device.device_id, device.entity_id, device.name, device.city,
                     device.created_at),
                )
                self._limits.seed_defaults(device.device_id)
        except sqlite3.IntegrityError as exc:
            # Outro cadastro do mesmo id gravou entre a checagem e o INSERT
            raise DeviceAlreadyExists(f"{data.device_id} já está cadastrada") from exc
        return device

    def list(self) -> list[Device]:
        """Todas as vinherias cadastradas, ordenadas pelo id."""
        linhas = self._conn.execute("SELECT * FROM devices ORDER BY device_id")
        return [_linha_para_device(linha) for linha in linhas]

    def get(self, device_id: str) -> Device:
        """Uma vinheria pelo id; DeviceNotFound se não estiver cadastrada."""
        linha = self._conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if linha is None:
            raise DeviceNotFound(f"{device_id} não está cadastrada")
        return _linha_para_device(linha)

    def detail(self, device_id: str) -> DeviceDetail:
        """Vinheria com a faixa ideal configurada."""
        device = self.get(device_id)
        return DeviceDetail(**device.model_dump(), limits=self._limits.get(device_id))

    async def delete(self, device_id: str) -> None:
        """Remove a vinheria do FIWARE e depois do SQLite.

        Ordem: subscriptions, device no IoT Agent e entidade no Orion (404
        aceito; remover o device já costuma apagar a entidade). Os triggers
        saem em cascata; os alertas ficam, pois o histórico sobrevive. Se o
        FIWARE falhar, o cadastro local fica para uma nova tentativa.
        """
        device = self.get(device_id)
        await self._fiware.delete_subscriptions(device.entity_id)
        await self._fiware.delete_device(device.device_id)
        await self._fiware.delete_entity(device.entity_id)
        with self._conn:
            self._conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))

    def _exists(self, device_id: str) -> bool:
        """True se o id já está no SQLite."""
        return self._conn.execute(
            "SELECT 1 FROM devices WHERE device_id = ?", (device_id,)).fetchone() is not None
