# Task 7A — Chatbot Gemini multi-vinheria: plano de implementação

> **Para executores (Sonnet):** use `superpowers:executing-plans` ou `superpowers:subagent-driven-development`. Os passos usam checkbox (`- [ ]`). Siga a [`spec.md`](spec.md) desta pasta. Em caso de divergência, **a spec manda**: pare e devolva para planejamento em Opus. Uma subtarefa por vez. Ao fim de cada uma, informe o que mudou e o resultado da verificação, e espere a revisão do usuário (`CLAUDE.md` §2 e §4).

**Objetivo:** `POST /api/chat` responde em português, com dados reais do FIWARE, a perguntas sobre uma vinheria, várias ou a frota. O painel conversa por `/chat` e por um botão flutuante, e as ações pedidas pelo usuário viram cartões que só executam depois do Confirmar.

**Arquitetura:**
- **Backend.** `ChatTools` expõe as tools sobre os services que já existem (`DeviceRegistry`, `ReadingsService`, `FleetState`, `AlertLog`, `LimitsStore`). `chat_declarations.py` descreve essas tools ao Gemini. `Chatbot` roda o loop manual de function calling (no máximo 5 chamadas ao modelo) via `google-genai` async. A rota só chama `Chatbot.ask`.
- **Front.** `ChatContext` guarda a conversa acima das rotas. `ChatBox` é usado pela página `/chat` e pelo `ChatFlutuante`. O `CartaoAcao` executa a ação pelas rotas que já existem.

**Stack:**
- Python 3.11+ (a máquina roda 3.14), FastAPI, `google-genai` (versão fixada na subtarefa 7A.1), pytest.
- React 19 em `.jsx`, Tailwind v4 com os tokens da 5B, `lucide-react`, Vitest.

**Spec:** [`docs/specs/task-7a-chatbot/spec.md`](spec.md)

## Global Constraints

- Comentários em português em todo módulo e em toda função não óbvia; código no estilo dos arquivos vizinhos.
- Rota não chama SDK nem `httpx`. Só `services/chatbot.py` importa `google.genai`; `services/chat_declarations.py` importa apenas `google.genai.types`.
- A chave do Gemini só no `backend/.env`. Nunca em arquivo versionado, log ou resposta HTTP.
- `GEMINI_MODEL` default `gemini-3.5-flash-lite`.
- Nenhum arquivo novo passa de ~250 linhas.
- Testes sem rede e sem chave real (Gemini falso).
- Front: só o kit `components/ui/` e os tokens existentes. Sem hex, sem `style=` e sem `fetch` fora do `src/api/client.js`.
- Nomes canônicos de atributos (`temperature`, `humidity`, `luminosity`) e comandos (`blink_temp`, `blink_hum`, `blink_lux`, `alert_off`).
- Commit a cada subtarefa verificada, mensagem em português no imperativo, **sem** linha de co-autor.
- O PowerShell 5.1 não aceita `&&`. Rode cada comando dentro da pasta indicada (`backend/` ou `frontend/`).

## Review Focus

Condições que a spec implica mas nenhum requisito testa diretamente. Cada uma ganhou um teste na subtarefa dona:

1. **O Gemini manda `horas` como texto ou fora da faixa** (`"2"`, `0`, `100`): a tool deve converter e recortar para 0,25–24, sem quebrar. Teste em 7A.5.
2. **O Gemini pede duas tools na mesma resposta** (chamadas paralelas): as duas devem ser executadas e as duas respostas voltam juntas. Teste em 7A.8.
3. **Sem internet no notebook da demo** (erro de rede que não é `APIError`): deve dar 502 com mensagem clara, não 500. Teste em 7A.8.
4. **Nenhuma vinheria cadastrada**: o resumo da frota diz "nenhuma vinheria cadastrada", e as tools não quebram com lista vazia. Teste em 7A.7.
5. **Clique duplo no Confirmar**: a ação em `executando` não pode ser disparada de novo. Teste em 7A.16 (`podeDecidir`).

---

## Mapa de arquivos

**Backend — criar:**
| Arquivo | Responsabilidade |
|---|---|
| `backend/app/models/schemas_chat.py` | `ChatTurn`, `ChatRequest`, `ChatAction`, `ChatReply` |
| `backend/app/services/chat_errors.py` | `ChatbotError` e subclasses |
| `backend/app/services/chat_stats.py` | funções puras: janela, estatística, tendência, hora local, nomes e unidades |
| `backend/app/services/chat_tools.py` | `ChatTools`: 6 tools de leitura + `executar` + `registrar` |
| `backend/app/services/chat_acoes.py` | `ChatAcoes`: `propor_comando`, `propor_faixa` (bloco B) |
| `backend/app/services/chat_declarations.py` | `FunctionDeclaration` de cada tool |
| `backend/app/services/chatbot.py` | `resumo_frota`, `Chatbot.ask` (loop) |
| `backend/app/api/routes_chat.py` | `POST /api/chat` |
| `backend/tests/test_chat_stats.py`, `test_chat_tools.py`, `test_chat_acoes.py`, `test_chat_declarations.py`, `test_chatbot.py`, `test_routes_chat.py` | testes |

**Backend — modificar:** `app/core/config.py`, `app/api/errors.py`, `app/api/deps.py`, `app/main.py`, `requirements.txt`, `.env.example`, `tests/test_config.py`

**Front — criar:** `src/lib/chat.js`, `src/lib/chat.test.js`, `src/context/ChatContext.jsx`, `src/components/ChatMensagem.jsx`, `src/components/ChatBox.jsx`, `src/components/ChatFlutuante.jsx`, `src/components/CartaoAcao.jsx`, `src/pages/Chat.jsx`

**Front — modificar:** `src/api/client.js`, `src/components/ui/formulario.jsx` (novo `AreaTexto`), `src/App.jsx`

---

# Bloco A — núcleo

## Subtarefa 7A.1 — Sonda do SDK, dependência e configuração (R1, R10)

**Files:**
- Create (descartável, **não commitar**): `<scratchpad>/sonda_genai.py`
- Modify: `backend/requirements.txt`, `backend/.env.example`, `backend/app/core/config.py`, `backend/tests/test_config.py`

**Interfaces:**
- Produces: `Settings.gemini_api_key: str = ""`, `Settings.gemini_model: str = "gemini-3.5-flash-lite"`, ambos preenchidos por `load_settings`.

- [ ] **Passo 1: instalar o SDK.** Em `backend/`:

```
pip install google-genai==2.32.0
pip show google-genai
```
Esperado: `Version: 2.32.0`.

- [ ] **Passo 2: [VOCÊ] colocar a chave.** O usuário abre `backend/.env` (o mesmo onde está o `FIWARE_HOST`) e acrescenta uma linha:

```
GEMINI_API_KEY=cole-a-chave-aqui
```
O executor **não lê nem imprime** o valor. Confirme apenas que a linha existe, com `Select-String -Path backend/.env -Pattern "^GEMINI_API_KEY=." -Quiet`, que deve devolver `True`.

- [ ] **Passo 3: escrever a sonda** em `<scratchpad>/sonda_genai.py` (fora do repositório):

```python
"""Sonda descartável da Task 7A: confirma a API do google-genai. Não commitar."""
import asyncio
import importlib.metadata
import inspect
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv(sys.argv[1])  # caminho do backend/.env
print("versão:", importlib.metadata.version("google-genai"))
cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

declaracao = types.FunctionDeclaration(
    name="estado_atual",
    description="Estado atual de uma vinheria",
    parameters=types.Schema(type="OBJECT",
                            properties={"vinheria": types.Schema(type="STRING")},
                            required=["vinheria"]),
)
config = types.GenerateContentConfig(
    system_instruction="Responda em português usando a ferramenta.",
    tools=[types.Tool(function_declarations=[declaracao])],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)


async def main():
    contents = [types.Content(role="user",
                              parts=[types.Part.from_text(text="Como está a vinheria de São Paulo?")])]
    r1 = await cliente.aio.models.generate_content(model="gemini-3.5-flash-lite",
                                                    contents=contents, config=config)
    print("(b) function_calls:", r1.function_calls)
    chamada = r1.function_calls[0]
    print("    nome/args:", chamada.name, dict(chamada.args))
    contents.append(r1.candidates[0].content)
    contents.append(types.Content(role="user", parts=[types.Part.from_function_response(
        name=chamada.name, response={"temperatura": 14.2, "unidade": "°C"})]))
    r2 = await cliente.aio.models.generate_content(model="gemini-3.5-flash-lite",
                                                    contents=contents, config=config)
    print("(c) texto final:", r2.text)
    try:
        await cliente.aio.models.generate_content(model="modelo-que-nao-existe", contents="oi")
    except errors.APIError as exc:
        print("(d) erro:", [c.__name__ for c in type(exc).__mro__][:3],
              "code =", exc.code, "message =", getattr(exc, "message", None))
    print("(d) assinatura APIError:", inspect.signature(errors.APIError.__init__))


asyncio.run(main())
```

- [ ] **Passo 4: rodar a sonda.** Na raiz do repositório: `python <scratchpad>/sonda_genai.py backend/.env`

Esperado, nesta ordem:
- (a) `versão: 2.32.0`;
- (b) uma lista com um `FunctionCall` de `name='estado_atual'` e args contendo `vinheria`;
- (c) um texto em português citando 14,2 °C;
- (d) `APIError` (ou subclasse `ClientError`) com `code = 404`, e a assinatura com `code` e `response_json`.

**Se qualquer item divergir** (nome de atributo, forma de devolver a resposta da tool, classe do erro), **pare** e reporte a saída exata. As subtarefas 7A.6 e 7A.8 dependem disso. Não apague a sonda até o fim da task.

- [ ] **Passo 5: teste falhando de configuração.** Em `backend/tests/test_config.py`:
  - acrescente `"GEMINI_API_KEY", "GEMINI_MODEL"` à tupla `VARIAVEIS`;
  - no fim de `test_load_settings_usa_defaults`, acrescente:
```python
    assert s.gemini_api_key == ""
    assert s.gemini_model == "gemini-3.5-flash-lite"
```
  - acrescente o teste:
```python
def test_load_settings_le_gemini(ambiente_limpo):
    ambiente_limpo.setenv("GEMINI_API_KEY", "chave-de-teste")
    ambiente_limpo.setenv("GEMINI_MODEL", "gemini-outro")
    s = load_settings(env_file=None)
    assert s.gemini_api_key == "chave-de-teste"
    assert s.gemini_model == "gemini-outro"
```

- [ ] **Passo 6: rodar.** Em `backend/`: `pytest tests/test_config.py -v`. Esperado: FAIL com `AttributeError: 'Settings' object has no attribute 'gemini_api_key'`.

- [ ] **Passo 7: implementar.** Em `backend/app/core/config.py`:
  - na dataclass `Settings`, logo antes do comentário `# Poller e backup em fundo`, acrescente:
```python
    # Chatbot (Task 7A): chave só no .env; vazia deixa o chat indisponível (503)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
```
  - em `load_settings`, antes de `run_background=True,`, acrescente:
```python
        gemini_api_key=_env("GEMINI_API_KEY", p.gemini_api_key),
        gemini_model=_env("GEMINI_MODEL", p.gemini_model),
```

- [ ] **Passo 8: rodar.** `pytest tests/test_config.py -v`. Esperado: PASS.

- [ ] **Passo 9: dependência e exemplo de ambiente.**
  - em `backend/requirements.txt`, acrescente depois de `python-dotenv`: `google-genai==2.32.0` (ou a versão que a sonda mostrou);
  - no fim de `backend/.env.example`, acrescente:
```
# Chatbot Gemini (Task 7A). A chave real fica só no .env, nunca no Git.
# Sem chave, o painel funciona e o chat responde "não configurado".
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
```

- [ ] **Passo 10: suíte inteira.** `pytest tests -q`. Esperado: tudo verde (285 + 1 testes).

- [ ] **Passo 11: commit.**
```
git add backend/requirements.txt backend/.env.example backend/app/core/config.py backend/tests/test_config.py
git commit -m "chore: adiciona o google-genai e a configuracao do gemini"
```
Antes do commit, confira com `git status` que `backend/.env` **não** aparece.

---

## Subtarefa 7A.2 — Contrato e erros do chatbot (R2, R6.5)

**Files:**
- Create: `backend/app/models/schemas_chat.py`, `backend/app/services/chat_errors.py`, `backend/tests/test_routes_chat.py` (só os testes de schema nesta subtarefa)

**Interfaces:**
- Produces:
  - `ChatTurn(role: Literal["user","model"], text: str)`, `ChatRequest(message: str, history: list[ChatTurn])`, `ChatAction(kind, device_id, name, summary, command=None, limits=None)`, `ChatReply(reply: str, actions: list[ChatAction])`, `MAX_HISTORICO = 20`;
  - `ChatbotError(message)` com `.message` e `service = "gemini"`; subclasses `ChatbotUnavailable`, `ChatbotRateLimited`, `ChatbotUpstreamError`.

- [ ] **Passo 1: teste falhando.** Crie `backend/tests/test_routes_chat.py`:

