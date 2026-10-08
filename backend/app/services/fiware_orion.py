"""
Operações do Orion Context Broker (porta 1026): leitura, subscriptions,
comandos, atributos e remoção de entidades.

Mixin do FiwareClient; depende de `_request` e `orion_url` de FiwareBase.
"""
from app.services.fiware_base import FiwareBase
from app.services.fiware_constants import (
    ATRIBUTOS_LONGOS,
    COMMANDS,
    ENTITY_TYPE,
    ORION_LIST_LIMIT,
)


class OrionOperations(FiwareBase):
    """Consulta e escrita de entidades no Orion."""

    # ----- leitura -----------------------------------------------------------

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

    # ----- escrita -----------------------------------------------------------

    async def subscribe_attr(self, entity_id: str, attr: str) -> str:
        """Assina um atributo da entidade para o STH-Comet guardar o histórico.

        Uma subscription por atributo. O destino é o endereço interno do STH
        na rede Docker (STH_INTERNAL_URL). Devolve o id da subscription.
        """
        if attr not in ATRIBUTOS_LONGOS:
            raise ValueError(f"atributo inválido: {attr!r}; use um de {ATRIBUTOS_LONGOS}")
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

        Usa POST /v2/op/update com actionType append, que cria a entidade se
        ela ainda não estiver armazenada. Logo após o provisionamento, a
        entidade só existe pela registration do IoT Agent até a primeira
        leitura, e POST /v2/entities/<id>/attrs responde 404 (verificado na
        EC2 em 07/10/2026). Repetir a chamada é seguro.
        """
        entidade = {"id": entity_id, "type": ENTITY_TYPE}
        entidade.update(
            {nome: {"type": "Number", "value": valor} for nome, valor in attrs.items()})
        await self._request("orion", "POST", self.orion_url("/v2/op/update"),
                            json={"actionType": "append", "entities": [entidade]})

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
