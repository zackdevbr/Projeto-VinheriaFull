# Spec — Task 7A: Chatbot Gemini multi-vinheria

> Método spec-driven: esta spec diz **o que** a Task 7A entrega e **como saber que está certo**. O passo a passo fica em [`plan.md`](plan.md), que segue esta spec item por item. Se as duas divergirem, a spec manda e o executor para e devolve para planejamento.
>
> Fonte: Task 7A de [`PLANO-CP5-VINHERIA.md`](../../../PLANO-CP5-VINHERIA.md), PRD (chatbot multi-vinheria), design system da Task 5B ([`../task-5b-design-system/spec.md`](../task-5b-design-system/spec.md)) e as decisões tomadas com o usuário em 20/10/2026. Formato do `CLAUDE.md` §3.

---

## 1. Contexto

**Por que existe.** O chatbot é um dos diferenciais da entrega (critério "Diferencial", 10 %) e entra no roteiro do hands-on: o operador pergunta em linguagem natural sobre qualquer vinheria ("como está a temperatura da vinheria de São Paulo?") e recebe resposta com números reais do STH-Comet. O bot também avisa sozinho de vinherias em alerta ou offline. Na revisão de 20/10/2026, o usuário pediu que o bot também **proponha ações** (disparar ou desligar alerta, mudar a faixa ideal), sempre executadas só depois de um clique de confirmação.

**O que já está pronto.**
- **Backend** (285 testes), peças reaproveitadas:
  - `resolve_vinheria(texto, devices)` em `services/vinheria_resolver.py`, que lança `AmbiguousVinheria(message, options)` ou `VinheriaNotFound`.
  - `DeviceRegistry.list()` e `DeviceRegistry.get(device_id)`.
  - `FleetState.report(device_ids)` e `FleetState.get(device_id)`, com o retrato de cada vinheria: `status` (`ok|alerta|offline|configurando`), `offline_reason`, `seconds_since`, `current`, `score` e `active_alerts`, mais `fiware_online` da EC2.
  - `ReadingsService.history(device_id, HistoryQuery)`, que devolve `[HistoryPoint(ts, value)]`.
  - `AlertLog.list(device_id, limit)` e `LimitsStore.get(device_id)`, que devolve `Limits`.
  - `AttrLimits` (valida min < max) e `Limits` em `models/schemas.py`.
  - Rotas que executam as ações: `PUT /api/devices/{id}/triggers` (devolve `device_sync: enviado|pendente`) e `POST /api/devices/{id}/commands` (409 se offline ou configurando).
  - `register_error_handlers` em `api/errors.py` e injeção por `app.state` em `api/deps.py`.
  - `.gitignore` com `.env` (Task 2).
- **Front** (112 testes):
  - `api/client.js`, com `api.sendCommand` e `api.saveTriggers`;
  - `criarContexto`, `useAcao`;
  - kit `components/ui/` (`Titulo`, `Subtitulo`, `Cartao`, `Botao`, `BotaoIcone`, `Campo`, `MensagemErro`, `Nota`, `EstadoVazio`, `Esqueleto`);
  - rota `/chat` hoje como `Placeholder` em `App.jsx`.

**Achado da exploração.** A consulta por datas no STH (`fiware_sth.py`) pede `hLimit=500, hOffset=0` e recebe os **500 pontos mais antigos** da janela. Com leitura a cada 2 s, 1 h pode ter mais de 500 pontos. Por isso as tools pedem `last_n=500` (os mais novos) e filtram pela janela em Python, devolvendo o período que os pontos de fato cobrem.

**O que depende desta task.** O ensaio do hands-on (item 8 da verificação end-to-end do plano) e os manuais da Task 8.

## 2. Objetivo

Com a chave do Gemini no `backend/.env`, a EC2 e ao menos dois Wokwi ligados:
- `/chat` e o painel flutuante (aberto de qualquer tela) respondem em português a perguntas sobre uma vinheria, várias ou a frota, com números que batem com os gráficos do detalhe;
- o bot cita sozinho uma vinheria offline ou em alerta;
- pedidos de ação ("pisque a luz da 002", "aumente o máximo de temperatura de São Paulo para 20") geram um cartão com Confirmar e Cancelar, e só o Confirmar executa.