```python
"""Testes do contrato e da rota do chatbot (spec R2 e R7)."""
import pytest
from pydantic import ValidationError

from app.models.schemas_chat import ChatAction, ChatReply, ChatRequest, ChatTurn


def test_chat_request_aceita_mensagem_e_historico():
    pedido = ChatRequest(message="  Como está a 001?  ",
                         history=[{"role": "user", "text": "oi"}, {"role": "model", "text": "olá"}])
    assert pedido.message == "Como está a 001?"
    assert pedido.history[1] == ChatTurn(role="model", text="olá")


@pytest.mark.parametrize("dados", [
    {"message": ""},
    {"message": "   "},
    {"message": "x" * 1001},
    {"message": "oi", "history": [{"role": "user", "text": "a"}] * 21},
    {"message": "oi", "history": [{"role": "system", "text": "a"}]},
])
def test_chat_request_rejeita_entrada_invalida(dados):
    with pytest.raises(ValidationError):
        ChatRequest(**dados)


def test_chat_reply_comeca_sem_acoes():
    assert ChatReply(reply="ok").actions == []


def test_chat_action_de_comando():
    acao = ChatAction(kind="command", device_id="vinheria002", name="Vinheria Mineira",
                      summary="Piscar a luz", command="blink_lux")
    assert acao.limits is None
```

- [ ] **Passo 2: rodar.** Em `backend/`: `pytest tests/test_routes_chat.py -v`. Esperado: FAIL com `ModuleNotFoundError: No module named 'app.models.schemas_chat'`.

- [ ] **Passo 3: implementar** `backend/app/models/schemas_chat.py`:

```python
"""
Modelos do chatbot (Task 7A): pedido do painel, turno do histórico,
resposta do assistente e ação proposta.

O backend não guarda a conversa: o painel manda o histórico (só texto) a
cada pergunta. As ações propostas nunca são executadas aqui; o painel
executa pelas rotas de faixa e de comando depois do Confirmar.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import Limits
from app.models.schemas_fleet import ManualCommand

# Quantos turnos anteriores o painel pode mandar junto com a pergunta
MAX_HISTORICO = 20


class ChatTurn(BaseModel):
    """Um turno anterior da conversa: do usuário ou do modelo."""
    role: Literal["user", "model"]
    text: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """Pergunta do painel com o histórico da conversa."""
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORICO)


class ChatAction(BaseModel):
    """Ação proposta pelo assistente, aguardando o Confirmar do usuário.

    kind="command" traz `command`; kind="limits" traz a faixa completa
    (`limits`) já com a mudança, pronta para o PUT /triggers.
    """
    kind: Literal["command", "limits"]
    device_id: str
    name: str
    summary: str
    command: ManualCommand | None = None
    limits: Limits | None = None


class ChatReply(BaseModel):
    """Resposta do assistente e as ações que ele propôs nesta pergunta."""
    reply: str
    actions: list[ChatAction] = Field(default_factory=list)
```

- [ ] **Passo 4: implementar** `backend/app/services/chat_errors.py`:

```python
"""
Exceções do chatbot.

Como as do FIWARE e do cadastro, não dependem do FastAPI; a tradução para
resposta HTTP fica em app/api/errors.py (503, 429 e 502).
"""


class ChatbotError(Exception):
    """Falha ao responder pelo Gemini."""
    service = "gemini"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ChatbotUnavailable(ChatbotError):
    """Chatbot sem chave configurada no backend/.env."""


class ChatbotRateLimited(ChatbotError):
    """O Gemini recusou por limite de uso (HTTP 429)."""


class ChatbotUpstreamError(ChatbotError):
    """Outra falha do Gemini ou da rede até ele."""
```

- [ ] **Passo 5: rodar.** `pytest tests/test_routes_chat.py -v`. Esperado: PASS (8 testes).

- [ ] **Passo 6: commit.**
```
git add backend/app/models/schemas_chat.py backend/app/services/chat_errors.py backend/tests/test_routes_chat.py
git commit -m "feat: adiciona o contrato e os erros do chatbot"
```

---

## Subtarefa 7A.3 — Estatísticas puras (R3)

**Files:**
- Create: `backend/app/services/chat_stats.py`, `backend/tests/test_chat_stats.py`

**Interfaces:**
- Consumes: `HistoryPoint(ts: str, value: float)` de `app.models.schemas`.
- Produces:
  - `NOME_ATRIBUTO: dict[str, str]`, `UNIDADE: dict[str, str]`, `LIMIAR_ESTAVEL: dict[str, float]`, `COBERTURA_MINIMA = 0.9`;
  - `para_datetime(ts: str) -> datetime`, `hora_local(ts: str, fuso: tzinfo | None = None) -> str`;
  - `filtrar_janela(pontos, horas: float, agora: datetime) -> list[HistoryPoint]`;
  - `tendencia(pontos, atributo) -> str`;
  - `estatisticas(pontos, atributo, horas_pedidas, fuso=None) -> dict`.

- [ ] **Passo 1: teste falhando.** Crie `backend/tests/test_chat_stats.py`:

```python
"""Testes das estatísticas do chatbot (spec R3)."""
from datetime import datetime, timedelta, timezone

from app.models.schemas import HistoryPoint
from app.services.chat_stats import estatisticas, filtrar_janela, tendencia

AGORA = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


def pontos(valores, passo_min=1.0, fim=AGORA, formato_z=True):
    """Série do mais velho ao mais novo, o último em `fim`."""
    n = len(valores)
    serie = []
    for i, valor in enumerate(valores):
        instante = fim - timedelta(minutes=passo_min * (n - 1 - i))
        ts = instante.isoformat()
        serie.append(HistoryPoint(ts=ts.replace("+00:00", "Z") if formato_z else ts, value=valor))
    return serie


def test_estatisticas_basicas():
    r = estatisticas(pontos([14, 15, 16]), "temperature", 1, fuso=timezone.utc)
    assert (r["n"], r["media"], r["minimo"], r["maximo"], r["desvio"]) == (3, 15.0, 14, 16, 1.0)
    assert r["unidade"] == "°C"
    assert (r["inicio"], r["fim"]) == ("08/10 11:58", "08/10 12:00")
    assert r["tendencia"] == "subindo"


def test_estatisticas_sem_pontos():
    assert estatisticas([], "humidity", 1) == {"n": 0}


def test_estatisticas_um_ponto():
    r = estatisticas(pontos([60]), "humidity", 1)
    assert r["desvio"] is None
    assert r["tendencia"] == "estável"
    assert r["unidade"] == "%"


def test_estatisticas_ordenam_pontos_fora_de_ordem():
    serie = pontos([20, 18, 16])
    assert estatisticas(list(reversed(serie)), "temperature", 1)["tendencia"] == "caindo"


def test_janela_completa_e_incompleta():
    cheia = pontos([14] * 61, passo_min=1)        # 60 min cobertos
    curta = pontos([14] * 51, passo_min=1)        # 50 min cobertos (< 90 % de 1 h)
    assert estatisticas(cheia, "temperature", 1)["janela_completa"] is True
    assert estatisticas(curta, "temperature", 1)["janela_completa"] is False
    assert estatisticas(curta, "temperature", 1)["periodo_coberto_horas"] == 0.8


def test_tendencia_estavel_abaixo_do_limiar():
    assert tendencia(pontos([14, 14.5, 14.9]), "temperature") == "estável"
    assert tendencia(pontos([50, 52]), "humidity") == "estável"
    assert tendencia(pontos([10, 14]), "luminosity") == "estável"


def test_tendencia_acima_do_limiar():
    assert tendencia(pontos([50, 54]), "humidity") == "subindo"
    assert tendencia(pontos([30, 20]), "luminosity") == "caindo"


def test_filtrar_janela_aceita_z_e_offset():
    velhos = pontos([1], fim=AGORA - timedelta(minutes=90))
    novos_z = pontos([2], fim=AGORA - timedelta(minutes=30))
    novos_offset = pontos([3], fim=AGORA, formato_z=False)
    filtrados = filtrar_janela(velhos + novos_z + novos_offset, 1, AGORA)
    assert [p.value for p in filtrados] == [2, 3]
```

- [ ] **Passo 2: rodar.** `pytest tests/test_chat_stats.py -v`. Esperado: FAIL com `ModuleNotFoundError: No module named 'app.services.chat_stats'`.

- [ ] **Passo 3: implementar** `backend/app/services/chat_stats.py`:

```python
"""
Estatísticas das séries do STH-Comet para o chatbot (funções puras).

Calcula média, mínimo, máximo, desvio e tendência de uma lista de pontos
[{ts, value}], e diz quanto da janela pedida os pontos de fato cobrem: a
consulta pega no máximo os 500 pontos mais novos, que podem não chegar ao
começo da janela.
"""
import statistics
from datetime import datetime, timedelta, timezone, tzinfo

from app.models.schemas import HistoryPoint

# Nome em português e unidade de cada atributo, como o bot deve falar
NOME_ATRIBUTO = {"temperature": "temperatura", "humidity": "umidade",
                 "luminosity": "luminosidade"}
UNIDADE = {"temperature": "°C", "humidity": "%", "luminosity": "%"}
# Amplitude (máx − mín) abaixo da qual a série é considerada estável
LIMIAR_ESTAVEL = {"temperature": 1.0, "humidity": 3.0, "luminosity": 5.0}
# Fração mínima da janela pedida que os pontos precisam cobrir
COBERTURA_MINIMA = 0.9


def para_datetime(ts: str) -> datetime:
    """ISO do STH ("...Z") ou do SQLite ("+00:00") para datetime com fuso (UTC se faltar)."""
    instante = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return instante if instante.tzinfo else instante.replace(tzinfo=timezone.utc)


def hora_local(ts: str, fuso: tzinfo | None = None) -> str:
    """Instante no formato DD/MM HH:MM; sem `fuso`, usa o fuso da máquina."""
    return para_datetime(ts).astimezone(fuso).strftime("%d/%m %H:%M")


def filtrar_janela(pontos: list[HistoryPoint], horas: float, agora: datetime) -> list[HistoryPoint]:
    """Só os pontos das últimas `horas` antes de `agora`."""
    inicio = agora - timedelta(hours=horas)
    return [ponto for ponto in pontos if para_datetime(ponto.ts) >= inicio]


def tendencia(pontos: list[HistoryPoint], atributo: str) -> str:
    """"estável", "subindo" ou "caindo".

    Estável quando a amplitude fica abaixo do limiar do atributo; senão, o
    sinal da inclinação da reta de mínimos quadrados (valor × tempo) decide.
    """
    if len(pontos) < 2:
        return "estável"
    valores = [ponto.value for ponto in pontos]
    if max(valores) - min(valores) < LIMIAR_ESTAVEL[atributo]:
        return "estável"
    inicio = para_datetime(pontos[0].ts)
    segundos = [(para_datetime(ponto.ts) - inicio).total_seconds() for ponto in pontos]
    if len(set(segundos)) < 2:
        return "estável"
    inclinacao = statistics.linear_regression(segundos, valores).slope
    return "subindo" if inclinacao > 0 else "caindo"


def estatisticas(pontos: list[HistoryPoint], atributo: str, horas_pedidas: float,
                 fuso: tzinfo | None = None) -> dict:
    """Resumo numérico da série, pronto para o Gemini citar; {"n": 0} sem pontos."""
    if not pontos:
        return {"n": 0}
    ordenados = sorted(pontos, key=lambda ponto: para_datetime(ponto.ts))
    valores = [ponto.value for ponto in ordenados]
    coberto = (para_datetime(ordenados[-1].ts) - para_datetime(ordenados[0].ts)).total_seconds() / 3600
    return {
        "n": len(valores),
        "media": round(statistics.fmean(valores), 1),
        "minimo": round(min(valores), 1),
        "maximo": round(max(valores), 1),
        "desvio": round(statistics.stdev(valores), 1) if len(valores) >= 2 else None,
        "inicio": hora_local(ordenados[0].ts, fuso),
        "fim": hora_local(ordenados[-1].ts, fuso),
        "periodo_coberto_horas": round(coberto, 1),
        "janela_completa": coberto >= COBERTURA_MINIMA * horas_pedidas,
        "tendencia": tendencia(ordenados, atributo),
        "unidade": UNIDADE[atributo],
    }
```

- [ ] **Passo 4: rodar.** `pytest tests/test_chat_stats.py -v`. Esperado: PASS (8 testes).

- [ ] **Passo 5: commit.**
```
git add backend/app/services/chat_stats.py backend/tests/test_chat_stats.py
git commit -m "feat: adiciona as estatisticas das series para o chatbot"
```

---

## Subtarefa 7A.4 — Tools de leitura, parte 1: resolução, lista, estado e faixa (R4.1–R4.4, R4.8, R4.9)

**Files:**
- Create: `backend/app/services/chat_tools.py`, `backend/tests/test_chat_tools.py`

**Interfaces:**
- Consumes:
  - `resolve_vinheria(texto, devices)`, `AmbiguousVinheria.options`, `VinheriaNotFound`;
  - `DeviceRegistry.list()`, `FleetState.get(id)`, `FleetState.status_of(id)`, `LimitsStore.get(id)`;
  - `NOME_ATRIBUTO`, `UNIDADE`, `hora_local` (7A.3).
- Produces:
  - `ChatTools(registry, readings, fleet, alerts, limits, agora=agora_utc, fuso=None)`;
  - `async executar(nome: str, args: dict, propostas: list) -> dict`;
  - `registrar(nome: str, funcao, recebe_propostas: bool = False)`;
  - `nomes() -> set[str]`;
  - funções de módulo `resolver(registry, texto) -> tuple[Device | None, dict | None]`, `checar_atributo(atributo) -> dict | None` e `ATRIBUTOS`.

- [ ] **Passo 1: teste falhando.** Crie `backend/tests/test_chat_tools.py`:

