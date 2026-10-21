"""Testes do chatbot: resumo da frota e loop de function calling (spec R6)."""
from datetime import timezone
from types import SimpleNamespace

import pytest
from google.genai import errors, types

from app.core.config import Settings
from app.models.schemas import Device
from app.models.schemas_chat import ChatAction, ChatTurn
from app.models.schemas_fleet import ActiveAlert, FleetReport
from app.services.chat_errors import ChatbotRateLimited, ChatbotUnavailable, ChatbotUpstreamError
from app.services.chatbot import MAX_CHAMADAS, SEM_CONCLUSAO, Chatbot, resumo_frota
from app.services.fleet_state import FleetState
from tests.fakes import status_vinheria

DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria Paulista", city="São Paulo")


def _status(device_id, status, name, alertas=()):
    return status_vinheria(device_id, status).model_copy(update={
        "name": name, "active_alerts": [ActiveAlert(attr=a, since="2026-10-08T11:00:00+00:00")
                                        for a in alertas]})


def test_resumo_tudo_normal():
    report = FleetReport(fiware_online=True, vinherias=[
        _status("vinheria001", "ok", "Vinheria Paulista"),
        _status("vinheria002", "ok", "Vinheria Mineira")])
    assert resumo_frota(report) == "Situação agora: FIWARE ok; 2 vinherias, todas normais."


def test_resumo_com_alerta_offline_e_configurando():
    report = FleetReport(fiware_online=True, vinherias=[
        _status("vinheria001", "ok", "Vinheria Paulista"),
        _status("vinheria002", "alerta", "Vinheria Mineira", ["temperature", "humidity"]),
        _status("vinheria003", "offline", "Vinheria Sul"),
        _status("vinheria004", "configurando", "Vinheria Norte")])
    assert resumo_frota(report) == (
        "Situação agora: FIWARE ok; 4 vinherias; "
        "vinheria002 (Vinheria Mineira) em alerta de temperatura, umidade; "
        "vinheria003 (Vinheria Sul) offline; "
        "vinheria004 (Vinheria Norte) aguardando a faixa (configurando).")


def test_resumo_fiware_fora():
    report = FleetReport(fiware_online=False, fiware_offline_since="2026-10-08T11:30:00+00:00",
                         vinherias=[_status("vinheria001", "offline", "Vinheria Paulista")])
    assert resumo_frota(report, fuso=timezone.utc) == (
        "Situação agora: FIWARE fora do ar desde 08/10 11:30; "
        "os dados das vinherias podem estar desatualizados.")


def test_resumo_sem_vinherias():
    report = FleetReport(fiware_online=True, vinherias=[])
    assert resumo_frota(report) == "Situação agora: FIWARE ok; nenhuma vinheria cadastrada."


class ModelsFalso:
    """Faz o papel de client.aio.models: devolve respostas roteirizadas."""

    def __init__(self, roteiro):
        self.roteiro = list(roteiro)
        self.chamadas = []

    async def generate_content(self, model, contents, config):
        self.chamadas.append({"model": model, "contents": list(contents), "config": config})
        item = self.roteiro.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def cliente(*roteiro):
    return SimpleNamespace(aio=SimpleNamespace(models=ModelsFalso(roteiro)))


def texto(conteudo):
    """Resposta final do Gemini, só com texto."""
    return SimpleNamespace(function_calls=None, text=conteudo, candidates=[])


def pede(*chamadas):
    """Resposta do Gemini pedindo tools: chamadas = [(nome, args), ...]."""
    fcs = [types.FunctionCall(name=nome, args=args) for nome, args in chamadas]
    conteudo = types.Content(role="model", parts=[types.Part(function_call=fc) for fc in fcs])
    return SimpleNamespace(function_calls=fcs, text=None,
                           candidates=[SimpleNamespace(content=conteudo)])


class ToolsFalso:
    """Registra as tools executadas; 'propor' acrescenta uma proposta."""

    def __init__(self):
        self.execucoes = []

    async def executar(self, nome, args, propostas):
        self.execucoes.append((nome, args))
        if nome == "propor":
            propostas.append(ChatAction(kind="command", device_id="vinheria001",
                                        name="Vinheria Paulista", summary="Piscar a luz",
                                        command="blink_lux"))
        return {"ok": nome}


class RegistryFalso:
    def list(self):
        return [DEVICE]


@pytest.fixture
def tools_falso():
    return ToolsFalso()


def chatbot(tools, client, chave="chave-de-teste"):
    return Chatbot(tools, RegistryFalso(), FleetState(), Settings(gemini_api_key=chave), client=client)


def _textos(conteudo):
    return [p.text for p in conteudo.parts if p.text]


