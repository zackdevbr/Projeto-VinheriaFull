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
from app.models.schemas import Device, HealthReport, ServiceHealth
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
# Nomes longos aceitos em subscriptions e no histórico
_ATRIBUTOS_LONGOS = tuple(longo for _, longo, _ in SENSOR_ATTRS)
# Página máxima pedida ao STH quando a consulta é por intervalo de datas
HISTORY_PAGE_LIMIT = 500


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

    # ----- IoT Agent ---------------------------------------------------------

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

    # ----- Orion: escrita ----------------------------------------------------

    async def subscribe_attr(self, entity_id: str, attr: str) -> str:
        """Assina um atributo da entidade para o STH-Comet guardar o histórico.

        Uma subscription por atributo. O destino é o endereço interno do STH
        na rede Docker (STH_INTERNAL_URL). Devolve o id da subscription.
        """
        if attr not in _ATRIBUTOS_LONGOS:
            raise ValueError(f"atributo inválido: {attr!r}; use um de {_ATRIBUTOS_LONGOS}")
        corpo = {
            "description": f"Notify STH-Comet of {attr} changes",
            "subject": {
                "entities": [{"id": entity_id, "type": ENTITY_TYPE}],
                "condition": {"attrs": [attr]},
            },
            "notification": {
                "http": {"url": f"{self._settings.sth_internal_url}/notify"},
                "attrs": [attr],
                "attrsFormat": "legacy",
            },
        }
        resposta = await self._request("orion", "POST", self.orion_url("/v2/subscriptions"),
                                       json=corpo)
        # O Orion devolve o id no header Location: /v2/subscriptions/<id>
        return resposta.headers.get("Location", "").rstrip("/").split("/")[-1]

    async def send_command(self, entity_id: str, command: str, value: str = "") -> None:
        """Envia um comando à vinheria pelo Orion (que repassa ao IoT Agent).

        `value` só é usado pelo set_limits ("tmin;tmax;hmin;hmax;lmin;lmax").
        """
        if command not in COMMANDS:
            raise ValueError(f"comando inválido: {command!r}; use um de {COMMANDS}")
        corpo = {command: {"type": "command", "value": value}}
        await self._request("orion", "PATCH", self.orion_url(f"/v2/entities/{entity_id}/attrs"),
                            json=corpo)

    async def update_attrs(self, entity_id: str, attrs: dict[str, float]) -> None:
        """Cria ou atualiza atributos numéricos na entidade (ex.: faixa ideal).

        Usa POST (upsert) porque PATCH falha quando o atributo ainda não existe.
        """
        corpo = {nome: {"type": "Number", "value": valor} for nome, valor in attrs.items()}
        await self._request("orion", "POST", self.orion_url(f"/v2/entities/{entity_id}/attrs"),
                            json=corpo)

    async def delete_entity(self, entity_id: str) -> None:
        """Remove a entidade do Orion; se já não existe (404), segue."""
        await self._request("orion", "DELETE", self.orion_url(f"/v2/entities/{entity_id}"),
                            aceitar=(404,))

    async def delete_subscriptions(self, entity_id: str) -> int:
        """Apaga as subscriptions que observam esta entidade e devolve quantas foram."""
        resposta = await self._request("orion", "GET", self.orion_url("/v2/subscriptions"),
                                       params={"limit": ORION_LIST_LIMIT})
        apagadas = 0
        for assinatura in resposta.json():
            entidades = assinatura.get("subject", {}).get("entities", [])
            if any(e.get("id") == entity_id for e in entidades):
                await self._request(
                    "orion", "DELETE",
                    self.orion_url(f"/v2/subscriptions/{assinatura['id']}"),
                    aceitar=(404,),
                )
                apagadas += 1
        return apagadas

    # ----- STH-Comet ---------------------------------------------------------

    async def query_history(self, entity_type: str, entity_id: str, attr: str,
                            last_n: int | None = None,
                            date_from: str | None = None,
                            date_to: str | None = None) -> list[dict]:
        """Histórico bruto de um atributo no STH-Comet.

        Use OU last_n (últimos N pontos) OU date_from/date_to (datas ISO 8601).
        Devolve a lista `values` do STH ([{recvTime, attrValue, ...}]), ou []
        quando não há dados.
        """
        por_datas = date_from is not None or date_to is not None
        if last_n is None and not por_datas:
            raise ValueError("informe last_n ou date_from/date_to")
        if last_n is not None and por_datas:
            raise ValueError("use last_n ou date_from/date_to, não os dois")
        if last_n is not None:
            params = {"lastN": last_n}
        else:
            # Consulta por datas exige paginação explícita no STH
            params = {"hLimit": HISTORY_PAGE_LIMIT, "hOffset": 0}
            if date_from is not None:
                params["dateFrom"] = date_from
            if date_to is not None:
                params["dateTo"] = date_to
        caminho = (f"/STH/v1/contextEntities/type/{entity_type}"
                   f"/id/{entity_id}/attributes/{attr}")
        resposta = await self._request("sth", "GET", self.sth_url(caminho), params=params)
        try:
            return resposta.json()["contextResponses"][0]["contextElement"]["attributes"][0]["values"]
        except (KeyError, IndexError, TypeError):
            return []

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