```python
"""Testes das tools de leitura do chatbot (spec R4)."""
from datetime import timedelta, timezone

import pytest

from app.models.schemas import HistoryPoint
from app.models.schemas_fleet import ActiveAlert, SensorValues
from app.services.chat_tools import ChatTools
from app.services.fiware_errors import FiwareUnavailable
from tests.fakes import status_vinheria

pytestmark = pytest.mark.anyio


class ReadingsFalso:
    """Substitui o ReadingsService: devolve séries por (device_id, atributo)."""

    def __init__(self):
        self.series = {}
        self.erro = None
        self.pedidos = []

    async def history(self, device_id, query):
        self.pedidos.append((device_id, query))
        if self.erro:
            raise self.erro
        return list(self.series.get((device_id, query.attr), []))


def serie(relogio, valores, passo_min=1.0):
    """Pontos do mais velho ao mais novo, o último no instante do relógio."""
    n = len(valores)
    return [HistoryPoint(ts=(relogio.agora - timedelta(minutes=passo_min * (n - 1 - i)))
                         .strftime("%Y-%m-%dT%H:%M:%S.000Z"), value=v)
            for i, v in enumerate(valores)]


@pytest.fixture
def readings_falso():
    return ReadingsFalso()


@pytest.fixture
def tools(registry, readings_falso, fleet, alert_log, limits, relogio):
    return ChatTools(registry, readings_falso, fleet, alert_log, limits,
                     agora=relogio, fuso=timezone.utc)


@pytest.fixture
def duas(cadastrar):
    """vinheria001 em São Paulo e vinheria002 em Belo Horizonte."""
    cadastrar("001", "Vinheria Paulista", "São Paulo")
    cadastrar("002", "Vinheria Mineira", "Belo Horizonte")


def retrato(fleet, relogio, *statuses):
    fleet.replace(list(statuses), at=relogio.iso())


async def test_vinheria_ambigua_devolve_opcoes(tools, duas):
    r = await tools.executar("estado_atual", {"vinheria": "vinheria"}, [])
    assert "erro" in r
    assert [o["device_id"] for o in r["opcoes"]] == ["vinheria001", "vinheria002"]


async def test_vinheria_nao_encontrada(tools, duas):
    r = await tools.executar("estado_atual", {"vinheria": "Recife"}, [])
    assert "erro" in r and "opcoes" not in r


async def test_listar_vinherias_com_status(tools, duas, fleet, relogio):
    retrato(fleet, relogio, status_vinheria("vinheria001", "alerta"))
    r = await tools.executar("listar_vinherias", {}, [])
    assert r["fiware_online"] is True
    assert [(v["device_id"], v["status"]) for v in r["vinherias"]] == [
        ("vinheria001", "alerta"), ("vinheria002", "aguardando")]
    assert r["vinherias"][0]["name"] == "Vinheria Paulista"


async def test_listar_sem_vinherias(tools):
    assert (await tools.executar("listar_vinherias", {}, []))["vinherias"] == []


async def test_estado_atual_sem_retrato(tools, duas):
    r = await tools.executar("estado_atual", {"vinheria": "São Paulo"}, [])
    assert "poller" in r["erro"]


async def test_estado_atual_com_retrato(tools, duas, fleet, relogio):
    status = status_vinheria("vinheria001", "alerta").model_copy(update={
        "seconds_since": 4, "score": 72.5,
        "current": SensorValues(temperature=21.3, humidity=60, luminosity=10),
        "active_alerts": [ActiveAlert(attr="temperature", value=21.3,
                                      since="2026-10-08T11:50:00+00:00")]})
    retrato(fleet, relogio, status)
    r = await tools.executar("estado_atual", {"vinheria": "sao paulo"}, [])
    assert (r["device_id"], r["status"], r["temperatura"], r["score"]) == (
        "vinheria001", "alerta", 21.3, 72.5)
    assert r["visto_ha_segundos"] == 4
    assert r["alertas_ativos"] == [{"atributo": "temperatura", "valor": 21.3, "desde": "08/10 11:50"}]


async def test_limites_padrao(tools, duas):
    r = await tools.executar("limites", {"vinheria": "vinheria002"}, [])
    assert r["temperatura"] == {"min": 12, "max": 18, "unidade": "°C"}
    assert r["luminosidade"]["max"] == 30


async def test_tool_desconhecida(tools):
    assert "erro" in await tools.executar("apagar_tudo", {}, [])


async def test_argumentos_invalidos(tools, duas):
    r = await tools.executar("estado_atual", {"cidade": "SP"}, [])
    assert "argumentos inválidos" in r["erro"]


async def test_fiware_fora_vira_erro(tools, duas, readings_falso):
    readings_falso.erro = FiwareUnavailable("sth", "sem resposta")
    r = await tools.executar("estatisticas", {"vinheria": "001", "atributo": "temperature"}, [])
    assert r == {"erro": "FIWARE indisponível: sem resposta"}
```
O último teste já usa `estatisticas`, que só nasce na 7A.5. Ele fica vermelho até lá; isso é esperado e está anotado no Passo 4.

- [ ] **Passo 2: rodar.** `pytest tests/test_chat_tools.py -v`. Esperado: FAIL com `ModuleNotFoundError: No module named 'app.services.chat_tools'`.

- [ ] **Passo 3: implementar** `backend/app/services/chat_tools.py` (parte 1; `estatisticas`, `comparar` e `alertas` entram na 7A.5):

```python
"""
Ferramentas (tools) que o Gemini chama para responder sobre as vinherias.

Cada tool lê os services que já existem (cadastro, frota, histórico,
alertas e faixa) e devolve um dict simples, pronto para virar JSON. Falhas
esperadas (vinheria ambígua ou não encontrada, FIWARE fora, argumento
errado) voltam como {"erro": ...} para o próprio Gemini, que então pergunta
ou explica ao usuário em vez de a requisição falhar.
"""
import inspect
from datetime import datetime, timezone, tzinfo

from app.models.schemas import Device
from app.services.chat_stats import NOME_ATRIBUTO, UNIDADE, hora_local
from app.services.fiware_errors import FiwareError
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound
from app.services.vinheria_resolver import resolve_vinheria

# Atributos aceitos pelas tools (nomes longos do Orion/STH)
ATRIBUTOS = tuple(NOME_ATRIBUTO)


def agora_utc() -> datetime:
    """Relógio padrão das tools (os testes injetam um relógio parado)."""
    return datetime.now(timezone.utc)


def resolver(registry, texto) -> tuple[Device | None, dict | None]:
    """Resolve o texto livre em vinheria; em falha, devolve o erro pronto para o Gemini."""
    try:
        return resolve_vinheria(str(texto or ""), registry.list()), None
    except AmbiguousVinheria as exc:
        opcoes = [{"device_id": d.device_id, "name": d.name, "city": d.city} for d in exc.options]
        return None, {"erro": exc.message, "opcoes": opcoes}
    except VinheriaNotFound as exc:
        return None, {"erro": exc.message}


def checar_atributo(atributo) -> dict | None:
    """Erro para o Gemini quando o atributo não é um dos três sensores."""
    if atributo in ATRIBUTOS:
        return None
    return {"erro": f"atributo inválido: {atributo}; use temperature, humidity ou luminosity"}


def _faixa(limites, atributo: str) -> dict:
    """Faixa de um atributo com a unidade, no formato que o bot cita."""
    faixa = getattr(limites, atributo)
    return {"min": faixa.min, "max": faixa.max, "unidade": UNIDADE[atributo]}


class ChatTools:
    """Tools de leitura do chatbot e o despacho por nome."""

    def __init__(self, registry, readings, fleet, alerts, limits,
                 agora=agora_utc, fuso: tzinfo | None = None):
        self._registry = registry
        self._readings = readings
        self._fleet = fleet
        self._alerts = alerts
        self._limits = limits
        self._agora = agora
        self._fuso = fuso
        # nome da tool -> (função, se recebe a lista de propostas da pergunta)
        self._tabela = {
            "listar_vinherias": (self.listar_vinherias, False),
            "estado_atual": (self.estado_atual, False),
            "limites": (self.limites, False),
        }

    def registrar(self, nome: str, funcao, recebe_propostas: bool = False) -> None:
        """Acrescenta uma tool (as de ação, do bloco B, chegam por aqui)."""
        self._tabela[nome] = (funcao, recebe_propostas)

    def nomes(self) -> set[str]:
        """Nomes das tools disponíveis (conferidos contra as declarações)."""
        return set(self._tabela)

    async def executar(self, nome: str, args: dict, propostas: list) -> dict:
        """Executa a tool pedida pelo Gemini; qualquer falha esperada vira {"erro"}."""
        if nome not in self._tabela:
            return {"erro": f"ferramenta desconhecida: {nome}"}
        funcao, recebe_propostas = self._tabela[nome]
        argumentos = dict(args or {})
        if recebe_propostas:
            argumentos["propostas"] = propostas
        try:
            inspect.signature(funcao).bind(**argumentos)
        except TypeError as exc:
            return {"erro": f"argumentos inválidos para {nome}: {exc}"}
        try:
            return await funcao(**argumentos)
        except FiwareError as exc:
            return {"erro": f"FIWARE indisponível: {exc.message}"}

    async def listar_vinherias(self) -> dict:
        """Todas as cadastradas, com o status do último ciclo do poller."""
        vinherias = []
        for device in self._registry.list():
            status = self._fleet.get(device.device_id)
            vinherias.append({
                "device_id": device.device_id, "name": device.name, "city": device.city,
                "status": status.status if status else "aguardando",
                "offline_reason": status.offline_reason if status else None,
            })
        return {"fiware_online": self._fleet.fiware_online, "vinherias": vinherias}

    async def estado_atual(self, vinheria: str) -> dict:
        """Valores atuais, score, "visto há" e alertas ativos de uma vinheria."""
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        status = self._fleet.get(device.device_id)
        if status is None:
            return {"erro": "ainda sem leitura do poller, tente em alguns segundos"}
        atual = status.current
        return {
            "device_id": device.device_id, "name": device.name, "city": device.city,
            "status": status.status, "offline_reason": status.offline_reason,
            "visto_ha_segundos": status.seconds_since,
            "temperatura": atual.temperature, "umidade": atual.humidity,
            "luminosidade": atual.luminosity,
            "unidades": {"temperatura": "°C", "umidade": "%", "luminosidade": "%"},
            "score": status.score,
            "alertas_ativos": [
                {"atributo": NOME_ATRIBUTO.get(a.attr, a.attr), "valor": a.value,
                 "desde": hora_local(a.since, self._fuso)}
                for a in status.active_alerts],
        }

    async def limites(self, vinheria: str) -> dict:
        """Faixa ideal da vinheria (a mesma que dispara os alertas)."""
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        limites = self._limits.get(device.device_id)
        return {"device_id": device.device_id, "name": device.name,
                **{NOME_ATRIBUTO[a]: _faixa(limites, a) for a in ATRIBUTOS}}
```

- [ ] **Passo 4: rodar.** `pytest tests/test_chat_tools.py -v`. Esperado: 9 PASS e 1 FAIL (`test_fiware_fora_vira_erro`, com `ferramenta desconhecida: estatisticas`). Nenhuma outra falha.

- [ ] **Passo 5: commit.**
```
git add backend/app/services/chat_tools.py backend/tests/test_chat_tools.py
git commit -m "feat: adiciona as tools de leitura de estado e faixa do chatbot"
```

---

## Subtarefa 7A.5 — Tools de leitura, parte 2: estatísticas, comparação e alertas (R4.5–R4.7)

**Files:**
- Modify: `backend/app/services/chat_tools.py`, `backend/tests/test_chat_tools.py`

**Interfaces:**
- Consumes:
  - `ReadingsService.history(device_id, HistoryQuery)`, que lança `FiwareNotFound` quando o STH não tem dados;
  - `AlertLog.list(device_id, limit)`;
  - `estatisticas`, `filtrar_janela` e `para_datetime` (7A.3).
- Produces: as tools `estatisticas(vinheria, atributo, horas=1)`, `comparar(atributo, horas=1)` e `alertas(vinheria=None, horas=24)`, registradas na tabela.

- [ ] **Passo 1: testes falhando.** Acrescente ao fim de `backend/tests/test_chat_tools.py`:

