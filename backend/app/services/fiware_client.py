"""
Cliente do FIWARE — a fachada única que o resto do backend usa para falar
com a EC2.

Junta os componentes, cada um no seu módulo:
- fiware_base.py: URLs, headers e requisição HTTP (único uso de httpx);
- fiware_iota.py: IoT Agent MQTT (4041), service group e devices;
- fiware_orion.py: Orion Context Broker (1026), entidades, comandos e subscriptions;
- fiware_sth.py: STH-Comet (8666), histórico das leituras.

Aqui ficam também o teste de saúde dos três componentes e a re-exportação
das constantes, para quem importa tudo de app.services.fiware_client.
"""
import asyncio
import time

from app.models.schemas import HealthReport, ServiceHealth
from app.services.fiware_base import FiwareBase
from app.services.fiware_constants import (  # noqa: F401  (re-exportadas)
    COMMANDS,
    ENTITY_TYPE,
    HISTORY_PAGE_LIMIT,
    ORION_LIST_LIMIT,
    SENSOR_ATTRS,
)
from app.services.fiware_errors import FiwareError, FiwareUnavailable
from app.services.fiware_iota import IotaOperations
from app.services.fiware_orion import OrionOperations
from app.services.fiware_sth import SthOperations


class FiwareClient(IotaOperations, OrionOperations, SthOperations, FiwareBase):
    """Fachada assíncrona sobre as APIs REST do FIWARE."""

    async def _ping(self, service: str, url: str) -> ServiceHealth:
        """Testa um endpoint e mede a latência; nunca levanta exceção."""
        inicio = time.perf_counter()
        try:
            resposta = await self._request(service, "GET", url)
        except FiwareError as exc:
            return ServiceHealth(ok=False, status_code=exc.status_code, error=exc.message)
        latencia = int((time.perf_counter() - inicio) * 1000)
        return ServiceHealth(ok=True, status_code=resposta.status_code, latency_ms=latencia)

    async def health(self) -> HealthReport:
        """Testa Orion, IoT Agent e STH em paralelo no IP atual."""
        ec2_ip = self._config.get().ec2_ip
        try:
            urls = (
                self.orion_url("/version"),
                self.iota_url("/iot/about"),
                self.sth_url("/version"),
            )
        except FiwareUnavailable as exc:
            falha = ServiceHealth(ok=False, error=exc.message)
            return HealthReport(ok=False, ec2_ip=ec2_ip, orion=falha, iota=falha, sth=falha)
        orion, iota, sth = await asyncio.gather(
            self._ping("orion", urls[0]),
            self._ping("iota", urls[1]),
            self._ping("sth", urls[2]),
        )
        return HealthReport(ok=orion.ok and iota.ok and sth.ok, ec2_ip=ec2_ip,
                            orion=orion, iota=iota, sth=sth)