@pytest.mark.anyio
async def test_sem_chave_fica_indisponivel(tools_falso):
    with pytest.raises(ChatbotUnavailable):
        await chatbot(tools_falso, cliente(texto("x")), chave="").ask("oi", [])


@pytest.mark.anyio
async def test_resposta_direta_leva_resumo_e_historico(tools_falso):
    c = cliente(texto("Tudo certo."))
    historico = [ChatTurn(role="user", text="oi"), ChatTurn(role="model", text="olá")]
    r = await chatbot(tools_falso, c).ask("Como está a 001?", historico)
    assert (r.reply, r.actions) == ("Tudo certo.", [])
    chamada = c.aio.models.chamadas[0]
    assert chamada["model"] == "gemini-3.5-flash"
    assert [x.role for x in chamada["contents"]] == ["user", "model", "user"]
    ultima = _textos(chamada["contents"][-1])[0]
    assert ultima.startswith("[Situação agora: FIWARE ok;")
    assert ultima.endswith("Como está a 001?")
    assert chamada["config"].system_instruction


@pytest.mark.anyio
async def test_resumo_antes_do_primeiro_ciclo_do_poller(tools_falso):
    # Cadastrada mas ainda sem retrato da frota: não pode dizer "nenhuma vinheria"
    c = cliente(texto("ok"))
    await chatbot(tools_falso, c).ask("oi", [])
    ultima = _textos(c.aio.models.chamadas[0]["contents"][-1])[0]
    assert "ainda sem leitura do poller" in ultima
    assert "nenhuma vinheria" not in ultima


@pytest.mark.anyio
async def test_executa_tool_e_devolve_resultado(tools_falso):
    c = cliente(pede(("estado_atual", {"vinheria": "SP"})), texto("Está a 14 °C."))
    r = await chatbot(tools_falso, c).ask("Como está SP?", [])
    assert r.reply == "Está a 14 °C."
    assert tools_falso.execucoes == [("estado_atual", {"vinheria": "SP"})]
    resposta_tool = c.aio.models.chamadas[1]["contents"][-1].parts[0].function_response
    assert (resposta_tool.name, resposta_tool.response) == ("estado_atual", {"ok": "estado_atual"})


@pytest.mark.anyio
async def test_duas_tools_na_mesma_resposta(tools_falso):
    c = cliente(pede(("estado_atual", {"vinheria": "001"}), ("limites", {"vinheria": "001"})),
                texto("ok"))
    await chatbot(tools_falso, c).ask("estado e faixa da 001", [])
    assert [n for n, _ in tools_falso.execucoes] == ["estado_atual", "limites"]
    partes = c.aio.models.chamadas[1]["contents"][-1].parts
    assert [p.function_response.name for p in partes] == ["estado_atual", "limites"]


@pytest.mark.anyio
async def test_para_no_limite_de_chamadas(tools_falso):
    c = cliente(*[pede(("listar_vinherias", {}))] * MAX_CHAMADAS)
    r = await chatbot(tools_falso, c).ask("loop", [])
    assert r.reply == SEM_CONCLUSAO
    assert len(c.aio.models.chamadas) == MAX_CHAMADAS


@pytest.mark.anyio
async def test_propostas_voltam_em_actions(tools_falso):
    c = cliente(pede(("propor", {})), texto("Proposta pronta."))
    r = await chatbot(tools_falso, c).ask("pisque a luz da 001", [])
    assert [a.command for a in r.actions] == ["blink_lux"]


@pytest.mark.anyio
async def test_resposta_vazia_vira_mensagem_padrao(tools_falso):
    r = await chatbot(tools_falso, cliente(texto("  "))).ask("?", [])
    assert r.reply.startswith("Não encontrei uma resposta")


@pytest.mark.anyio
async def test_limite_do_gemini_vira_rate_limited(tools_falso):
    erro = errors.APIError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    with pytest.raises(ChatbotRateLimited):
        await chatbot(tools_falso, cliente(erro)).ask("oi", [])


@pytest.mark.anyio
async def test_outro_erro_do_gemini_vira_upstream(tools_falso):
    erro = errors.APIError(500, {"error": {"code": 500, "message": "interno", "status": "INTERNAL"}})
    with pytest.raises(ChatbotUpstreamError):
        await chatbot(tools_falso, cliente(erro)).ask("oi", [])


@pytest.mark.anyio
async def test_sem_internet_vira_upstream(tools_falso):
    with pytest.raises(ChatbotUpstreamError) as exc:
        await chatbot(tools_falso, cliente(ConnectionError("rede caiu"))).ask("oi", [])
    assert "chave-de-teste" not in exc.value.message