```python
from app.services.fiware_errors import FiwareNotFound  # noqa: E402


async def test_estatisticas_da_ultima_hora(tools, duas, readings_falso, relogio):
    # 90 pontos de 1 em 1 min: os 30 mais velhos ficam fora da janela de 1 h
    readings_falso.series[("vinheria001", "temperature")] = serie(relogio, [30] * 29 + [14, 15, 16] * 20 + [15])
    r = await tools.executar("estatisticas", {"vinheria": "São Paulo", "atributo": "temperature"}, [])
    assert (r["device_id"], r["atributo"], r["horas_pedidas"]) == ("vinheria001", "temperatura", 1.0)
    assert (r["n"], r["media"], r["minimo"], r["maximo"]) == (61, 15.0, 14, 16)
    assert readings_falso.pedidos[0][1].last_n == 500


async def test_estatisticas_sem_dados_no_sth(tools, duas, readings_falso):
    readings_falso.erro = FiwareNotFound("sth", "sem dados")
    r = await tools.executar("estatisticas", {"vinheria": "001", "atributo": "humidity"}, [])
    assert r["n"] == 0


@pytest.mark.parametrize("horas, esperado", [("2", 2.0), (0, 0.25), (100, 24.0), ("abc", 1.0)])
async def test_estatisticas_recortam_horas(tools, duas, horas, esperado):
    r = await tools.executar("estatisticas",
                             {"vinheria": "001", "atributo": "humidity", "horas": horas}, [])
    assert r["horas_pedidas"] == esperado


async def test_estatisticas_atributo_invalido(tools, duas):
    r = await tools.executar("estatisticas", {"vinheria": "001", "atributo": "pressao"}, [])
    assert "atributo inválido" in r["erro"]


async def test_comparar_ordena_pela_media(tools, duas, cadastrar, readings_falso, relogio):
    cadastrar("003", "Vinheria Sul", "Porto Alegre")
    readings_falso.series[("vinheria001", "humidity")] = serie(relogio, [55, 57])
    readings_falso.series[("vinheria002", "humidity")] = serie(relogio, [70, 72])
    r = await tools.executar("comparar", {"atributo": "humidity"}, [])
    assert r["unidade"] == "%"
    assert [(v["device_id"], v["media"]) for v in r["vinherias"]] == [
        ("vinheria002", 71.0), ("vinheria001", 56.0), ("vinheria003", None)]


async def test_comparar_isola_falha_de_uma_vinheria(tools, duas, readings_falso, relogio):
    original = readings_falso.history

    async def falha_na_002(device_id, query):
        if device_id == "vinheria002":
            raise FiwareUnavailable("sth", "timeout")
        return await original(device_id, query)

    readings_falso.history = falha_na_002
    readings_falso.series[("vinheria001", "temperature")] = serie(relogio, [14])
    r = await tools.executar("comparar", {"atributo": "temperature"}, [])
    assert r["vinherias"][0]["media"] == 14.0
    assert r["vinherias"][1]["erro"] == "FIWARE indisponível: timeout"


async def test_alertas_filtra_janela_e_vinheria(tools, duas, alert_log, relogio):
    alert_log.open("vinheria001", "temperature", 21.0, relogio.iso(segundos_atras=3600))
    antigo = alert_log.open("vinheria002", "humidity", 80.0, relogio.iso(segundos_atras=30 * 3600))
    alert_log.close(antigo.id, relogio.iso(segundos_atras=29 * 3600))
    alert_log.open("fiware", "offline", None, relogio.iso(segundos_atras=600))
    todos = await tools.executar("alertas", {}, [])
    assert [a["device_id"] for a in todos["alertas"]] == ["fiware", "vinheria001"]
    assert todos["alertas"][1]["aberto"] is True
    so_001 = await tools.executar("alertas", {"vinheria": "São Paulo"}, [])
    assert [a["device_id"] for a in so_001["alertas"]] == ["vinheria001"]
```

- [ ] **Passo 2: rodar.** `pytest tests/test_chat_tools.py -v`. Esperado: os testes novos e `test_fiware_fora_vira_erro` FALHAM com `ferramenta desconhecida`.

- [ ] **Passo 3: implementar.** Em `backend/app/services/chat_tools.py`:
  - troque os imports do topo por:
```python
import inspect
import statistics
from datetime import datetime, timedelta, timezone, tzinfo

from app.models.schemas import Device, HistoryPoint, HistoryQuery
from app.services.chat_stats import (
    NOME_ATRIBUTO,
    UNIDADE,
    estatisticas as calcular_estatisticas,
    filtrar_janela,
    hora_local,
    para_datetime,
)
from app.services.fiware_errors import FiwareError, FiwareNotFound
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound
from app.services.vinheria_resolver import resolve_vinheria
```
  - depois de `ATRIBUTOS`, acrescente:
```python
# Pontos pedidos ao STH: os mais novos (a consulta por datas devolveria os mais velhos)
PONTOS_HISTORICO = 500
# Janela aceita pelas tools, em horas
HORAS_MIN, HORAS_MAX = 0.25, 24.0
# Quantos alertas ler do SQLite antes de filtrar pela janela
LIMITE_ALERTAS = 200
```
  - depois de `checar_atributo`, acrescente:
```python
def horas_validas(valor, padrao: float = 1.0) -> float:
    """Converte a janela pedida pelo Gemini (número ou texto) e recorta em 0,25–24 h."""
    try:
        horas = float(valor)
    except (TypeError, ValueError):
        horas = padrao
    return min(max(horas, HORAS_MIN), HORAS_MAX)
```
  - na `_tabela` do `__init__`, acrescente as três entradas:
```python
            "estatisticas": (self.estatisticas, False),
            "comparar": (self.comparar, False),
            "alertas": (self.alertas, False),
```
  - no fim da classe, acrescente:
```python
    async def _pontos(self, device_id: str, atributo: str, horas: float) -> list[HistoryPoint]:
        """Os 500 pontos mais novos do STH, só os que caem na janela; [] sem dados."""
        consulta = HistoryQuery(attr=atributo, last_n=PONTOS_HISTORICO)
        try:
            pontos = await self._readings.history(device_id, consulta)
        except FiwareNotFound:
            return []
        return filtrar_janela(pontos, horas, self._agora())

    async def estatisticas(self, vinheria: str, atributo: str, horas=1) -> dict:
        """Média, mínimo, máximo, desvio e tendência de um atributo na janela."""
        erro = checar_atributo(atributo)
        if erro:
            return erro
        device, erro = resolver(self._registry, vinheria)
        if erro:
            return erro
        horas = horas_validas(horas)
        pontos = await self._pontos(device.device_id, atributo, horas)
        return {"device_id": device.device_id, "name": device.name,
                "atributo": NOME_ATRIBUTO[atributo], "horas_pedidas": horas,
                **calcular_estatisticas(pontos, atributo, horas, self._fuso)}

    async def comparar(self, atributo: str, horas=1) -> dict:
        """Média do atributo em cada vinheria, da maior para a menor (sem dados por último)."""
        erro = checar_atributo(atributo)
        if erro:
            return erro
        horas = horas_validas(horas)
        linhas = []
        for device in self._registry.list():
            linha = {"device_id": device.device_id, "name": device.name, "city": device.city}
            try:
                pontos = await self._pontos(device.device_id, atributo, horas)
            except FiwareError as exc:
                linhas.append({**linha, "media": None, "n": 0,
                               "erro": f"FIWARE indisponível: {exc.message}"})
                continue
            media = round(statistics.fmean(p.value for p in pontos), 1) if pontos else None
            linhas.append({**linha, "media": media, "n": len(pontos)})
        linhas.sort(key=lambda l: (l["media"] is None, -(l["media"] or 0)))
        return {"atributo": NOME_ATRIBUTO[atributo], "unidade": UNIDADE[atributo],
                "horas": horas, "vinherias": linhas}

    async def alertas(self, vinheria: str | None = None, horas=24) -> dict:
        """Alertas abertos nas últimas `horas`, de uma vinheria ou de todas (e da EC2)."""
        device_id = None
        if vinheria:
            device, erro = resolver(self._registry, vinheria)
            if erro:
                return erro
            device_id = device.device_id
        horas = horas_validas(horas, padrao=24.0)
        inicio = self._agora() - timedelta(hours=horas)
        lista = [a for a in self._alerts.list(device_id, limit=LIMITE_ALERTAS)
                 if para_datetime(a.opened_at) >= inicio]
        return {"horas": horas, "alertas": [
            {"device_id": a.device_id, "attr": a.attr, "value": a.value,
             "inicio": hora_local(a.opened_at, self._fuso),
             "fim": hora_local(a.closed_at, self._fuso) if a.closed_at else None,
             "duracao_segundos": a.duration_seconds, "aberto": a.closed_at is None}
            for a in lista]}
```

- [ ] **Passo 4: rodar.** `pytest tests/test_chat_tools.py -v`. Esperado: tudo PASS. Confira o tamanho com `(Get-Content backend/app/services/chat_tools.py | Measure-Object -Line).Lines`: deve ficar em até ~250 linhas.

- [ ] **Passo 5: commit.**
```
git add backend/app/services/chat_tools.py backend/tests/test_chat_tools.py
git commit -m "feat: adiciona estatisticas, comparacao e alertas as tools do chatbot"
```

---

## Subtarefa 7A.6 — Declarações das tools (R5)

**Files:**
- Create: `backend/app/services/chat_declarations.py`, `backend/tests/test_chat_declarations.py`

**Interfaces:**
- Consumes: `google.genai.types` (forma confirmada na sonda 7A.1), `ChatTools.nomes()`.
- Produces: `declaracoes(com_acoes: bool) -> list[types.FunctionDeclaration]`, `LEITURA`, `ACOES` (lista vazia no bloco A).

- [ ] **Passo 1: teste falhando.** Crie `backend/tests/test_chat_declarations.py`:

```python
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
```

- [ ] **Passo 2: rodar.** `pytest tests/test_chat_declarations.py -v`. Esperado: FAIL com `ModuleNotFoundError`.

- [ ] **Passo 3: implementar** `backend/app/services/chat_declarations.py`:

```python
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
ACOES: list[types.FunctionDeclaration] = []


def declaracoes(com_acoes: bool) -> list[types.FunctionDeclaration]:
    """Declarações enviadas ao Gemini; as de ação só com `com_acoes`."""
    return LEITURA + (ACOES if com_acoes else [])
```

- [ ] **Passo 4: rodar.** `pytest tests/test_chat_declarations.py -v`. Esperado: PASS (4 testes).

- [ ] **Passo 5: commit.**
```
git add backend/app/services/chat_declarations.py backend/tests/test_chat_declarations.py
git commit -m "feat: declara as tools do chatbot para o gemini"
```

---

## Subtarefa 7A.7 — Resumo da frota (R6.2)

**Files:**
- Create: `backend/app/services/chatbot.py` (só `resumo_frota` e as constantes de texto nesta subtarefa), `backend/tests/test_chatbot.py`

**Interfaces:**
- Consumes: `FleetReport`, `VinheriaStatus`, `ActiveAlert`; `NOME_ATRIBUTO`, `hora_local`.
- Produces: `resumo_frota(report: FleetReport, fuso=None) -> str`.

- [ ] **Passo 1: teste falhando.** Crie `backend/tests/test_chatbot.py`:

```python
"""Testes do chatbot: resumo da frota e loop de function calling (spec R6)."""
from datetime import timezone

from app.models.schemas_fleet import ActiveAlert, FleetReport
from app.services.chatbot import resumo_frota
from tests.fakes import status_vinheria


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
```

- [ ] **Passo 2: rodar.** `pytest tests/test_chatbot.py -v`. Esperado: FAIL com `ModuleNotFoundError: No module named 'app.services.chatbot'`.

- [ ] **Passo 3: implementar** `backend/app/services/chatbot.py` (parte 1):

```python
"""
Chatbot multi-vinheria (Task 7A) com Google Gemini e function calling.

A cada pergunta, o backend acrescenta uma linha com a situação da frota
(para o bot avisar sozinho de vinheria em alerta ou offline), manda ao
Gemini a conversa e as declarações das tools e executa as tools que ele
pedir, até a resposta final ou o limite de chamadas. Nada é executado no
FIWARE por aqui: as ações viram propostas que o painel confirma.
"""
from datetime import tzinfo

from app.models.schemas_fleet import FleetReport
from app.services.chat_stats import NOME_ATRIBUTO, hora_local


def resumo_frota(report: FleetReport, fuso: tzinfo | None = None) -> str:
    """Uma linha em português com a situação da EC2 e das vinherias com problema."""
    if not report.fiware_online:
        desde = (f" desde {hora_local(report.fiware_offline_since, fuso)}"
                 if report.fiware_offline_since else "")
        return (f"Situação agora: FIWARE fora do ar{desde}; "
                "os dados das vinherias podem estar desatualizados.")
    total = len(report.vinherias)
    if total == 0:
        return "Situação agora: FIWARE ok; nenhuma vinheria cadastrada."
    problemas = []
    for status in report.vinherias:
        rotulo = f"{status.device_id} ({status.name})"
        if status.status == "alerta":
            atributos = ", ".join(NOME_ATRIBUTO.get(a.attr, a.attr) for a in status.active_alerts)
            problemas.append(f"{rotulo} em alerta de {atributos or 'faixa'}")
        elif status.status == "offline":
            problemas.append(f"{rotulo} offline")
        elif status.status == "configurando":
            problemas.append(f"{rotulo} aguardando a faixa (configurando)")
    plural = "vinheria" if total == 1 else "vinherias"
    if not problemas:
        return f"Situação agora: FIWARE ok; {total} {plural}, todas normais."
    return f"Situação agora: FIWARE ok; {total} {plural}; " + "; ".join(problemas) + "."
```

- [ ] **Passo 4: rodar.** `pytest tests/test_chatbot.py -v`. Esperado: PASS (4 testes).

- [ ] **Passo 5: commit.**
```
git add backend/app/services/chatbot.py backend/tests/test_chatbot.py
git commit -m "feat: adiciona o resumo da frota para o chatbot"
```

---

## Subtarefa 7A.8 — Loop de function calling (R6.1, R6.3–R6.6)

**Files:**
- Modify: `backend/app/services/chatbot.py`, `backend/tests/test_chatbot.py`

**Interfaces:**
- Consumes:
  - `ChatTools.executar(nome, args, propostas)` e `declaracoes(com_acoes)`;
  - `ChatReply`, `ChatAction`, `ChatTurn`;
  - os erros de `chat_errors`;
  - `Settings.gemini_api_key`, `Settings.gemini_model`;
  - SDK: `client.aio.models.generate_content(model=, contents=, config=)`, `response.function_calls`, `response.candidates[0].content`, `response.text`, `types.Part.from_text`, `types.Part.from_function_response`, `errors.APIError.code` (confirmados na sonda).
- Produces: `Chatbot(tools, registry, fleet, settings, client=None, com_acoes=False, fuso=None)` e `async ask(message: str, history: list[ChatTurn]) -> ChatReply`; as constantes `MAX_CHAMADAS = 5`, `SEM_CONCLUSAO`, `SEM_RESPOSTA`, `INSTRUCAO_BASE`, `INSTRUCAO_ACOES`.

- [ ] **Passo 1: testes falhando.** Acrescente ao fim de `backend/tests/test_chatbot.py`:

