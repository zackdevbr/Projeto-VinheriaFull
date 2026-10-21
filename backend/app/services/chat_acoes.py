"""
Tools de ação do chatbot (bloco B da Task 7A): só PROPÕEM.

Validam o pedido (vinheria, comando, faixa) e acrescentam um ChatAction à
lista da pergunta. Nada vai para o FIWARE nem para o SQLite aqui: o painel
mostra o cartão e, no Confirmar, executa pelas rotas de comando e de faixa,
que já recusam vinheria offline e validam a faixa.
"""
from pydantic import ValidationError

from app.models.schemas import AttrLimits
from app.models.schemas_chat import ChatAction
from app.services.chat_stats import NOME_ATRIBUTO, UNIDADE
from app.services.chat_tools import checar_atributo, resolver

# Comandos que o assistente pode propor e como aparecem no cartão
DESCRICAO_COMANDO = {
    "blink_temp": "Piscar o alerta de temperatura",
    "blink_hum": "Piscar o alerta de umidade",
    "blink_lux": "Piscar o alerta de luminosidade",
    "alert_off": "Desligar o alerta",
}
# Status em que a vinheria não recebe comando (mesma regra do DeviceControl)
BLOQUEIO = {
    "offline": "{name} está offline e não recebe comandos agora",
    "configurando": "{name} ainda não recebeu a faixa ideal e não aceita alertas",
}


def _numero(valor) -> str:
    """Número sem ".0" sobrando (18 em vez de 18.0)."""
    return f"{valor:g}"


def _resumo_faixa(atributo: str, antes: AttrLimits, depois: AttrLimits, nome: str) -> str:
    """Ex.: "Temperatura máx. 18 → 20 °C na Vinheria Paulista"."""
    unidade = UNIDADE[atributo]
    partes = []
    if depois.min != antes.min:
        partes.append(f"mín. {_numero(antes.min)} → {_numero(depois.min)} {unidade}")
    if depois.max != antes.max:
        partes.append(f"máx. {_numero(antes.max)} → {_numero(depois.max)} {unidade}")
    mudanca = ", ".join(partes) or "sem mudança"
    return f"{NOME_ATRIBUTO[atributo].capitalize()} {mudanca} na {nome}"


class ChatAcoes:
    """Propostas de comando e de faixa, aguardando o Confirmar do painel."""

    def __init__(self, registry, fleet, limits):
        self._registry = registry
        self._fleet = fleet
        self._limits = limits

    def registrar_em(self, tools) -> None:
        """Acrescenta as duas tools de proposta ao ChatTools."""
        tools.registrar("propor_comando", self.propor_comando, recebe_propostas=True)
        tools.registrar("propor_faixa", self.propor_faixa, recebe_propostas=True)

    async def propor_comando(self, vinheria: str, comando: str, propostas: list) -> dict:
        """Propõe disparar ou desligar o alerta de uma vinheria."""
        if comando not in DESCRICAO_COMANDO:
            return {"erro": f"comando inválido: {comando}; use blink_temp, blink_hum, "
                            "blink_lux ou alert_off"}
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        bloqueio = BLOQUEIO.get(self._fleet.status_of(device.device_id))
        if bloqueio:
            return {"erro": bloqueio.format(name=device.name)}
        resumo = f"{DESCRICAO_COMANDO[comando]} ({comando}) na {device.name}"
        propostas.append(ChatAction(kind="command", device_id=device.device_id,
                                    name=device.name, summary=resumo, command=comando))
        return {"proposta": resumo, "aguardando_confirmacao": True}

    async def propor_faixa(self, vinheria: str, atributo: str, propostas: list,
                           minimo=None, maximo=None) -> dict:
        """Propõe mudar o mínimo e/ou o máximo da faixa ideal de um atributo."""
        erro = checar_atributo(atributo)
        if erro:
            return erro
        if minimo is None and maximo is None:
            return {"erro": "informe o novo mínimo, o novo máximo ou os dois"}
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        atual = self._limits.get(device.device_id)
        antes = getattr(atual, atributo)
        try:
            depois = AttrLimits(min=antes.min if minimo is None else float(minimo),
                                max=antes.max if maximo is None else float(maximo))
        except (ValidationError, ValueError, TypeError):
            return {"erro": f"faixa inválida: o mínimo precisa ser menor que o máximo "
                            f"(atual: {_numero(antes.min)} a {_numero(antes.max)} {UNIDADE[atributo]})"}
        resumo = _resumo_faixa(atributo, antes, depois, device.name)
        propostas.append(ChatAction(kind="limits", device_id=device.device_id, name=device.name,
                                    summary=resumo, limits=atual.model_copy(update={atributo: depois})))
        return {"proposta": resumo, "aguardando_confirmacao": True}