## 3. Requisitos e critérios de aceite

Formato: **QUANDO** <situação>, o sistema **DEVE** <comportamento>. Testes automáticos estão no `plan.md`; itens *(manual)* são conferidos com a EC2 e o navegador.

O trabalho se divide em dois blocos:
- **Bloco A** (R1–R10): o núcleo.
- **Bloco B** (R11–R13): as ações. É o corte se o prazo apertar. O corte não quebra o contrato, porque `actions` já existe no bloco A, sempre como `[]`.

### Bloco A — núcleo

#### R1 — Configuração
- **R1.1** `Settings` DEVE ganhar `gemini_api_key: str = ""` e `gemini_model: str = "gemini-2.5-flash"`, lidos de `GEMINI_API_KEY` e `GEMINI_MODEL` em `load_settings`.
- **R1.2** `backend/.env.example` DEVE ganhar as duas chaves, com `GEMINI_API_KEY=` vazio e um comentário dizendo que a chave real fica só no `.env`.
- **R1.3** `requirements.txt` DEVE ganhar `google-genai==<versão confirmada na sonda R10>`.
- **R1.4** A chave NUNCA aparece em arquivo versionado, em log nem em resposta HTTP.

#### R2 — Contrato (`models/schemas_chat.py`)
- **R2.1** `ChatTurn { role: "user" | "model", text: str (1–4000) }`.
- **R2.2** `ChatRequest { message: str (1–1000, sem espaços nas pontas), history: list[ChatTurn] = [] (no máximo 20) }`. Fora disso, 422.
- **R2.3** `ChatAction { kind: "command" | "limits", device_id, name, summary, command: str | None, limits: Limits | None }`.
- **R2.4** `ChatReply { reply: str, actions: list[ChatAction] = [] }`.

#### R3 — Estatísticas puras (`services/chat_stats.py`)
- **R3.1** `filtrar_janela(pontos, horas, agora) -> list[HistoryPoint]`: mantém os pontos com `ts >= agora - horas`. Aceita `ts` com `Z` ou com offset.
- **R3.2** `estatisticas(pontos, atributo, horas_pedidas) -> dict` com:
  - `n`, `media`, `minimo`, `maximo` e `desvio` (desvio-padrão amostral; `None` com n < 2), arredondados a 1 casa;
  - `inicio` e `fim` (ts do primeiro e do último ponto, no fuso local da máquina, formato `DD/MM HH:MM`);
  - `periodo_coberto_horas` (de `inicio` a `fim`, 1 casa);
  - `janela_completa: bool` (falso quando o período coberto é menor que 90 % de `horas_pedidas`);
  - `tendencia`;
  - `unidade` ("°C" para temperatura, "%" para umidade e luminosidade).
  Com n = 0, devolve `{ "n": 0 }`.
- **R3.3** `tendencia` é "estável" se a amplitude (máx − mín) for menor que o limiar do atributo: 1,0 °C (temperatura), 3 % (umidade) ou 5 % (luminosidade). Senão, o sinal da inclinação da reta de mínimos quadrados (valor × tempo) decide: "subindo" ou "caindo". Com n < 2, "estável". Os limiares ficam numa constante do módulo.

#### R4 — Tools de leitura (`services/chat_tools.py`)
Classe `ChatTools(registry, readings, fleet, alerts, limits, agora=<função>)`. `agora` é injetável para os testes. Todas as tools são `async` e devolvem `dict` serializável em JSON.
- **R4.1** Resolução: toda tool com o parâmetro `vinheria` chama `resolve_vinheria(vinheria, registry.list())`.
  - Ambígua: devolve `{ "erro": <mensagem>, "opcoes": [{device_id, name, city}] }`.
  - Não encontrada: devolve `{ "erro": <mensagem> }`.
  - Nenhuma das duas lança exceção.
