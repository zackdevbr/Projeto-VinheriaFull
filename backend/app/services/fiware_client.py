"""
Cliente HTTP do FIWARE — a única peça do backend que fala com a EC2.

Cobre os três componentes usados no projeto:
- IoT Agent MQTT (4041): service group e devices;
- Orion Context Broker (1026): entidades, comandos e subscriptions;
- STH-Comet (8666): histórico das leituras.

As URLs são montadas a cada chamada a partir do ConfigStore, então trocar o
IP pelo painel vale na hora, sem reiniciar o backend. Falhas de rede e status
de erro viram exceções de app.services.fiware_errors.
"""
import asyncio
import time

import httpx

from app.core.config import ConfigStore, Settings
from app.models.schemas import HealthReport, ServiceHealth
from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)

# Atributos de sensor: (nome curto no UltraLight, nome longo no Orion/STH, tipo)
SENSOR_ATTRS = (
    ("t", "temperature", "Float"),
    ("h", "humidity", "Float"),
    ("l", "luminosity", "Integer"),
)
# Comandos que o firmware entende
COMMANDS = ("blink_temp", "blink_hum", "blink_lux", "alert_off", "set_limits")
ENTITY_TYPE = "Vinheria"
# Máximo de itens por listagem no Orion (frota e subscriptions)
ORION_LIST_LIMIT = 1000


class FiwareClient:
    """Fachada assíncrona sobre as APIs REST do FIWARE."""

    def __init__(self, config_store: ConfigStore, settings: Settings,
                 http: httpx.AsyncClient | None = None):
        self._config = config_store
        self._settings = settings
        # Um único AsyncClient reaproveita conexões entre chamadas;
        # nos testes o respx intercepta as requisições dele.
        self._http = http or httpx.AsyncClient(timeout=settings.http_timeout_seconds)

    async def aclose(self) -> None:
        """Fecha o pool de conexões (chamado no desligamento do app)."""
        await self._http.aclose()

    # ----- URLs e requisição -------------------------------------------------

    def _base(self, campo_porta: str) -> str:
        """Monta http://<ip>:<porta> com a configuração deste instante."""
        cfg = self._config.get()
        if not cfg.ec2_ip:
            raise FiwareUnavailable(
                "config",
                "IP do FIWARE não configurado: defina FIWARE_HOST no .env "
                "ou informe o IP no painel Avançado",
            )
        return f"http://{cfg.ec2_ip}:{getattr(cfg, campo_porta)}"

    def orion_url(self, path: str) -> str:
        """URL completa de um caminho do Orion."""
        return self._base("orion_port") + path

    def iota_url(self, path: str) -> str:
        """URL completa de um caminho do IoT Agent."""
        return self._base("iota_port") + path

    def sth_url(self, path: str) -> str:
        """URL completa de um caminho do STH-Comet."""
        return self._base("sth_port") + path

    def _headers(self) -> dict[str, str]:
        """Headers de multi-tenancy exigidos por todos os componentes."""
        return {
            "fiware-service": self._settings.fiware_service,
            "fiware-servicepath": self._settings.fiware_servicepath,
        }

    async def _request(self, service: str, method: str, url: str, *,
                       aceitar: tuple[int, ...] = (), **kwargs) -> httpx.Response:
        """Faz a requisição e converte falhas em FiwareError.

        `aceitar` lista status de erro que, naquele contexto, contam como
        sucesso (ex.: 409 ao recriar o service group, 404 ao remover algo
        que já não existe).
        """
        try:
            resposta = await self._http.request(method, url, headers=self._headers(), **kwargs)
        except httpx.TimeoutException as exc:
            raise FiwareUnavailable(service, f"tempo esgotado em {url}") from exc
        except httpx.TransportError as exc:
            raise FiwareUnavailable(service, f"sem conexão com {url}: {exc}") from exc
        if resposta.is_success or resposta.status_code in aceitar:
            return resposta
        detalhe = resposta.text[:300] or resposta.reason_phrase
        if resposta.status_code == 404:
            raise FiwareNotFound(service, detalhe, 404)
        if resposta.status_code == 409:
            raise FiwareConflict(service, detalhe, 409)
        raise FiwareError(service, detalhe, resposta.status_code)

    # ----- Orion: leitura ----------------------------------------------------

    async def get_entity(self, entity_id: str) -> dict:
        """Estado atual de uma entidade, no formato simplificado keyValues."""
        resposta = await self._request(
            "orion", "GET", self.orion_url(f"/v2/entities/{entity_id}"),
            params={"options": "keyValues"},
        )
        return resposta.json()

    async def list_entities(self, entity_type: str = ENTITY_TYPE) -> list[dict]:
        """Todas as entidades de um tipo numa única chamada (usado pelo poller).

        O TimeInstant vem junto quando o service group tem timestamp: true.
        """
        resposta = await self._request(
            "orion", "GET", self.orion_url("/v2/entities"),
            params={"type": entity_type, "options": "keyValues", "limit": ORION_LIST_LIMIT},
        )
        return resposta.json()

    # ----- Saúde -------------------------------------------------------------

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
