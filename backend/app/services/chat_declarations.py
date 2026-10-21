"""
Declaração das tools do chatbot para o Gemini (function calling).

Descreve nome, finalidade e parâmetros de cada tool de chat_tools.py (e,
no bloco B, de chat_acoes.py). O Gemini lê só isto para decidir qual tool
chamar. As descrições são curtas de propósito: vão em toda requisição, e
no plano gratuito cada token conta.
"""
from google.genai import types

_VINHERIA = types.Schema(
    type="STRING",
    description="Id, nome ou cidade da vinheria, como o usuário escreveu (ex.: 'São Paulo', '002').")
_ATRIBUTO = types.Schema(
    type="STRING", enum=["temperature", "humidity", "luminosity"],
    description="Sensor: temperatura, umidade ou luminosidade.")


def _horas(padrao: int) -> types.Schema:
    """Parâmetro de janela em horas, com o padrão descrito."""
    return types.Schema(type="NUMBER", description=f"Janela em horas (0.25 a 24). Padrão {padrao}.")


def _objeto(propriedades: dict, obrigatorios: list[str]) -> types.Schema:
    """Schema de objeto com as propriedades e as obrigatórias."""
    return types.Schema(type="OBJECT", properties=propriedades, required=obrigatorios)


LEITURA = [
    types.FunctionDeclaration(
        name="listar_vinherias",
        description="Lista as vinherias com id, nome, cidade e status."),
    types.FunctionDeclaration(
        name="estado_atual",
        description="Leituras atuais, score e alertas ativos de uma vinheria.",
        parameters=_objeto({"vinheria": _VINHERIA}, ["vinheria"])),
    types.FunctionDeclaration(
        name="estatisticas",
        description="Média, mínimo, máximo, desvio e tendência de um sensor de uma vinheria "
                    "nas últimas horas.",
        parameters=_objeto({"vinheria": _VINHERIA, "atributo": _ATRIBUTO, "horas": _horas(1)},
                           ["vinheria", "atributo"])),
    types.FunctionDeclaration(
        name="comparar",
        description="Média de um sensor em cada vinheria nas últimas horas, da maior para a menor.",
        parameters=_objeto({"atributo": _ATRIBUTO, "horas": _horas(1)}, ["atributo"])),
    types.FunctionDeclaration(
        name="alertas",
        description="Histórico de alertas (sensor fora da faixa, vinheria offline, FIWARE fora) "
                    "de uma vinheria ou de todas.",
        parameters=_objeto({"vinheria": _VINHERIA, "horas": _horas(24)}, [])),
    types.FunctionDeclaration(
        name="limites",
        description="Faixa ideal (mínimo e máximo) de cada sensor de uma vinheria.",
        parameters=_objeto({"vinheria": _VINHERIA}, ["vinheria"])),
]

# Tools de ação (bloco B): só propõem, quem executa é o painel após o Confirmar
ACOES = [
    types.FunctionDeclaration(
        name="propor_comando",
        description="Propõe disparar o alerta de um sensor ou desligá-lo numa vinheria. Não executa: "
                    "o usuário confirma num cartão. Só quando ele pedir.",
        parameters=_objeto({
            "vinheria": _VINHERIA,
            "comando": types.Schema(
                type="STRING", enum=["blink_temp", "blink_hum", "blink_lux", "alert_off"],
                description="blink_temp, blink_hum, blink_lux (alerta do sensor) ou alert_off (desligar)."),
        }, ["vinheria", "comando"])),
    types.FunctionDeclaration(
        name="propor_faixa",
        description="Propõe mudar o mínimo e/ou o máximo da faixa ideal de um sensor de uma vinheria. "
                    "Não grava: o usuário confirma num cartão. Informe só o que mudar.",
        parameters=_objeto({
            "vinheria": _VINHERIA,
            "atributo": _ATRIBUTO,
            "minimo": types.Schema(type="NUMBER", description="Novo mínimo, se mudar."),
            "maximo": types.Schema(type="NUMBER", description="Novo máximo, se mudar."),
        }, ["vinheria", "atributo"])),
]


def declaracoes(com_acoes: bool) -> list[types.FunctionDeclaration]:
    """Declarações enviadas ao Gemini; as de ação só com `com_acoes`."""
    return LEITURA + (ACOES if com_acoes else [])