- **R4.2** `FiwareError` dentro de uma tool vira `{ "erro": "FIWARE indisponível: <mensagem>" }`.
- **R4.3** `listar_vinherias()` → `{ fiware_online, vinherias: [{ device_id, name, city, status, offline_reason }] }`, a partir de `fleet.report(ids cadastrados)`.
- **R4.4** `estado_atual(vinheria)` → `{ device_id, name, city, status, offline_reason, visto_ha_segundos, temperatura, umidade, luminosidade, score, alertas_ativos }`, a partir de `fleet.get`. Sem retrato no `FleetState` (poller ainda não rodou): `{ "erro": "ainda sem leitura do poller, tente em alguns segundos" }`.
- **R4.5** `estatisticas(vinheria, atributo, horas=1)`:
  - `horas` vai de 0,25 a 24 (fora disso, recorta para o limite);
  - pede `readings.history` com `last_n=500`, aplica R3.1 e R3.2 e devolve `{ device_id, name, atributo, horas_pedidas, ...estatisticas }`.
- **R4.6** `comparar(atributo, horas=1)` → `{ atributo, unidade, vinherias: [{ device_id, name, city, media, n }] }`, ordenado da maior média para a menor. Vinheria com n = 0 vai por último, com `media: null`. A falha de uma vinheria não derruba as outras: ela entra com `erro`.
- **R4.7** `alertas(vinheria=None, horas=24)` → `{ alertas: [{ device_id, attr, value, inicio, fim, duracao_segundos, aberto }] }`. Usa `AlertLog.list(device_id, limit=200)` filtrado por `opened_at >= agora - horas`, do mais novo ao mais velho. Sem `vinheria`, inclui os de todas as vinherias e o `device_id="fiware"`.
- **R4.8** `limites(vinheria)` → `{ device_id, name, temperatura: {min, max, unidade}, umidade: {...}, luminosidade: {...} }`.
- **R4.9** `executar(nome, args, propostas: list[ChatAction]) -> dict` despacha pelo nome. Nome desconhecido ou argumento inválido devolve `{ "erro": ... }`. A lista `propostas` é criada pelo `Chatbot` a cada `ask` e só as tools do bloco B escrevem nela.

#### R5 — Declarações (`services/chat_declarations.py`)
- **R5.1** Uma `FunctionDeclaration` por tool, com descrição em português e parâmetros tipados. `atributo` é enum `temperature|humidity|luminosity`; `comando` (bloco B) é enum `blink_temp|blink_hum|blink_lux|alert_off`.
- **R5.2** `declaracoes(com_acoes: bool)` devolve a lista. As declarações do bloco B só entram com `com_acoes=True`.

#### R6 — Chatbot (`services/chatbot.py`)
Classe `Chatbot(tools, registry, fleet, settings, client=None)`. `client` é injetável: nos testes, um Gemini falso; em produção, `genai.Client(api_key=...)` criado na primeira chamada.
- **R6.1** Chave vazia: `ask` lança `ChatbotUnavailable("chatbot não configurado: defina GEMINI_API_KEY no backend/.env")`.
- **R6.2** `resumo_frota(report) -> str` (função pura) devolve uma linha em português, por exemplo:
  - "Situação agora: FIWARE ok; 3 vinherias; vinheria002 (Vinheria Mineira) em alerta de temperatura; vinheria003 (Vinheria Sul) offline."
  - Sem problema: "Situação agora: FIWARE ok; 3 vinherias, todas normais."
  - EC2 fora: "FIWARE fora do ar desde <hora>".
- **R6.3** System instruction (constante do módulo):
  - responder em português;
  - usar só dados das tools e nunca inventar número;
  - citar números com unidade e o período;
  - dizer quando `janela_completa` é falso;
  - recomendar ação de vinheria em caso de anomalia (temperatura, umidade ou luz fora da faixa);
  - avisar no início da resposta de vinheria em alerta ou offline citada no resumo, mesmo sem ter sido perguntado;
  - texto simples, sem markdown (listas com hífen);
  - no bloco B: só propor ação quando o usuário pedir, e explicar que ela aguarda confirmação no cartão.
