"""Testes do chatbot: resumo da frota e loop de function calling (spec R6)."""
from datetime import timezone
from types import SimpleNamespace

import pytest
from google.genai import errors, types

from app.core.config import Settings
from app.models.schemas import Device
from app.models.schemas_chat import ChatAction, ChatTurn
from app.models.schemas_fleet import ActiveAlert, FleetReport, SensorValues
from app.services.chat_errors import ChatbotRateLimited, ChatbotUnavailable, ChatbotUpstreamError
from app.services.chatbot import MAX_CHAMADAS, SEM_CONCLUSAO, Chatbot, leituras_frota, resumo_frota
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


def _com_leitura(device_id, status, name, city, t, h, l, score=None):
    return status_vinheria(device_id, status).model_copy(update={
        "name": name, "city": city, "score": score,
        "current": SensorValues(temperature=t, humidity=h, luminosity=l)})


def test_leituras_das_vinherias_online():
    report = FleetReport(fiware_online=True, vinherias=[
        _com_leitura("vinheria001", "ok", "Vinheria Paulista", "São Paulo", 14.2, 62, 20, score=92),
        _com_leitura("vinheria002", "alerta", "Vinheria Mineira", "Belo Horizonte", 21.5, None, 10),
        _com_leitura("vinheria003", "offline", "Vinheria Sul", "Porto Alegre", 10, 50, 5)])
    assert leituras_frota(report) == (
        "Leituras agora: vinheria001 (Vinheria Paulista, São Paulo): 14.2 °C, 62 %, luz 20 %, score 92; "
        "vinheria002 (Vinheria Mineira, Belo Horizonte): 21.5 °C, n/d %, luz 10 %.")


def test_leituras_vazias_quando_nao_ha_o_que_citar():
    assert leituras_frota(FleetReport(fiware_online=True, vinherias=[])) == ""
    offline = FleetReport(fiware_online=True, vinherias=[_com_leitura("vinheria001", "offline", "V", "C", 1, 1, 1)])
    assert leituras_frota(offline) == ""
    fiware_fora = FleetReport(fiware_online=False, vinherias=[_com_leitura("vinheria001", "ok", "V", "C", 1, 1, 1)])
    assert leituras_frota(fiware_fora) == ""


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


def test_cliente_real_tem_timeout_e_sem_retry_do_sdk(monkeypatch, tools_falso):
    # O SDK repete 503 por conta própria e o chat ficaria minutos em "Pensando…"
    capturado = {}

    class ClienteFalso:
        def __init__(self, **kwargs):
            capturado.update(kwargs)

    monkeypatch.setattr("app.services.chatbot.genai.Client", ClienteFalso)
    bot = Chatbot(tools_falso, RegistryFalso(), FleetState(), Settings(gemini_api_key="k"))
    bot._cliente()
    assert capturado["api_key"] == "k"
    assert capturado["http_options"].timeout == 30000
    assert capturado["http_options"].retry_options.attempts == 1


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
    assert chamada["model"] == "gemini-3.5-flash-lite"
    assert [x.role for x in chamada["contents"]] == ["user", "model", "user"]
    ultima = _textos(chamada["contents"][-1])[0]
    assert ultima.startswith("[Situação agora: FIWARE ok;")
    assert ultima.endswith("Como está a 001?")
    assert chamada["config"].system_instruction


@pytest.mark.anyio
async def test_pergunta_leva_as_leituras_atuais_e_economiza_tokens(tools_falso):
    # Leituras no contexto = estado atual sem ferramenta (1 chamada em vez de 2+);
    # pensamento mínimo e teto de saída poupam tokens
    fleet = FleetState()
    fleet.replace([_com_leitura("vinheria001", "ok", "Vinheria Paulista", "São Paulo", 14.2, 62, 20)],
                  at="2026-10-08T12:00:00+00:00")
    c = cliente(texto("ok"))
    await Chatbot(tools_falso, RegistryFalso(), fleet, Settings(gemini_api_key="k"), client=c).ask("oi", [])
    chamada = c.aio.models.chamadas[0]
    ultima = _textos(chamada["contents"][-1])[0]
    assert "Leituras agora: vinheria001 (Vinheria Paulista, São Paulo): 14.2 °C, 62 %, luz 20 %" in ultima
    assert chamada["config"].thinking_config.thinking_level == types.ThinkingLevel.MINIMAL
    assert chamada["config"].max_output_tokens == 500


