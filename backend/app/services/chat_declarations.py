"""
Declaração das tools do chatbot para o Gemini (function calling).

Descreve nome, finalidade e parâmetros de cada tool de chat_tools.py (e,
no bloco B, de chat_acoes.py). O Gemini lê só isto para decidir qual tool
chamar, por isso as descrições dizem em português quando usar cada uma.
"""
from google.genai import types

_VINHERIA = types.Schema(
    type="STRING",
    description="Id, nome ou cidade da vinheria, do jeito que o usuário escreveu "
                "(ex.: 'São Paulo', 'Vinheria Mineira', 'vinheria002', '002').")
_ATRIBUTO = types.Schema(
    type="STRING", enum=["temperature", "humidity", "luminosity"],
    description="Sensor: temperature (temperatura, °C), humidity (umidade, %) "
                "ou luminosity (luminosidade, %).")


def _horas(padrao: int) -> types.Schema:
    """Parâmetro de janela em horas, com o padrão descrito."""
    return types.Schema(type="NUMBER",
                        description=f"Janela em horas, de 0.25 a 24. Padrão {padrao}.")


def _objeto(propriedades: dict, obrigatorios: list[str]) -> types.Schema:
    """Schema de objeto com as propriedades e as obrigatórias."""
    return types.Schema(type="OBJECT", properties=propriedades, required=obrigatorios)


LEITURA = [
    types.FunctionDeclaration(
        name="listar_vinherias",
        description="Lista todas as vinherias cadastradas com id, nome, cidade e status "
                    "(ok, alerta, offline, configurando, aguardando). Use para perguntas "
                    "sobre a frota inteira ou para descobrir qual vinheria o usuário quis dizer."),
    types.FunctionDeclaration(
        name="estado_atual",
        description="Estado atual de uma vinheria: temperatura, umidade, luminosidade, score "
                    "de qualidade, há quantos segundos chegou a última leitura e alertas ativos.",
        parameters=_objeto({"vinheria": _VINHERIA}, ["vinheria"])),
    types.FunctionDeclaration(
        name="estatisticas",
        description="Média, mínimo, máximo, desvio e tendência de um sensor de uma vinheria "
                    "nas últimas horas, a partir do histórico do STH-Comet.",
        parameters=_objeto({"vinheria": _VINHERIA, "atributo": _ATRIBUTO, "horas": _horas(1)},
                           ["vinheria", "atributo"])),
    types.FunctionDeclaration(
        name="comparar",
        description="Compara a média de um sensor entre todas as vinherias, da maior para a "
                    "menor. Use para 'qual vinheria está mais quente/úmida/clara'.",
        parameters=_objeto({"atributo": _ATRIBUTO, "horas": _horas(1)}, ["atributo"])),
    types.FunctionDeclaration(
        name="alertas",
        description="Histórico de alertas (sensor fora da faixa, vinheria offline ou FIWARE "
                    "fora do ar) nas últimas horas, de uma vinheria ou de todas.",
        parameters=_objeto({"vinheria": _VINHERIA, "horas": _horas(24)}, [])),
    types.FunctionDeclaration(
        name="limites",
        description="Faixa ideal (mínimo e máximo) de temperatura, umidade e luminosidade de "
                    "uma vinheria; é a mesma faixa que dispara os alertas.",
        parameters=_objeto({"vinheria": _VINHERIA}, ["vinheria"])),
]

# Tools de ação (bloco B): só propõem, quem executa é o painel após o Confirmar
ACOES = [
    types.FunctionDeclaration(
        name="propor_comando",
        description="Propõe disparar o padrão de alerta (luz e som) de um sensor, ou desligar o "
                    "alerta, no ESP32 de uma vinheria. NÃO executa: o usuário confirma num "
                    "cartão. Use só quando o usuário pedir explicitamente.",
        parameters=_objeto({
            "vinheria": _VINHERIA,
            "comando": types.Schema(
                type="STRING", enum=["blink_temp", "blink_hum", "blink_lux", "alert_off"],
                description="blink_temp (alerta de temperatura), blink_hum (umidade), "
                            "blink_lux (luminosidade) ou alert_off (desligar o alerta)."),
        }, ["vinheria", "comando"])),
    types.FunctionDeclaration(
        name="propor_faixa",
        description="Propõe mudar o mínimo e/ou o máximo da faixa ideal de um sensor de uma "
                    "vinheria. NÃO grava: o usuário confirma num cartão. Informe só o que mudar.",
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