- **R6.4** `ask(message, history) -> ChatReply`:
  - monta `contents` com o histórico (`role` user/model, só texto) e a mensagem atual com o resumo da frota antes dela;
  - chama `client.aio.models.generate_content(model, contents, config com system_instruction e tools)`;
  - enquanto a resposta trouxer function calls, executa cada uma por `tools.executar`, anexa a chamada e o resultado a `contents` e chama de novo;
  - para no máximo após 5 chamadas ao modelo. Se a 5.ª ainda pedir tool: `reply = "Não consegui concluir a consulta. Tente reformular a pergunta."`.
- **R6.5** Erro 429 do Gemini lança `ChatbotRateLimited("limite de uso do Gemini atingido, aguarde alguns segundos")`. Outro erro do SDK lança `ChatbotUpstreamError("falha ao consultar o Gemini: <mensagem curta>")`. As três exceções herdam de `ChatbotError(message)`, em `services/chat_errors.py`.
- **R6.6** Resposta final vazia vira "Não encontrei uma resposta. Tente reformular a pergunta."

#### R7 — Rota (`api/routes_chat.py`)
- **R7.1** `POST /api/chat`: corpo `ChatRequest`, resposta `ChatReply`. A rota só chama `Chatbot.ask` via `get_chatbot` em `deps.py`.
- **R7.2** `errors.py` traduz os erros do chatbot para `{ detail, service: "gemini" }`:
  - `ChatbotUnavailable` → 503;
  - `ChatbotRateLimited` → 429;
  - `ChatbotUpstreamError` → 502.
- **R7.3** `main.py` cria `ChatTools` e `Chatbot` em `app.state.chatbot` e inclui o router.

#### R8 — Front: lógica e cliente
- **R8.1** `api.sendChat(message, history)` → `POST /api/chat`.
- **R8.2** `lib/chat.js`:
  - `montarHistorico(mensagens)` → `[{role, text}]` com só as mensagens `user`/`model` (sem as de erro), as 20 últimas;
  - `novaMensagem(role, text, extras)` gera um `id` único;
  - `ACAO_ESTADOS` e `podeDecidir(estado)` (verdadeiro só em `pendente` e `erro`).
- **R8.3** `context/ChatContext.jsx` (via `criarContexto('Chat')`) expõe:
  - `mensagens` e `enviando`;
  - `enviar(texto)`: acrescenta a mensagem do usuário, chama a API e acrescenta a resposta (com `actions` em estado `pendente`) ou uma mensagem `erro` com o texto do `ApiError`. Em erro, devolve `{ ok: false, texto }` para o campo recuperar o texto;
  - `atualizarAcao(mensagemId, indice, estado, detalhe)`.

#### R9 — Front: telas
- **R9.1** `ChatBox`:
  - lista de `ChatMensagem` com rolagem automática para a última;
  - `EstadoVazio` com as chips quando não há mensagens;
  - chips sempre acessíveis acima do campo: "Como está a vinheria de São Paulo?", "Alguma vinheria em alerta?", "Qual vinheria está mais úmida agora?";
  - campo de texto: Enter envia, Shift+Enter quebra a linha, desabilitado enquanto `enviando`;
  - indicador "pensando…" enquanto `enviando`.
- **R9.2** `ChatMensagem`:
  - bolha do usuário à direita e do bot à esquerda;
  - mensagem `erro` com `MensagemErro`;
  - texto com `whitespace-pre-wrap`;
  - cartões de ação abaixo (bloco B).
- **R9.3** `pages/Chat.jsx`: `Titulo` + `ChatBox` ocupando a altura útil. `App.jsx` troca o `Placeholder` de `/chat` por ela e envolve tudo em `ChatProvider`.
- **R9.4** `ChatFlutuante`:
  - botão redondo bordô fixo no canto inferior **esquerdo** (o direito já é dos toasts do `AlertBanner`); abaixo de 768 px fica acima da `NavInferior` e abaixo dos toasts na ordem de empilhamento;
  - abre um painel de ~400 px no mesmo canto (desktop) ou tela cheia (celular) com o mesmo `ChatBox`;
  - fecha com Esc e com ×;
  - não aparece na rota `/chat`;
  - a conversa é a mesma da página (o contexto vive acima das rotas).