@pytest.mark.anyio
async def test_resumo_antes_do_primeiro_ciclo_do_poller(tools_falso):
    # Cadastrada mas ainda sem retrato da frota: não pode dizer "nenhuma vinheria"
    c = cliente(texto("ok"))
    await chatbot(tools_falso, c).ask("oi", [])
    ultima = _textos(c.aio.models.chamadas[0]["contents"][-1])[0]
    assert "ainda sem leitura do poller" in ultima
    assert "nenhuma vinheria" not in ultima


@pytest.mark.anyio
async def test_com_acoes_declara_e_instrui(tools_falso):
    c = cliente(texto("ok"))
    bot = Chatbot(tools_falso, RegistryFalso(), FleetState(), Settings(gemini_api_key="k"),
                  client=c, com_acoes=True)
    await bot.ask("oi", [])
    config = c.aio.models.chamadas[0]["config"]
    nomes = {d.name for d in config.tools[0].function_declarations}
    assert {"propor_comando", "propor_faixa"} <= nomes
    assert "confirm" in config.system_instruction.lower()


@pytest.mark.anyio
async def test_sem_acoes_nao_declara_propostas(tools_falso):
    c = cliente(texto("ok"))
    await chatbot(tools_falso, c).ask("oi", [])
    config = c.aio.models.chamadas[0]["config"]
    nomes = {d.name for d in config.tools[0].function_declarations}
    assert not {"propor_comando", "propor_faixa"} & nomes


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


def erro_429_com_espera(segundos):
    detalhes = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": f"{segundos}s"}]
    return errors.APIError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED",
                                           "details": detalhes}})


@pytest.mark.anyio
async def test_cota_diaria_esgotada_diz_quanto_esperar(tools_falso):
    # 31781 s = 8 h 49 min 41 s (arredondado ao minuto: 8 h 50 min); não pode dizer "alguns segundos"
    with pytest.raises(ChatbotRateLimited) as exc:
        await chatbot(tools_falso, cliente(erro_429_com_espera(31781))).ask("oi", [])
    assert "8 h 50 min" in exc.value.message
    assert "GEMINI_MODEL" in exc.value.message
    assert "alguns segundos" not in exc.value.message


@pytest.mark.anyio
async def test_limite_curto_continua_pedindo_alguns_segundos(tools_falso):
    with pytest.raises(ChatbotRateLimited) as exc:
        await chatbot(tools_falso, cliente(erro_429_com_espera(12))).ask("oi", [])
    assert "alguns segundos" in exc.value.message


@pytest.mark.anyio
async def test_outro_erro_do_gemini_vira_upstream(tools_falso):
    erro = errors.APIError(500, {"error": {"code": 500, "message": "interno", "status": "INTERNAL"}})
    with pytest.raises(ChatbotUpstreamError):
        await chatbot(tools_falso, cliente(erro)).ask("oi", [])


def erro_503():
    return errors.APIError(503, {"error": {"code": 503, "message": "alta demanda", "status": "UNAVAILABLE"}})


def chatbot_sem_espera(tools, client, esperas=(0, 0)):
    return Chatbot(tools, RegistryFalso(), FleetState(), Settings(gemini_api_key="chave-de-teste"),
                   client=client, esperas=esperas)


@pytest.mark.anyio
async def test_503_tenta_de_novo_e_responde(tools_falso):
    c = cliente(erro_503(), texto("Passou."))
    r = await chatbot_sem_espera(tools_falso, c).ask("oi", [])
    assert r.reply == "Passou."
    assert len(c.aio.models.chamadas) == 2


@pytest.mark.anyio
async def test_503_persistente_vira_upstream_depois_das_tentativas(tools_falso):
    c = cliente(erro_503(), erro_503(), erro_503())
    with pytest.raises(ChatbotUpstreamError):
        await chatbot_sem_espera(tools_falso, c).ask("oi", [])
    assert len(c.aio.models.chamadas) == 3


@pytest.mark.anyio
async def test_429_e_500_nao_tentam_de_novo(tools_falso):
    erro = errors.APIError(500, {"error": {"code": 500, "message": "interno", "status": "INTERNAL"}})
    c = cliente(erro, texto("nunca chega"))
    with pytest.raises(ChatbotUpstreamError):
        await chatbot_sem_espera(tools_falso, c).ask("oi", [])
    assert len(c.aio.models.chamadas) == 1


@pytest.mark.anyio
async def test_sem_internet_vira_upstream(tools_falso):
    with pytest.raises(ChatbotUpstreamError) as exc:
        await chatbot(tools_falso, cliente(ConnectionError("rede caiu"))).ask("oi", [])
    assert "chave-de-teste" not in exc.value.message