```python
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402
from google.genai import errors, types  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.models.schemas import Device  # noqa: E402
from app.models.schemas_chat import ChatAction, ChatTurn  # noqa: E402
from app.services.chat_errors import (  # noqa: E402
    ChatbotRateLimited, ChatbotUnavailable, ChatbotUpstreamError)
from app.services.chatbot import MAX_CHAMADAS, SEM_CONCLUSAO, Chatbot  # noqa: E402
from app.services.fleet_state import FleetState  # noqa: E402

DEVICE = Device(device_id="vinheria001", entity_id="urn:ngsi-ld:Vinheria:001",
                name="Vinheria Paulista", city="São Paulo")


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
    assert chamada["model"] == "gemini-3.5-flash-lite"
    assert [x.role for x in chamada["contents"]] == ["user", "model", "user"]
    ultima = _textos(chamada["contents"][-1])[0]
    assert ultima.startswith("[Situação agora: FIWARE ok;")
    assert ultima.endswith("Como está a 001?")
    assert chamada["config"].system_instruction


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
```
Se a sonda mostrou outra assinatura para `errors.APIError`, ajuste só a construção do erro nos dois testes e anote o desvio.

- [ ] **Passo 2: rodar.** `pytest tests/test_chatbot.py -v`. Esperado: FAIL com `ImportError: cannot import name 'MAX_CHAMADAS'`.

- [ ] **Passo 3: implementar.** Em `backend/app/services/chatbot.py`:
  - troque os imports (logo abaixo do docstring) por:
```python
import logging
from datetime import tzinfo

from google import genai
from google.genai import errors, types

from app.models.schemas_chat import ChatAction, ChatReply, ChatTurn
from app.models.schemas_fleet import FleetReport
from app.services.chat_declarations import declaracoes
from app.services.chat_errors import ChatbotRateLimited, ChatbotUnavailable, ChatbotUpstreamError
from app.services.chat_stats import NOME_ATRIBUTO, hora_local

log = logging.getLogger(__name__)

# Chamadas ao modelo por pergunta (cada pedido de tool gasta uma)
MAX_CHAMADAS = 5
SEM_CONCLUSAO = "Não consegui concluir a consulta. Tente reformular a pergunta."
SEM_RESPOSTA = "Não encontrei uma resposta. Tente reformular a pergunta."

INSTRUCAO_BASE = """Você é o assistente da Smart Solutions, que monitora vinherias.
Regras:
- Responda sempre em português do Brasil, de forma curta e direta.
- Use só os dados devolvidos pelas ferramentas. Nunca invente número, vinheria ou horário.
- Cite números com unidade (°C para temperatura, % para umidade e luminosidade) e o período a que se referem.
- Se uma estatística vier com janela_completa falso, diga que os dados cobrem só o período_coberto_horas.
- Se uma ferramenta devolver "erro" com "opcoes", pergunte ao usuário qual das vinherias ele quis dizer.
- Quando houver temperatura, umidade ou luz fora da faixa, recomende uma ação prática de vinheria (ex.: ajustar a climatização, ligar o umidificador, apagar ou cobrir a iluminação).
- Cada mensagem do usuário começa com a situação da frota entre colchetes. Se ela citar vinheria em alerta ou offline, ou o FIWARE fora do ar, avise isso no início da resposta, mesmo que o usuário não tenha perguntado.
- Escreva em texto simples, sem markdown: nada de asteriscos, títulos ou tabelas; para listas, use linhas começando com hífen."""

# Regras extras do bloco B (ações com confirmação)
INSTRUCAO_ACOES = ""
```
  - mantenha `resumo_frota` como está;
  - acrescente no fim do arquivo:
```python
def _conteudo(role: str, texto: str) -> types.Content:
    """Um turno de texto no formato do SDK."""
    return types.Content(role=role, parts=[types.Part.from_text(text=texto)])


class Chatbot:
    """Responde perguntas sobre as vinherias usando o Gemini e as tools."""

    def __init__(self, tools, registry, fleet, settings, client=None,
                 com_acoes: bool = False, fuso: tzinfo | None = None):
        # client: genai.Client real (criado na primeira pergunta) ou falso nos testes
        self._tools = tools
        self._registry = registry
        self._fleet = fleet
        self._settings = settings
        self._client = client
        self._com_acoes = com_acoes
        self._fuso = fuso

    def _cliente(self):
        """Cliente do Gemini; sem chave no .env, o chat fica indisponível."""
        if not self._settings.gemini_api_key:
            raise ChatbotUnavailable(
                "chatbot não configurado: defina GEMINI_API_KEY no backend/.env")
        if self._client is None:
            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    def _config(self) -> types.GenerateContentConfig:
        """Instrução de sistema, tools declaradas e chamada automática desligada (o loop é nosso)."""
        return types.GenerateContentConfig(
            system_instruction=INSTRUCAO_BASE + (INSTRUCAO_ACOES if self._com_acoes else ""),
            tools=[types.Tool(function_declarations=declaracoes(self._com_acoes))],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def _resumo(self) -> str:
        """Situação atual da frota, só com as vinherias cadastradas."""
        ids = [device.device_id for device in self._registry.list()]
        return resumo_frota(self._fleet.report(ids), self._fuso)

    async def _gerar(self, cliente, contents: list, config):
        """Uma chamada ao modelo, com as falhas traduzidas para ChatbotError.

        A mensagem de erro nunca inclui a chave nem o corpo da requisição.
        """
        try:
            return await cliente.aio.models.generate_content(
                model=self._settings.gemini_model, contents=contents, config=config)
        except errors.APIError as exc:
            if exc.code == 429:
                raise ChatbotRateLimited(
                    "limite de uso do Gemini atingido, aguarde alguns segundos") from exc
            log.warning("Gemini respondeu HTTP %s", exc.code)
            raise ChatbotUpstreamError(f"falha ao consultar o Gemini (HTTP {exc.code})") from exc
        except Exception as exc:  # rede caída, DNS, timeout: o SDK não padroniza essas falhas
            log.warning("sem conexão com o Gemini: %s", type(exc).__name__)
            raise ChatbotUpstreamError(
                "falha ao consultar o Gemini: sem conexão com a internet?") from exc

    async def ask(self, message: str, history: list[ChatTurn]) -> ChatReply:
        """Responde a pergunta, executando as tools que o Gemini pedir (no máximo 5 chamadas)."""
        cliente = self._cliente()
        contents = [_conteudo(turno.role, turno.text) for turno in history]
        contents.append(_conteudo("user", f"[{self._resumo()}]\n\n{message}"))
        propostas: list[ChatAction] = []
        config = self._config()
        for _ in range(MAX_CHAMADAS):
            resposta = await self._gerar(cliente, contents, config)
            chamadas = resposta.function_calls or []
            if not chamadas:
                texto = (resposta.text or "").strip()
                return ChatReply(reply=texto or SEM_RESPOSTA, actions=propostas)
            contents.append(resposta.candidates[0].content)
            partes = []
            for chamada in chamadas:
                resultado = await self._tools.executar(chamada.name, dict(chamada.args or {}), propostas)
                partes.append(types.Part.from_function_response(name=chamada.name, response=resultado))
            contents.append(types.Content(role="user", parts=partes))
        return ChatReply(reply=SEM_CONCLUSAO, actions=propostas)
```

- [ ] **Passo 4: rodar.** `pytest tests/test_chatbot.py -v`. Esperado: PASS (14 testes). Depois `pytest tests -q`: tudo verde. Confira que `chatbot.py` tem até ~250 linhas.

- [ ] **Passo 5: commit.**
```
git add backend/app/services/chatbot.py backend/tests/test_chatbot.py
git commit -m "feat: adiciona o loop de function calling do chatbot"
```

---

## Subtarefa 7A.9 — Rota, tradução de erros e ligação no app (R7)

**Files:**
- Create: `backend/app/api/routes_chat.py`
- Modify: `backend/app/api/errors.py`, `backend/app/api/deps.py`, `backend/app/main.py`, `backend/tests/test_routes_chat.py`

**Interfaces:**
- Consumes: `Chatbot.ask`, `ChatTools(...)`, `ChatRequest`, `ChatReply`, `ChatbotError` e subclasses.
- Produces: `POST /api/chat`, `get_chatbot(request)`, `app.state.chatbot`.

- [ ] **Passo 1: testes falhando.** Acrescente ao fim de `backend/tests/test_routes_chat.py`:

```python
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.chat_errors import ChatbotRateLimited, ChatbotUpstreamError  # noqa: E402


class ChatbotFalso:
    def __init__(self, erro=None):
        self.erro = erro
        self.perguntas = []

    async def ask(self, message, history):
        self.perguntas.append((message, history))
        if self.erro:
            raise self.erro
        return ChatReply(reply=f"eco: {message}")


@pytest.fixture
def app(tmp_path):
    return create_app(Settings(fiware_host="10.0.0.1", database_path=str(tmp_path / "chat.db")))


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


def test_chat_sem_chave_da_503(client):
    resposta = client.post("/api/chat", json={"message": "oi"})
    assert resposta.status_code == 503
    assert resposta.json() == {"detail": "chatbot não configurado: defina GEMINI_API_KEY no backend/.env",
                               "service": "gemini"}


def test_chat_responde_200(client, app):
    app.state.chatbot = ChatbotFalso()
    resposta = client.post("/api/chat", json={"message": "oi", "history": [{"role": "user", "text": "a"}]})
    assert resposta.status_code == 200
    assert resposta.json() == {"reply": "eco: oi", "actions": []}
    assert app.state.chatbot.perguntas[0][1] == [ChatTurn(role="user", text="a")]


def test_chat_valida_entrada(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    longo = [{"role": "user", "text": "a"}] * 21
    assert client.post("/api/chat", json={"message": "oi", "history": longo}).status_code == 422


@pytest.mark.parametrize("erro, status", [
    (ChatbotRateLimited("limite"), 429),
    (ChatbotUpstreamError("falhou"), 502),
])
def test_chat_traduz_erros(client, app, erro, status):
    app.state.chatbot = ChatbotFalso(erro)
    resposta = client.post("/api/chat", json={"message": "oi"})
    assert resposta.status_code == status
    assert resposta.json()["service"] == "gemini"
```

- [ ] **Passo 2: rodar.** `pytest tests/test_routes_chat.py -v`. Esperado: os testes novos FALHAM com 404 (rota inexistente).

- [ ] **Passo 3: tradução de erros.** Em `backend/app/api/errors.py`:
  - acrescente aos imports:
```python
from app.services.chat_errors import ChatbotError, ChatbotRateLimited, ChatbotUnavailable
```
  - acrescente depois de `_status_registry`:
```python
def _status_chatbot(erro: ChatbotError) -> int:
    """Sem chave dá 503, limite do Gemini dá 429, o resto (Gemini ou rede) dá 502."""
    if isinstance(erro, ChatbotUnavailable):
        return 503
    if isinstance(erro, ChatbotRateLimited):
        return 429
    return 502
```
  - dentro de `register_error_handlers`, no fim:
```python
    @app.exception_handler(ChatbotError)
    async def _trata_chatbot(request: Request, erro: ChatbotError) -> JSONResponse:
        return JSONResponse(status_code=_status_chatbot(erro),
                            content={"detail": erro.message, "service": erro.service})
```
  - atualize o docstring do módulo: "FiwareError, RegistryError e ChatbotError viram JSON ...".

- [ ] **Passo 4: dependência.** Em `backend/app/api/deps.py`, acrescente o import `from app.services.chatbot import Chatbot` e, no fim:
```python
def get_chatbot(request: Request) -> Chatbot:
    """Chatbot da aplicação."""
    return request.app.state.chatbot
```

- [ ] **Passo 5: rota.** Crie `backend/app/api/routes_chat.py`:
```python
"""
Rota do chatbot: recebe a pergunta e o histórico do painel e devolve a
resposta do assistente com as ações propostas (que o painel confirma).
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_chatbot
from app.models.schemas_chat import ChatReply, ChatRequest
from app.services.chatbot import Chatbot

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatReply)
async def chat(pedido: ChatRequest, chatbot: Chatbot = Depends(get_chatbot)) -> ChatReply:
    """Pergunta em linguagem natural; a vinheria é resolvida pelo próprio texto."""
    return await chatbot.ask(pedido.message, pedido.history)
```

- [ ] **Passo 6: ligar no app.** Em `backend/app/main.py`:
  - acrescente `routes_chat,` na lista de `from app.api import (...)`, em ordem alfabética, depois de `routes_alerts,`;
  - acrescente os imports `from app.services.chat_tools import ChatTools` e `from app.services.chatbot import Chatbot`;
  - logo depois da linha `app.state.control = DeviceControl(...)`, acrescente:
```python
    chat_tools = ChatTools(registry, app.state.readings, fleet, alerts, limits)
    app.state.chatbot = Chatbot(chat_tools, registry, fleet, settings)
```
  - depois de `app.include_router(routes_fleet.router)`, acrescente `app.include_router(routes_chat.router)`;
  - no docstring do módulo, inclua "chatbot" na lista de services.

- [ ] **Passo 7: rodar.** `pytest tests -q`. Esperado: tudo verde.

- [ ] **Passo 8: conferência sem chave.** Em `backend/`, com o `.env` real, rode `uvicorn app.main:app --reload`. No Swagger (`http://localhost:8000/docs`), `POST /api/chat` com `{"message": "oi"}` deve dar **200** (a chave já está no `.env` desde a 7A.1). Para conferir o 503: pare o uvicorn, rode `$env:GEMINI_API_KEY=" "` no mesmo terminal e suba de novo. Esperado: 503 com `"chatbot não configurado..."`. Depois, `Remove-Item Env:GEMINI_API_KEY` e suba de novo.

  > `_env` trata o valor em branco como ausente, mas o `load_dotenv(override=False)` não sobrescreve variável já definida, então o espaço deixa a chave vazia só nesse terminal.