- **R9.5** Só o kit da 5B e os tokens existentes: sem hex, sem `style=` e sem `fetch` fora do `client.js`.

#### R10 — Sonda do SDK (antes de qualquer código do chatbot)
- **R10.1** Script descartável em `scratchpad`, nunca commitado, com uma chave real. Confirma:
  - (a) a versão do `google-genai` instalada;
  - (b) `client.aio.models.generate_content` com `types.Tool(function_declarations=[...])` devolve a function call em `response.function_calls` (nome e `args`);
  - (c) como devolver o resultado (`types.Part.from_function_response`);
  - (d) a classe e o atributo de status do erro 429 (esperado: `google.genai.errors.APIError` com `code == 429`).
  Qualquer divergência para e volta ao planejamento antes da R6.

### Bloco B — ações com confirmação

#### R11 — Tools de proposta (`services/chat_acoes.py`)
Classe `ChatAcoes(registry, fleet, limits)`, registrada no `ChatTools` com `registrar_em(tools)`. Fica num arquivo próprio para o `chat_tools.py` não passar de ~250 linhas (R14.2). Nenhuma das duas tools chama o FIWARE nem escreve no SQLite.
- **R11.1** `propor_comando(vinheria, comando)`:
  - comando fora do enum devolve `erro`;
  - status `offline` ou `configurando` devolve `erro` com o motivo;
  - senão, registra uma `ChatAction(kind="command", ..., summary="Piscar a luz (blink_lux) na Vinheria Mineira")` e devolve `{ "proposta": summary, "aguardando_confirmacao": true }`.
- **R11.2** `propor_faixa(vinheria, atributo, minimo=None, maximo=None)` (os nomes evitam sombrear `min`/`max` do Python):
  - pelo menos um de `minimo`/`maximo` é obrigatório;
  - junta com `limits.get` e valida com `AttrLimits` (min ≥ max devolve `erro`);
  - registra `ChatAction(kind="limits", limits=<Limits completo>, summary="Temperatura máx. 18 → 20 °C na Vinheria Paulista")`.
  Faixa de vinheria offline é aceita: o backend deixa pendente, como no painel.
- **R11.3** As propostas vão para a lista `propostas` da R4.9 (sem estado entre requisições) e voltam em `ChatReply.actions`.

#### R12 — Chatbot com ações
- **R12.1** `Chatbot` passa `declaracoes(com_acoes=True)`, e a system instruction ganha as regras de proposta (R6.3).

#### R13 — Front: cartão de ação
- **R13.1** `CartaoAcao`:
  - mostra o `summary` e a vinheria;
  - em `pendente`: Confirmar (primário) e Cancelar (secundário);
  - Confirmar chama `api.sendCommand(device_id, command)` ou `api.saveTriggers(device_id, limits)` via `useAcao`;
  - estados:
    - `executando`: botão carregando;
    - `feito`: "Comando enviado." ou, conforme `device_sync`, "Faixa salva e enviada ao ESP32." / "Faixa salva; o ESP32 recebe quando voltar.";
    - `cancelado`: "Cancelado.";
    - `erro`: `MensagemErro` com o texto do backend e Confirmar de novo.
  - `feito` e `cancelado` não mostram botões.
- **R13.2** Chip extra: "Desligue o alerta da vinheria 001".

### R14 — Qualidade (vale para os dois blocos)
- **R14.1** Comentários em português em todo módulo e em toda função não óbvia.
- **R14.2** Nenhum arquivo novo passa de ~250 linhas.
- **R14.3** `pytest` e `npm test` verdes, `npm run build` ok, nenhum teste com rede ou chave real.
- **R14.4** A rota não importa `google.genai`. Só `chatbot.py` importa o SDK, e `chat_declarations.py` importa apenas `google.genai.types`.

