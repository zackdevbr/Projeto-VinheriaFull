# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes das declarações das tools para o Gemini (spec R5)."""
from app.services.chat_declarations import declaracoes
from app.services.chat_tools import ChatTools

LEITURA = {"listar_vinherias", "estado_atual", "estatisticas", "comparar", "alertas", "limites"}


def _por_nome(lista):
    return {d.name: d for d in lista}


def test_declaracoes_de_leitura():
    assert set(_por_nome(declaracoes(com_acoes=False))) == LEITURA


def test_cada_declaracao_tem_tool():
    tools = ChatTools(None, None, None, None, None)
    assert {d.name for d in declaracoes(com_acoes=True)} <= tools.nomes() | {"propor_comando", "propor_faixa"}
    assert LEITURA <= tools.nomes()


def test_atributo_e_enum_dos_tres_sensores():
    estat = _por_nome(declaracoes(com_acoes=False))["estatisticas"]
    assert estat.parameters.properties["atributo"].enum == ["temperature", "humidity", "luminosity"]
    assert estat.parameters.required == ["vinheria", "atributo"]


def test_descricoes_em_portugues():
    for declaracao in declaracoes(com_acoes=False):
        assert declaracao.description and "vinheria" in declaracao.description.lower()


def test_declaracoes_de_acao_so_com_acoes():
    nomes = {d.name for d in declaracoes(com_acoes=True)}
    assert nomes == LEITURA | {"propor_comando", "propor_faixa"}
    comando = _por_nome(declaracoes(com_acoes=True))["propor_comando"]
    assert comando.parameters.properties["comando"].enum == ["blink_temp", "blink_hum", "blink_lux", "alert_off"]