- [ ] **Passo 9: teste real pelo Swagger.** Com EC2 e ao menos um Wokwi ligados: `{"message": "Como está a vinheria de São Paulo?"}`. Esperado: 200 com `reply` em português citando temperatura, umidade e luminosidade da `vinheria001`. Anote a resposta para o relatório da subtarefa.

- [ ] **Passo 10: commit.**
```
git add backend/app/api/routes_chat.py backend/app/api/errors.py backend/app/api/deps.py backend/app/main.py backend/tests/test_routes_chat.py
git commit -m "feat: expoe o chatbot em POST /api/chat"
```

---

## Subtarefa 7A.10 — Front: cliente e lógica pura do chat (R8.1, R8.2)

**Files:**
- Modify: `frontend/src/api/client.js`
- Create: `frontend/src/lib/chat.js`, `frontend/src/lib/chat.test.js`

**Interfaces:**
- Produces:
  - `api.sendChat(message, history)`;
  - `MAX_HISTORICO = 20`, `SUGESTOES` (array de strings);
  - `novaMensagem(role, text, extras)`, que devolve `{ id, role, text, ...extras }`;
  - `montarHistorico(mensagens)`, que devolve `[{ role, text }]`;
  - `marcarFalha(mensagens, id)`;
  - `acoesIniciais(actions)`, que devolve as ações com `estado: 'pendente', detalhe: null`;
  - `trocarEstadoAcao(mensagens, mensagemId, indice, estado, detalhe)`;
  - `podeDecidir(estado)`;
  - `textoFeito(acao, resposta)`.

- [ ] **Passo 1: teste falhando.** Crie `frontend/src/lib/chat.test.js`:

```js
/** Testes da lógica pura do chat (Task 7A). */
import { describe, expect, it } from 'vitest';
import {
  MAX_HISTORICO,
  acoesIniciais,
  marcarFalha,
  montarHistorico,
  novaMensagem,
  podeDecidir,
  textoFeito,
  trocarEstadoAcao,
} from './chat.js';

describe('novaMensagem', () => {
  it('gera ids diferentes', () => {
    expect(novaMensagem('user', 'a').id).not.toBe(novaMensagem('user', 'a').id);
  });
});

describe('montarHistorico', () => {
  it('manda só turnos de usuário e modelo, sem erros nem perguntas que falharam', () => {
    const mensagens = [
      novaMensagem('user', 'oi'),
      novaMensagem('model', 'olá', { acoes: [] }),
      novaMensagem('user', 'caiu', { falhou: true }),
      novaMensagem('erro', 'Backend indisponível'),
    ];
    expect(montarHistorico(mensagens)).toEqual([
      { role: 'user', text: 'oi' },
      { role: 'model', text: 'olá' },
    ]);
  });

  it('corta nos últimos turnos', () => {
    const mensagens = Array.from({ length: 30 }, (_, i) => novaMensagem(i % 2 ? 'model' : 'user', `t${i}`));
    const historico = montarHistorico(mensagens);
    expect(historico).toHaveLength(MAX_HISTORICO);
    expect(historico.at(-1).text).toBe('t29');
  });
});

describe('marcarFalha', () => {
  it('marca só a mensagem indicada', () => {
    const [a, b] = [novaMensagem('user', 'a'), novaMensagem('user', 'b')];
    const resultado = marcarFalha([a, b], b.id);
    expect(resultado.map((m) => Boolean(m.falhou))).toEqual([false, true]);
    expect(a.falhou).toBeUndefined();
  });
});

describe('ações', () => {
  const acao = { kind: 'command', device_id: 'vinheria002', name: 'Vinheria Mineira', summary: 'Piscar', command: 'blink_lux' };

  it('nascem pendentes', () => {
    expect(acoesIniciais([acao])[0]).toMatchObject({ estado: 'pendente', detalhe: null });
    expect(acoesIniciais(undefined)).toEqual([]);
  });

  it('trocam de estado sem mexer nas outras mensagens', () => {
    const msg = novaMensagem('model', 'ok', { acoes: acoesIniciais([acao, acao]) });
    const outra = novaMensagem('user', 'x');
    const [m1, m2] = trocarEstadoAcao([msg, outra], msg.id, 1, 'feito', 'Comando enviado.');
    expect(m1.acoes.map((a) => a.estado)).toEqual(['pendente', 'feito']);
    expect(m1.acoes[1].detalhe).toBe('Comando enviado.');
    expect(m2).toBe(outra);
    expect(msg.acoes[1].estado).toBe('pendente');
  });

  it('só pendente e erro podem ser decididos (sem clique duplo em executando)', () => {
    expect(['pendente', 'executando', 'feito', 'cancelado', 'erro'].map(podeDecidir))
      .toEqual([true, false, false, false, true]);
  });

  it('descrevem o resultado', () => {
    expect(textoFeito(acao, null)).toBe('Comando enviado.');
    expect(textoFeito({ kind: 'limits' }, { device_sync: 'enviado' })).toBe('Faixa salva e enviada ao ESP32.');
    expect(textoFeito({ kind: 'limits' }, { device_sync: 'pendente' })).toBe('Faixa salva; o ESP32 recebe quando voltar.');
  });
});
```

- [ ] **Passo 2: rodar.** Em `frontend/`: `npx vitest run src/lib/chat.test.js`. Esperado: FAIL, com `Failed to resolve import "./chat.js"`.

- [ ] **Passo 3: implementar** `frontend/src/lib/chat.js`:

```js
/**
 * Lógica pura do chat (Task 7A): mensagens, histórico enviado ao backend e
 * estados das ações propostas pelo assistente. Sem React e sem fetch, para
 * ser testada com o Vitest.
 *
 * Mensagem: { id, role: 'user'|'model'|'erro', text, falhou?, acoes? }.
 * Ação: o ChatAction do backend + { estado, detalhe }.
 */

// Turnos anteriores mandados com cada pergunta (o backend aceita até 20)
export const MAX_HISTORICO = 20;

// Perguntas prontas mostradas acima do campo
export const SUGESTOES = [
  'Como está a vinheria de São Paulo?',
  'Alguma vinheria em alerta?',
  'Qual vinheria está mais úmida agora?',
];

let contador = 0;

/** Cria uma mensagem com id único na sessão. */
export function novaMensagem(role, text, extras = {}) {
  contador += 1;
  return { id: `m${Date.now()}-${contador}`, role, text, ...extras };
}

/** Histórico para o backend: só usuário e modelo, sem erros e sem perguntas que falharam. */
export function montarHistorico(mensagens) {
  return mensagens
    .filter((m) => (m.role === 'user' || m.role === 'model') && !m.falhou)
    .slice(-MAX_HISTORICO)
    .map(({ role, text }) => ({ role, text }));
}

/** Marca a pergunta que não teve resposta, para não ir no próximo histórico. */
export function marcarFalha(mensagens, id) {
  return mensagens.map((m) => (m.id === id ? { ...m, falhou: true } : m));
}

/** Ações recebidas do backend, todas aguardando a decisão do usuário. */
export function acoesIniciais(actions = []) {
  return (actions ?? []).map((acao) => ({ ...acao, estado: 'pendente', detalhe: null }));
}

/** Nova lista de mensagens com o estado de uma ação trocado (sem alterar a original). */
export function trocarEstadoAcao(mensagens, mensagemId, indice, estado, detalhe = null) {
  return mensagens.map((m) => {
    if (m.id !== mensagemId) {
      return m;
    }
    const acoes = m.acoes.map((acao, i) => (i === indice ? { ...acao, estado, detalhe } : acao));
    return { ...m, acoes };
  });
}

/** Confirmar e Cancelar só aparecem em pendente e erro (executando bloqueia o clique duplo). */
export function podeDecidir(estado) {
  return estado === 'pendente' || estado === 'erro';
}

/** Texto mostrado depois que a ação deu certo; `resposta` é a do PUT /triggers. */
export function textoFeito(acao, resposta) {
  if (acao.kind !== 'limits') {
    return 'Comando enviado.';
  }
  return resposta?.device_sync === 'enviado'
    ? 'Faixa salva e enviada ao ESP32.'
    : 'Faixa salva; o ESP32 recebe quando voltar.';
}
```

- [ ] **Passo 4: cliente.** Em `frontend/src/api/client.js`, dentro de `api`, depois de `getAlerts`, acrescente:
```js

  /** Pergunta ao chatbot; history = turnos anteriores [{ role: 'user'|'model', text }]. */
  sendChat: (message, history) => request('/api/chat', { method: 'POST', body: { message, history } }),
```

- [ ] **Passo 5: rodar.** `npm test`. Esperado: tudo PASS (112 + 8).

- [ ] **Passo 6: commit.**
```
git add frontend/src/lib/chat.js frontend/src/lib/chat.test.js frontend/src/api/client.js
git commit -m "feat: adiciona a logica pura e o cliente do chat"
```

---

## Subtarefa 7A.11 — Front: contexto do chat (R8.3)

**Files:**
- Create: `frontend/src/context/ChatContext.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: `api.sendChat`, `criarContexto`, as funções de `lib/chat.js`.
- Produces:
  - `ChatProvider`;
  - `useChat()`, que devolve `{ mensagens, enviando, enviar(texto) -> Promise<{ ok, texto? }>, atualizarAcao(mensagemId, indice, estado, detalhe?) }`.

- [ ] **Passo 1: implementar** `frontend/src/context/ChatContext.jsx`:

```jsx
/**
 * Contexto do chat (Task 7A): a conversa vive aqui, acima das rotas, para a
 * página /chat e o painel flutuante mostrarem a mesma conversa e ela
 * sobreviver à troca de página. Recarregar o navegador zera a conversa.
 *
 * enviar(texto) manda a pergunta com o histórico; em falha, acrescenta uma
 * mensagem de erro e devolve o texto para o campo. atualizarAcao troca o
 * estado de um cartão de ação (bloco B).
 */
import { useCallback, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { acoesIniciais, marcarFalha, montarHistorico, novaMensagem, trocarEstadoAcao } from '../lib/chat.js';
import { criarContexto } from './criarContexto.js';

const [Provedor, useChat] = criarContexto('Chat');
export { useChat };

export function ChatProvider({ children }) {
  const [mensagens, setMensagens] = useState([]);
  const [enviando, setEnviando] = useState(false);

  const enviar = useCallback(async (texto) => {
    const limpo = texto.trim();
    if (!limpo || enviando) {
      return { ok: false, texto };
    }
    const historico = montarHistorico(mensagens);
    const pergunta = novaMensagem('user', limpo);
    setMensagens((atuais) => [...atuais, pergunta]);
    setEnviando(true);
    try {
      const resposta = await api.sendChat(limpo, historico);
      const doBot = novaMensagem('model', resposta.reply, { acoes: acoesIniciais(resposta.actions) });
      setMensagens((atuais) => [...atuais, doBot]);
      return { ok: true };
    } catch (falha) {
      setMensagens((atuais) => [...marcarFalha(atuais, pergunta.id), novaMensagem('erro', falha.message)]);
      return { ok: false, texto: limpo };
    } finally {
      setEnviando(false);
    }
  }, [mensagens, enviando]);

  const atualizarAcao = useCallback((mensagemId, indice, estado, detalhe = null) => {
    setMensagens((atuais) => trocarEstadoAcao(atuais, mensagemId, indice, estado, detalhe));
  }, []);

  const valor = useMemo(
    () => ({ mensagens, enviando, enviar, atualizarAcao }),
    [mensagens, enviando, enviar, atualizarAcao],
  );
  return <Provedor value={valor}>{children}</Provedor>;
}
```

- [ ] **Passo 2: envolver o app.** Em `frontend/src/App.jsx`:
  - importe `{ ChatProvider }` de `'./context/ChatContext.jsx'`;
  - envolva o conteúdo de `<FleetProvider>` com `<ChatProvider>...</ChatProvider>` (de `<FiwareBar />` a `<NavInferior />`).

- [ ] **Passo 3: verificar.** Em `frontend/`: `npm run build` (esperado: build ok) e `npm test` (verde). Com `npm run dev`, as telas atuais abrem sem erro no console.

- [ ] **Passo 4: commit.**
```
git add frontend/src/context/ChatContext.jsx frontend/src/App.jsx
git commit -m "feat: adiciona o contexto da conversa do chat"
```

---

## Subtarefa 7A.12 — Front: campo de texto do kit, mensagem e caixa do chat (R9.1, R9.2, R9.5)

**Files:**
- Modify: `frontend/src/components/ui/formulario.jsx` (novo `AreaTexto`, com a classe de entrada compartilhada com o `Campo`)
- Create: `frontend/src/components/ChatMensagem.jsx`, `frontend/src/components/ChatBox.jsx`

**Interfaces:**
- Consumes: `useChat`, `SUGESTOES`, `Botao`, `EstadoVazio`, `MensagemErro`.
- Produces:
  - `AreaTexto({ rotulo, rotuloOculto = false, ...props })` no kit;
  - `ChatMensagem({ mensagem })`;
  - `ChatBox({ className })`.

- [ ] **Passo 1: `AreaTexto` no kit.** Em `frontend/src/components/ui/formulario.jsx`:
  - depois de `VARIANTES`, acrescente:
```js
// Visual de entrada de texto compartilhado por Campo e AreaTexto
const ENTRADA = 'min-h-11 rounded border bg-papel px-3 text-vinho placeholder:text-taupe/70 focus:border-bordo';
```
  - no `Campo`, troque o `className` do `<input>` por `` className={`${ENTRADA} ${erro ? 'border-alerta' : 'border-linha'}`} ``;
  - depois do `Campo`, acrescente:
```jsx
/** Texto de várias linhas com o mesmo visual do Campo; `rotuloOculto` deixa o rótulo só para leitor de tela. */
export function AreaTexto({ rotulo, rotuloOculto = false, ...props }) {
  return (
    <label className="flex flex-1 flex-col gap-1.5">
      <span className={rotuloOculto ? 'sr-only' : 'text-overline uppercase text-taupe'}>{rotulo}</span>
      <textarea className={`${ENTRADA} w-full resize-none border-linha py-2`} {...props} />
    </label>
  );
}
```
  - atualize o docstring do topo: "campo com rótulo, área de texto, botão com variantes...".

- [ ] **Passo 2: `ChatMensagem`.** Crie `frontend/src/components/ChatMensagem.jsx`:

```jsx
/**
 * Uma mensagem da conversa: bolha do usuário à direita (bordô), do
 * assistente à esquerda (papel) e erro do sistema com o ícone de alerta.
 * O texto do assistente vem sem markdown; as quebras de linha são mantidas.
 */
import { MensagemErro } from './ui/index.js';

export default function ChatMensagem({ mensagem }) {
  if (mensagem.role === 'erro') {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl border border-alerta/30 bg-alerta/10 px-4 pt-3 pb-1">
          <MensagemErro erro={mensagem.text} />
        </div>
      </div>
    );
  }
  const doUsuario = mensagem.role === 'user';
  return (
    <div className={`flex ${doUsuario ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${doUsuario ? 'bg-bordo text-papel' : 'border border-linha bg-papel text-vinho'}`}
      >
        <p className="break-words whitespace-pre-wrap">{mensagem.text}</p>
      </div>
    </div>
  );
}
```

- [ ] **Passo 3: `ChatBox`.** Crie `frontend/src/components/ChatBox.jsx`:

```jsx
/**
 * Caixa de conversa usada pela página /chat e pelo painel flutuante:
 * mensagens com rolagem automática, sugestões de pergunta e o campo de
 * texto (Enter envia, Shift+Enter quebra a linha). Se o envio falha, o
 * texto volta para o campo.
 */
