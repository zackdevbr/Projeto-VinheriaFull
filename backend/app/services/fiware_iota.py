"""
Operações do IoT Agent MQTT (porta 4041): service group e devices.

Mixin do FiwareClient; depende de `_request`, `iota_url` e `orion_url`
fornecidos por FiwareBase.
"""
from app.models.schemas import Device
from app.services.fiware_base import FiwareBase
from app.services.fiware_constants import COMMANDS, ENTITY_TYPE, SENSOR_ATTRS


class IotaOperations(FiwareBase):
    """Provisionamento de service group e devices no IoT Agent."""

    async def provision_service_group(self) -> None:
        """Cria o service group da apikey do projeto; se já existe (409), segue.

        timestamp: true faz o IoT Agent preencher TimeInstant a cada leitura,
        e a detecção de offline depende disso.
        """
        corpo = {"services": [{
            "apikey": self._settings.fiware_apikey,
            "cbroker": self.orion_url(""),
            "entity_type": "Thing",
            "resource": "",
            "timestamp": True,
        }]}
        await self._request("iota", "POST", self.iota_url("/iot/services"),
                            json=corpo, aceitar=(409,))

    async def provision_device(self, device: Device) -> None:
        """Provisiona a vinheria no IoT Agent com atributos e comandos.

        O próprio IoT Agent cria a registration dos comandos no Orion; criar
        outra à mão duplica e quebra o encaminhamento (achado da Task 1).
        Device já existente levanta FiwareConflict.
        """
        corpo = {"devices": [{
            "device_id": device.device_id,
            "entity_name": device.entity_id,
            "entity_type": ENTITY_TYPE,
            "protocol": "PDI-IoTA-UltraLight",
            "transport": "MQTT",
            "commands": [{"name": nome, "type": "command"} for nome in COMMANDS],
            "attributes": [
                {"object_id": curto, "name": longo, "type": tipo}
                for curto, longo, tipo in SENSOR_ATTRS
            ],
        }]}
        await self._request("iota", "POST", self.iota_url("/iot/devices"), json=corpo)

    async def delete_device(self, device_id: str) -> None:
        """Remove o device do IoT Agent; se já não existe (404), segue."""
        await self._request("iota", "DELETE", self.iota_url(f"/iot/devices/{device_id}"),
                            aceitar=(404,))
