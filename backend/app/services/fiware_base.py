"""
Base do cliente FIWARE: montagem de URLs, headers e requisição HTTP.

É aqui que o httpx é usado de fato. Os componentes (fiware_iota, fiware_orion,
fiware_sth) herdam esta base e só chamam `_request`; o FiwareClient em
fiware_client.py junta tudo numa fachada única.

As URLs são montadas a cada chamada a partir do ConfigStore, então trocar o
IP pelo painel vale na hora, sem reiniciar o backend. Falhas de rede e status
de erro viram exceções de app.services.fiware_errors.
"""
import httpx

from app.core.config import ConfigStore, Settings
from app.services.fiware_errors import (
    FiwareConflict,
    FiwareError,
    FiwareNotFound,
    FiwareUnavailable,
)


class FiwareBase:
    """Infraestrutura comum: configuração, pool HTTP, URLs e tratamento de erros."""

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