import { SendHorizontal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useChat } from '../context/ChatContext.jsx';
import { SUGESTOES } from '../lib/chat.js';
import ChatMensagem from './ChatMensagem.jsx';
import { AreaTexto, Botao, EstadoVazio } from './ui/index.js';

export default function ChatBox({ className = '' }) {
  const { mensagens, enviando, enviar } = useChat();
  const [texto, setTexto] = useState('');
  const fim = useRef(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: 'end' });
  }, [mensagens, enviando]);

  async function mandar(conteudo) {
    if (!conteudo.trim() || enviando) {
      return;
    }
    setTexto('');
    const resultado = await enviar(conteudo);
    if (!resultado.ok && resultado.texto) {
      setTexto(resultado.texto);
    }
  }

  function aoTeclar(evento) {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault();
      mandar(texto);
    }
  }

  return (
    <div className={`flex min-h-0 flex-col ${className}`}>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pb-3" aria-live="polite">
        {mensagens.length === 0 ? (
          <EstadoVazio
            titulo="Pergunte sobre as vinherias"
            texto="O assistente responde com os dados reais do FIWARE. Experimente uma das sugestões abaixo."
          />
        ) : (
          mensagens.map((mensagem) => <ChatMensagem key={mensagem.id} mensagem={mensagem} />)
        )}
        {enviando && (
          <p role="status" className="text-sm text-taupe">
            Pensando…
          </p>
        )}
        <div ref={fim} />
      </div>
      <div className="flex flex-wrap gap-2 pb-3">
        {SUGESTOES.map((sugestao) => (
          <Botao key={sugestao} variante="secundario" disabled={enviando} onClick={() => mandar(sugestao)}>
            {sugestao}
          </Botao>
        ))}
      </div>
      <form
        className="flex items-end gap-2"
        onSubmit={(evento) => {
          evento.preventDefault();
          mandar(texto);
        }}
      >
        <AreaTexto
          rotulo="Mensagem para o assistente"
          rotuloOculto
          rows={2}
          maxLength={1000}
          placeholder="Pergunte sobre uma vinheria…"
          value={texto}
          disabled={enviando}
          onChange={(evento) => setTexto(evento.target.value)}
          onKeyDown={aoTeclar}
        />
        <Botao type="submit" disabled={!texto.trim()} carregando={enviando} textoCarregando="Enviando…">
          <SendHorizontal size={18} strokeWidth={1.5} aria-hidden="true" />
          Enviar
        </Botao>
      </form>
    </div>
  );
}
```

- [ ] **Passo 4: verificar.** `npm run build` (ok) e `npm test` (verde). Rode as conferências estáticas: `Select-String -Path src/components/Chat*.jsx -Pattern "#[0-9a-fA-F]{3,6}|style=|fetch\("` não deve achar nada.

- [ ] **Passo 5: commit.**
```
git add frontend/src/components/ui/formulario.jsx frontend/src/components/ChatMensagem.jsx frontend/src/components/ChatBox.jsx
git commit -m "feat: adiciona a caixa de conversa do chat"
```

---

## Subtarefa 7A.13 — Front: página /chat (R9.3)

**Files:**
- Create: `frontend/src/pages/Chat.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Passo 1: página.** Crie `frontend/src/pages/Chat.jsx`:

```jsx
/**
 * Página /chat: o assistente ocupando a altura útil da tela. A conversa é a
 * mesma do painel flutuante (ChatContext).
 */
import ChatBox from '../components/ChatBox.jsx';
import { Cartao, Titulo } from '../components/ui/index.js';

export default function Chat() {
  return (
    <div className="flex h-[calc(100dvh-14rem)] min-h-96 flex-col md:h-[calc(100dvh-12rem)]">
      <Titulo overline="Assistente">Chat</Titulo>
      <Cartao className="flex min-h-0 flex-1 flex-col">
        <ChatBox className="flex-1" />
      </Cartao>
    </div>
  );
}
```

- [ ] **Passo 2: rota.** Em `frontend/src/App.jsx`:
  - importe `Chat from './pages/Chat.jsx'`;
  - troque `<Placeholder titulo="Chat" task="Task 7A" />` por `<Chat />`;
  - no docstring, troque "Só o /chat (Task 7A) ainda é Placeholder." por "O Placeholder fica só para o 404.". O `Placeholder` continua importado por causa do `*`.

- [ ] **Passo 3: verificar no navegador.** Com backend e `npm run dev`, abra `/chat` no desktop e no celular (DevTools, 390 px):
  - mensagens, sugestões e campo cabem sem rolagem da página inteira, e só a lista rola;
  - "Alguma vinheria em alerta?" responde.
  Se a altura `calc` deixar sobra ou corte com a `NavInferior`, ajuste só os números de `14rem`/`12rem` e anote no relatório.

- [ ] **Passo 4: commit.**
```
git add frontend/src/pages/Chat.jsx frontend/src/App.jsx
git commit -m "feat: adiciona a pagina do chat"
```

---

## Subtarefa 7A.14 — Front: botão e painel flutuantes (R9.4)

**Files:**
- Create: `frontend/src/components/ChatFlutuante.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: `ChatBox`, `BotaoIcone`, `Subtitulo`, `useLocation` do `react-router-dom`.

- [ ] **Passo 1: implementar** `frontend/src/components/ChatFlutuante.jsx`:

```jsx
/**
 * Chat flutuante: botão redondo no canto inferior esquerdo (o direito é dos
 * toasts) que abre o assistente sem sair da tela atual. No desktop vira um
 * painel de 400 px no mesmo canto; no celular ocupa a tela toda. Fecha com
 * Esc ou com o X. Não aparece em /chat, onde a página já é o chat.
 */
