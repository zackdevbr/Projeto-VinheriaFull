"""
Operações do STH-Comet (porta 8666): histórico das leituras.

Mixin do FiwareClient; depende de `_request` e `sth_url` de FiwareBase.
"""
from app.services.fiware_base import FiwareBase
from app.services.fiware_constants import HISTORY_PAGE_LIMIT


class SthOperations(FiwareBase):
    """Consulta de séries históricas no STH-Comet."""

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