## 4. Decisões (com o porquê)

| Decisão | Porquê |
|---|---|
| Loop manual de function calling, não o automático do SDK | Controla o limite de 5 voltas, coleta as propostas para `actions` e testa sem rede com um Gemini falso. |
| Ações só como proposta + clique | O LLM não tem caminho para executar nada, então não há ação alucinada nem troca de vinheria entre turnos. A execução reaproveita as rotas e validações que já existem. O backend continua sem estado. |
| Backend sem estado; histórico só no navegador, como texto | Simples e suficiente para a demo. Os dados das tools não voltam no histórico, e o bot consulta de novo, com números frescos. |
| `last_n=500` + filtro em Python | A consulta por datas do STH devolve os 500 pontos mais antigos da janela (achado da exploração). |
| `statistics` da biblioteca padrão, não pandas | Média, desvio e inclinação de até 500 pontos. O pandas só entra na 7B. |
| Fuso local da máquina (`astimezone()`) | O backend roda no notebook da apresentação, e `zoneinfo` no Windows exigiria o pacote `tzdata`. |
| Texto sem markdown | Dispensa biblioteca de markdown no front. |
| Erros das tools voltam ao Gemini como dados | O bot pergunta "qual das duas?" sozinho, em vez de a requisição falhar. |
| Conversa some ao recarregar | YAGNI. Página e painel flutuante compartilham o `ChatContext`, o que basta para a demo. |
| Chave só no `backend/.env` | O repositório é público na entrega. O `.env` já é ignorado pelo Git. |

## 5. Ferramentas e requisitos

- Python 3.11+ (a máquina do usuário roda 3.14), `google-genai` (versão fixada na sonda; a mais recente no PyPI em 20/10/2026 é 2.32.0).
- **[VOCÊ]** `GEMINI_API_KEY` no `backend/.env`. Necessária só na sonda (R10) e na verificação real. Testes não usam.
- EC2 ligada com a stack FIWARE e ao menos 2 Wokwi (`vinheria001`, `vinheria002`) para a verificação manual.
- Front: nenhuma dependência nova.

## 6. Fora do escopo

- Streaming da resposta, persistência da conversa e conversa por usuário.
- Ações além de `blink_*`, `alert_off` e faixa (cadastro e remoção de vinheria, configuração da EC2).
- Markdown na resposta e voz.
- Relatórios (Task 7B).

## 7. Como verificar

1. `cd backend && pytest tests -v`: tudo verde, incluindo `test_chat_stats.py`, `test_chat_tools.py`, `test_chatbot.py` e `test_routes_chat.py`.
2. `cd frontend && npm test && npm run build`: verde e build ok.
3. Sem chave no `.env`, `POST /api/chat` pelo Swagger devolve 503 `"chatbot não configurado..."`, e o resto do painel funciona.
4. *(manual, com chave, EC2 e 2 Wokwi)*:
   1. As três chips respondem, e média, mínimo e máximo de "Como está a vinheria de São Paulo?" batem com o gráfico do detalhe (janela "Por período", última hora).
   2. Pare um Wokwi. Depois de ~35 s, "Qual vinheria está mais úmida agora?" começa avisando da vinheria offline.
   3. "Alguma vinheria em alerta?" com o DHT de um Wokwi esquentado cita só aquela vinheria.
   4. *(bloco B)* "Pisque a luz da vinheria 002" mostra o cartão; Confirmar faz só o ESP32 da 002 reagir; Cancelar em outra proposta não envia nada.
   5. *(bloco B)* "Aumente o máximo de temperatura de São Paulo para 20" mostra o cartão "18 → 20 °C"; Confirmar faz a faixa nova aparecer no detalhe e no LCD.
   6. Uma conversa iniciada no painel flutuante do detalhe continua igual em `/chat` e de volta no detalhe.
5. `git grep -n "AIza"` não acha nada (nenhuma chave do Google commitada).