import { MessageCircle, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import ChatBox from './ChatBox.jsx';
import { BotaoIcone, Subtitulo } from './ui/index.js';

export default function ChatFlutuante() {
  const { pathname } = useLocation();
  const [aberto, setAberto] = useState(false);

  useEffect(() => {
    if (!aberto) {
      return undefined;
    }
    function aoTeclar(evento) {
      if (evento.key === 'Escape') {
        setAberto(false);
      }
    }
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  }, [aberto]);

  if (pathname === '/chat') {
    return null;
  }

  if (!aberto) {
    return (
      <button
        type="button"
        aria-label="Abrir o chat com o assistente"
        title="Assistente"
        onClick={() => setAberto(true)}
        className="fixed bottom-20 left-4 z-30 inline-flex size-14 items-center justify-center rounded-full bg-bordo text-papel shadow-media transition-colors duration-150 hover:bg-vinho md:bottom-6 md:left-6"
      >
        <MessageCircle size={24} strokeWidth={1.5} aria-hidden="true" />
      </button>
    );
  }

  return (
    <div
      role="dialog"
      aria-label="Chat com o assistente"
      className="fixed inset-0 z-50 flex animate-entrar flex-col bg-papel p-4 md:inset-auto md:bottom-6 md:left-6 md:h-[min(40rem,calc(100dvh-3rem))] md:w-100 md:rounded-2xl md:border md:border-linha md:shadow-media"
    >
      <div className="flex items-center justify-between">
        <Subtitulo>Assistente</Subtitulo>
        <BotaoIcone icone={X} rotulo="Fechar o chat" className="-mt-4" onClick={() => setAberto(false)} />
      </div>
      <ChatBox className="min-h-0 flex-1" />
    </div>
  );
}
```

- [ ] **Passo 2: incluir no app.** Em `frontend/src/App.jsx`, importe `ChatFlutuante from './components/ChatFlutuante.jsx'` e coloque `<ChatFlutuante />` logo antes de `<NavInferior />`, dentro do `ChatProvider`. Atualize o docstring: "O ChatFlutuante abre o assistente de qualquer tela, menos de /chat".

- [ ] **Passo 3: verificar no navegador** (desktop e 390 px):
  - o botão aparece em `/`, no detalhe, em `/alertas` e em `/dispositivos`, e não em `/chat`;
  - no celular fica acima da barra inferior, e um toast que apareça fica por cima dele;
  - abrir, perguntar, fechar com Esc, ir para `/chat`: a mesma conversa está lá;
  - voltar e abrir de novo: a conversa continua.

- [ ] **Passo 4: commit.**
```
git add frontend/src/components/ChatFlutuante.jsx frontend/src/App.jsx
git commit -m "feat: adiciona o chat flutuante em todas as telas"
```

---

## Subtarefa 7A.15 — Verificação do bloco A

- [ ] **Passo 1: suítes.**
  - em `backend/`: `pytest tests -q` (verde);
  - em `frontend/`: `npm test` e `npm run build` (verdes).
  Anote os totais.
- [ ] **Passo 2: segredos.** Na raiz: `git grep -n "AIza"`, sem resultado. `git status` não pode mostrar `backend/.env`.
- [ ] **Passo 3: ensaio manual** (EC2 e 2 Wokwi ligados; spec §7, itens 4.1, 4.2, 4.3 e 4.6):
  1. As três sugestões respondem. A média, o mínimo e o máximo de "Como está a vinheria de São Paulo?" batem com o gráfico do detalhe ("Por período", última hora).
  2. Pare um Wokwi e espere ~35 s. "Qual vinheria está mais úmida agora?" começa avisando da vinheria offline.
  3. Esquente o DHT de um Wokwi até o alerta. "Alguma vinheria em alerta?" cita só aquela vinheria.
  4. Uma conversa iniciada no painel flutuante continua em `/chat`.
  Anote o resultado de cada item. Se algum falhar, **pare** e reporte (não ajuste o prompt por conta própria).
- [ ] **Passo 4: registro.** No `PLANO-CP5-VINHERIA.md`, logo abaixo do título `### Task 7A`, acrescente uma nota: "**Bloco A FEITO em <data>** — commits <primeiro>..<último>; <n> testes do backend e <n> do front; ensaio: <resultado>; desvios: <lista ou 'nenhum'>." Commit: `git commit -am "docs: registra o bloco A da task 7a"`.

**Pare aqui e espere a revisão do usuário.** O bloco B só começa com autorização explícita.

---

# Bloco B — ações com confirmação

## Subtarefa 7A.16 — Tools de proposta (R11)

**Files:**
- Create: `backend/app/services/chat_acoes.py`, `backend/tests/test_chat_acoes.py`

**Interfaces:**
- Consumes:
  - `resolver`, `checar_atributo` e `ATRIBUTOS` de `chat_tools`;
  - `ChatTools.registrar`, `FleetState.status_of`, `LimitsStore.get`;
  - `AttrLimits`, `ChatAction`, `NOME_ATRIBUTO`, `UNIDADE`.
- Produces: `ChatAcoes(registry, fleet, limits)`, com `async propor_comando(vinheria, comando, propostas)`, `async propor_faixa(vinheria, atributo, propostas, minimo=None, maximo=None)` e `registrar_em(tools)`.

- [ ] **Passo 1: teste falhando.** Crie `backend/tests/test_chat_acoes.py`:

```python
"""Testes das tools de proposta do chatbot (spec R11): propõem, nunca executam."""
import pytest

from app.services.chat_acoes import ChatAcoes
from app.services.chat_tools import ChatTools
from tests.fakes import status_vinheria

pytestmark = pytest.mark.anyio


@pytest.fixture
def tools(registry, fleet, alert_log, limits, cadastrar, fiware_falso):
    cadastrar("001", "Vinheria Paulista", "São Paulo")
    cadastrar("002", "Vinheria Mineira", "Belo Horizonte")
    chat_tools = ChatTools(registry, None, fleet, alert_log, limits)
    ChatAcoes(registry, fleet, limits).registrar_em(chat_tools)
    return chat_tools


def com_status(fleet, relogio, device_id, status):
    fleet.replace([status_vinheria(device_id, status)], at=relogio.iso())


async def test_propor_comando(tools, fleet, relogio):
    com_status(fleet, relogio, "vinheria002", "ok")
    propostas = []
    r = await tools.executar("propor_comando", {"vinheria": "Mineira", "comando": "blink_lux"}, propostas)
    assert r["aguardando_confirmacao"] is True
    assert [(p.kind, p.device_id, p.command) for p in propostas] == [("command", "vinheria002", "blink_lux")]
    assert propostas[0].summary == "Piscar o alerta de luminosidade (blink_lux) na Vinheria Mineira"


@pytest.mark.parametrize("status", ["offline", "configurando"])
async def test_propor_comando_recusa_indisponivel(tools, fleet, relogio, status):
    com_status(fleet, relogio, "vinheria001", status)
    propostas = []
    r = await tools.executar("propor_comando", {"vinheria": "001", "comando": "alert_off"}, propostas)
    assert "erro" in r and propostas == []


async def test_propor_comando_invalido(tools):
    propostas = []
    r = await tools.executar("propor_comando", {"vinheria": "001", "comando": "set_limits"}, propostas)
    assert "comando inválido" in r["erro"] and propostas == []


async def test_propor_faixa_so_maximo(tools, limits):
    propostas = []
    r = await tools.executar("propor_faixa",
                             {"vinheria": "São Paulo", "atributo": "temperature", "maximo": 20}, propostas)
    assert r["aguardando_confirmacao"] is True
    proposta = propostas[0]
    assert proposta.kind == "limits"
    assert (proposta.limits.temperature.min, proposta.limits.temperature.max) == (12, 20)
    assert proposta.limits.humidity == limits.get("vinheria001").humidity
    assert proposta.summary == "Temperatura máx. 18 → 20 °C na Vinheria Paulista"
    assert limits.get("vinheria001").temperature.max == 18  # nada gravado


async def test_propor_faixa_min_e_max(tools):
    propostas = []
    await tools.executar("propor_faixa", {"vinheria": "002", "atributo": "humidity",
                                          "minimo": 45, "maximo": "75"}, propostas)
    assert propostas[0].summary == "Umidade mín. 50 → 45 %, máx. 70 → 75 % na Vinheria Mineira"


@pytest.mark.parametrize("args", [
    {"atributo": "temperature"},                          # sem minimo nem maximo
    {"atributo": "temperature", "minimo": 19},            # 19 >= máx atual 18
    {"atributo": "temperature", "maximo": "muito"},       # não numérico
    {"atributo": "pressao", "maximo": 3},                 # atributo inválido
])
async def test_propor_faixa_invalida(tools, args):
    propostas = []
    r = await tools.executar("propor_faixa", {"vinheria": "001", **args}, propostas)
    assert "erro" in r and propostas == []


async def test_propostas_nao_tocam_o_fiware(tools, fiware_falso, fleet, relogio):
    com_status(fleet, relogio, "vinheria001", "ok")
    await tools.executar("propor_comando", {"vinheria": "001", "comando": "blink_temp"}, [])
    await tools.executar("propor_faixa", {"vinheria": "001", "atributo": "luminosity", "maximo": 40}, [])
    assert fiware_falso.comandos == [] and fiware_falso.atualizacoes == []
```

- [ ] **Passo 2: rodar.** `pytest tests/test_chat_acoes.py -v`. Esperado: FAIL com `ModuleNotFoundError: No module named 'app.services.chat_acoes'`.

- [ ] **Passo 3: implementar** `backend/app/services/chat_acoes.py`:

```python
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
```

- [ ] **Passo 4: rodar.** `pytest tests/test_chat_acoes.py -v`. Esperado: PASS (11 testes).

- [ ] **Passo 5: commit.**
```
git add backend/app/services/chat_acoes.py backend/tests/test_chat_acoes.py
git commit -m "feat: adiciona as tools de proposta de acao do chatbot"
```

---

## Subtarefa 7A.17 — Declarações e chatbot com ações (R5.2, R6.3, R12)

**Files:**
- Modify: `backend/app/services/chat_declarations.py`, `backend/app/services/chatbot.py`, `backend/app/main.py`, `backend/tests/test_chat_declarations.py`, `backend/tests/test_chatbot.py`

- [ ] **Passo 1: testes falhando.**
  - em `backend/tests/test_chat_declarations.py`, acrescente:
```python
def test_declaracoes_de_acao_so_com_acoes():
    nomes = {d.name for d in declaracoes(com_acoes=True)}
    assert nomes == LEITURA | {"propor_comando", "propor_faixa"}
    comando = _por_nome(declaracoes(com_acoes=True))["propor_comando"]
    assert comando.parameters.properties["comando"].enum == ["blink_temp", "blink_hum", "blink_lux", "alert_off"]
```
  - em `backend/tests/test_chatbot.py`, acrescente:
```python
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
```

- [ ] **Passo 2: rodar.** `pytest tests/test_chat_declarations.py tests/test_chatbot.py -v`. Esperado: os dois novos FALHAM.

- [ ] **Passo 3: declarações.** Em `backend/app/services/chat_declarations.py`, troque `ACOES: list[types.FunctionDeclaration] = []` por:

```python
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
```

- [ ] **Passo 4: instrução.** Em `backend/app/services/chatbot.py`, troque `INSTRUCAO_ACOES = ""` por:

```python
INSTRUCAO_ACOES = """
- Você pode propor ações com propor_comando e propor_faixa, mas só quando o usuário pedir uma ação. Nunca proponha por iniciativa própria; no máximo, sugira em texto.
- As ações NÃO são executadas por você: elas aparecem num cartão e só acontecem quando o usuário clicar em Confirmar. Diga isso na resposta, sem afirmar que a ação já foi feita.
- Se a proposta voltar com "erro", explique o motivo ao usuário."""
```

- [ ] **Passo 5: ligar no app.** Em `backend/app/main.py`:
  - importe `from app.services.chat_acoes import ChatAcoes`;
  - troque as duas linhas do chatbot por:
```python
    chat_tools = ChatTools(registry, app.state.readings, fleet, alerts, limits)
    ChatAcoes(registry, fleet, limits).registrar_em(chat_tools)
    app.state.chatbot = Chatbot(chat_tools, registry, fleet, settings, com_acoes=True)
```

- [ ] **Passo 6: rodar.** `pytest tests -q`. Esperado: tudo verde.

- [ ] **Passo 7: commit.**
```
git add backend/app/services/chat_declarations.py backend/app/services/chatbot.py backend/app/main.py backend/tests/test_chat_declarations.py backend/tests/test_chatbot.py
git commit -m "feat: liga as acoes com confirmacao no chatbot"
```

---

## Subtarefa 7A.18 — Front: cartão de ação e sugestão de ação (R13)

**Files:**
- Create: `frontend/src/components/CartaoAcao.jsx`
- Modify: `frontend/src/components/ChatMensagem.jsx`, `frontend/src/lib/chat.js`

**Interfaces:**
- Consumes: `useChat().atualizarAcao`, `api.sendCommand`, `api.saveTriggers`, `podeDecidir`, `textoFeito`.

> **Por que não usa o `useAcao`:** o estado da ação precisa sobreviver quando o cartão desmonta (fechar o painel flutuante, trocar para `/chat`). Por isso ele mora no `ChatContext`, e não no estado local que o `useAcao` guarda.

- [ ] **Passo 1: implementar** `frontend/src/components/CartaoAcao.jsx`:

```jsx
/**
 * Cartão de uma ação proposta pelo assistente (bloco B da Task 7A).
 * Mostra o resumo e, enquanto pendente ou com erro, Confirmar e Cancelar.
 * Confirmar executa pelas rotas que o painel já usa (comando manual e
 * faixa ideal); o backend recusa vinheria offline (409) e o erro aparece
 * aqui. O estado fica no ChatContext para sobreviver à troca de tela.
 */
import { api } from '../api/client.js';
import { useChat } from '../context/ChatContext.jsx';
import { podeDecidir, textoFeito } from '../lib/chat.js';
import { Botao, MensagemErro } from './ui/index.js';

/** Executa a ação no backend e devolve o texto de sucesso. */
async function executarAcao(acao) {
  if (acao.kind === 'command') {
    await api.sendCommand(acao.device_id, acao.command);
    return textoFeito(acao, null);
  }
  return textoFeito(acao, await api.saveTriggers(acao.device_id, acao.limits));
}

export default function CartaoAcao({ mensagemId, indice, acao }) {
  const { atualizarAcao } = useChat();
  const executando = acao.estado === 'executando';

  async function confirmar() {
    atualizarAcao(mensagemId, indice, 'executando');
    try {
      atualizarAcao(mensagemId, indice, 'feito', await executarAcao(acao));
    } catch (falha) {
      atualizarAcao(mensagemId, indice, 'erro', falha.message);
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-linha bg-papel p-3 text-vinho">
      <p className="text-sm font-medium">{acao.summary}</p>
      {acao.estado === 'feito' && (
        <p role="status" className="mt-2 text-sm text-ok">
          {acao.detalhe}
        </p>
      )}
      {acao.estado === 'cancelado' && <p className="mt-2 text-sm text-taupe">Cancelado.</p>}
      {acao.estado === 'erro' && (
        <div className="mt-2">
          <MensagemErro erro={acao.detalhe} />
        </div>
      )}
      {(podeDecidir(acao.estado) || executando) && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Botao carregando={executando} textoCarregando="Enviando…" onClick={confirmar}>
            {acao.estado === 'erro' ? 'Tentar de novo' : 'Confirmar'}
          </Botao>
          <Botao
            variante="secundario"
            disabled={executando}
            onClick={() => atualizarAcao(mensagemId, indice, 'cancelado')}
          >
            Cancelar
          </Botao>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Passo 2: cartões na bolha.** Em `frontend/src/components/ChatMensagem.jsx`:
  - importe `CartaoAcao from './CartaoAcao.jsx'`;
  - logo depois do `<p className="break-words whitespace-pre-wrap">...</p>`, acrescente:
```jsx
        {mensagem.acoes?.map((acao, indice) => (
          <CartaoAcao key={indice} mensagemId={mensagem.id} indice={indice} acao={acao} />
        ))}
```
  - no docstring: "...e os cartões das ações propostas, embaixo do texto do assistente."

- [ ] **Passo 3: sugestão de ação.** Em `frontend/src/lib/chat.js`, acrescente `'Desligue o alerta da vinheria 001',` como último item de `SUGESTOES`.

- [ ] **Passo 4: verificar.** `npm test` e `npm run build` (verdes). Conferência estática do Passo 4 da 7A.12, agora incluindo `src/components/CartaoAcao.jsx`.

- [ ] **Passo 5: commit.**
```
git add frontend/src/components/CartaoAcao.jsx frontend/src/components/ChatMensagem.jsx frontend/src/lib/chat.js
git commit -m "feat: adiciona o cartao de confirmacao das acoes do chat"
```

---

## Subtarefa 7A.19 — Verificação final e registro

- [ ] **Passo 1: suítes.**
  - em `backend/`: `pytest tests -q`;
  - em `frontend/`: `npm test` e `npm run build`.
  Tudo verde; anote os totais.
- [ ] **Passo 2: tamanhos.** Nenhum arquivo criado nesta task passa de ~250 linhas. Na raiz:
```
Get-ChildItem backend/app/services/chat*.py, backend/app/api/routes_chat.py, frontend/src/components/Chat*.jsx, frontend/src/components/CartaoAcao.jsx, frontend/src/lib/chat.js, frontend/src/context/ChatContext.jsx | ForEach-Object { "{0} {1}" -f (Get-Content $_ | Measure-Object -Line).Lines, $_.Name }
```
- [ ] **Passo 3: camadas.** `Select-String -Path backend/app/api/*.py -Pattern "google.genai|httpx"` não acha nada. `Select-String -Path frontend/src/components/*.jsx, frontend/src/pages/*.jsx, frontend/src/context/*.jsx -Pattern "fetch\("` não acha nada.
- [ ] **Passo 4: segredos.** `git grep -n "AIza"` sem resultado; `git status` sem `backend/.env`.
- [ ] **Passo 5: ensaio manual** (spec §7, itens 4.4 e 4.5; EC2 e 2 Wokwi):
  1. "Pisque a luz da vinheria 002" mostra o cartão "Piscar o alerta de luminosidade (blink_lux) na ...". Confirmar faz só o ESP32 da 002 reagir (3 bipes rápidos). Em outra proposta, Cancelar não envia nada.
  2. "Aumente o máximo de temperatura de São Paulo para 20" mostra o cartão "Temperatura máx. 18 → 20 °C ...". Confirmar faz a faixa nova aparecer no detalhe da vinheria e no LCD.
  3. Pare o Wokwi da 002 e espere ~35 s. "Desligue o alerta da 002" faz o bot explicar que ela está offline, sem cartão.
  4. Repita rapidamente o item 1 do bloco A (números batem) para garantir que nada regrediu.
- [ ] **Passo 6: limpeza.** Apague `<scratchpad>/sonda_genai.py`.
- [ ] **Passo 7: registro.**
  - no `PLANO-CP5-VINHERIA.md`, transforme a nota do bloco A em "**Task 7A FEITA em <data>** — commits <primeiro>..<último>; testes: backend <n>, front <n>; ensaio: <resultado dos itens>; desvios: <lista ou 'nenhum'>";
  - em `### Task 7A`, troque a linha **Files:** pela lista real deste plano;
  - marque os passos antigos como `[x]`.
  Commit: `git commit -am "docs: fecha a task 7a do chatbot"`.

**Pare e espere a revisão do usuário.** A próxima é a Task 7B.
