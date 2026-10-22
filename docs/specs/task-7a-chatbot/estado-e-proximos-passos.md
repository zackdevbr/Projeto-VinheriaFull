# Task 7A (chatbot Gemini) — estado em 22/10/2026 e próximos passos

Este arquivo guarda onde a Task 7A parou, o que o uso real ensinou sobre o Gemini e a pesquisa de provedores de reserva. Serve para retomar o trabalho numa sessão nova sem depender da conversa anterior. A entrega do CP5 é em **26/10/2026**.

## 1. Onde paramos

A Task 7A está **implementada** (blocos A e B) e commitada, mas o **ensaio manual com a EC2 e os Wokwi ainda não foi feito**. Depois do primeiro uso real, a chave gratuita do Gemini estourou a cota, e o resto da sessão foi gasto em reduzir requisições e tokens. A decisão em aberto é se vale colocar um segundo provedor de IA como reserva (seção 5).

No fim da sessão, o backend (porta 8000) e o front (porta 5173) estavam **parados**: o Claude Code os encerrou por falta de memória do sistema. Nada foi perdido, e o `git status` estava limpo.

## 2. O que está pronto

- **Commits da 7A:** `8b8eaf4` a `fb1111a` (19 commits sobre chatbot e Gemini). Os últimos relevantes:
  - `fb1111a`: menos tokens e requisições, e modelo padrão `gemini-3.5-flash-lite`;
  - `affdee3`: timeout de 30 s e sem retry interno do SDK;
  - `e57764f`: a mensagem de 429 informa a espera real;
  - `d03f83a`: registro da implementação no `PLANO-CP5-VINHERIA.md`.
- **Testes:** backend com 369 passando e front com 120, build do front ok.
- **Funcionalidades:**
  - `POST /api/chat` com function calling (6 tools de leitura, 2 tools que só propõem ação);
  - página `/chat` e painel flutuante no canto inferior esquerdo, com a conversa compartilhada;
  - cartão Confirmar/Cancelar para ações (alerta manual e faixa ideal).
- **Verificado:** com o Gemini real (listar, estado, propostas de faixa e de comando) e no navegador contra um backend falso. O registro completo, com desvios e menores adiados, está na nota "Task 7A IMPLEMENTADA" do `PLANO-CP5-VINHERIA.md`.
- Spec e plano: [`spec.md`](spec.md) e [`plan.md`](plan.md) desta pasta.

## 3. Pendências, na ordem sugerida

1. **Ensaio manual da 7A** (spec §7, item 4). Precisa da EC2 ligada e de 2 Wokwi:
   1. As três sugestões respondem, e média, mínimo e máximo de "Como está a vinheria de São Paulo?" batem com o gráfico do detalhe (janela "Por período", última hora).
   2. Pare um Wokwi e espere cerca de 35 s. "Qual vinheria está mais úmida agora?" deve começar avisando da vinheria offline.
   3. Esquente o DHT de um Wokwi. "Alguma vinheria em alerta?" deve citar só ela.
   4. "Pisque a luz da vinheria 002" gera o cartão. Confirmar faz só o ESP32 da 002 reagir.
   5. "Aumente o máximo de temperatura de São Paulo para 20" gera o cartão. Confirmar faz a faixa nova aparecer no detalhe e no display.
   Cada pergunta de teste consome cota (seção 4).
2. **Decidir o provedor de reserva** (seção 5). É mudança de stack: precisa de decisão do usuário e de plano no Opus (CLAUDE.md §2 e §5).
3. **Task 7B:** relatórios CSV e PDF (primeiro corte se o prazo apertar).
4. **Task 8:** manuais, coleção do Postman e README final. Fecha a entrega.

## 4. O que aprendemos sobre o Gemini

- **A chave do usuário está no plano gratuito da API.** A assinatura do app Gemini não vale para a API. O limite é de **20 requisições por dia por modelo** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), e o 429 da primeira pergunta veio daí, em parte pela cota gasta nos testes. Só a cobrança ativada no projeto da chave (AI Studio ou Google Cloud) tira esse limite.
- **A cota é por modelo.** Se um modelo esgotar, trocar o `GEMINI_MODEL` no `backend/.env` por outro lite dá outra cota. Candidatos que responderam em 21/10/2026: `gemini-3.5-flash-lite` (o atual, 5,8 s numa pergunta com ferramenta), `gemini-3.1-flash-lite` e `gemini-3.7-flash`. Depois de trocar, é preciso reiniciar o backend.
- **O `gemini-2.5-flash` original dá 404** para esta chave ("no longer available to new users"). Por isso o padrão mudou.
- **503 e 504 intermitentes** do Google nos modelos 3.x: o código tenta de novo até 2 vezes (1 s e 2 s) e depois devolve 502 com mensagem clara. Não há como resolver isso só com código.
- **Consumo medido** (2 perguntas reais): 1 requisição por pergunta de estado atual, cerca de 1 s, cerca de 1,4 mil tokens de entrada e de 50 a 60 de saída. Isso vale porque cada pergunta já leva as leituras atuais da frota no contexto. Perguntas de histórico (médias, tendência) e ações gastam 2 requisições.
- **Economias aplicadas:** pensamento mínimo (`thinking_level=MINIMAL`), teto de 500 tokens de saída, instrução e declarações das tools curtas, histórico enviado pelo painel de 6 turnos.
- **A chave fica só no `backend/.env`** (ignorado pelo Git), nunca em arquivo versionado. O arquivo `backend/.env.example` traz as chaves vazias.

## 5. Provedor de reserva: pesquisa e proposta

**Pergunta do usuário:** colocar uma API do Claude (e/ou do GPT, ou alguma gratuita) de reserva quando a do Gemini esgotar.

### Como ficaria o código

O `Chatbot` hoje conversa direto com o SDK do Google. A proposta é separar o provedor atrás de uma interface (`GeminiProvider`, `ClaudeProvider` e um provedor genérico no formato OpenAI), com as ferramentas descritas num formato neutro e convertidas para cada API. Se o Gemini devolver 429, 503, 504 ou estourar o tempo, o backend tenta o próximo provedor na mesma pergunta. A lógica do resumo da frota, do histórico e das ações com Confirmar fica igual. O `.env` ganharia as chaves e modelos de cada provedor. Estimativa: cerca de 1 dia, com testes e provedores falsos.

**Ideia que reduz o custo:** Groq, OpenRouter, Mistral, Cerebras e a própria OpenAI usam a API no formato "OpenAI-compatible". Um único adaptador (SDK `openai` com `base_url`, chave e modelo no `.env`) conecta qualquer um deles, e trocar de provedor vira trocar o `.env`.

### Opções (pesquisa de 22/10/2026)

As fontes são blogs de terceiros e divergem entre si. **Confirme nos sites oficiais antes de depender.** Nenhuma fonte confirmou function calling por provedor, então cada um precisa de uma sonda.

| Provedor | O que as fontes dizem |
|---|---|
| **Claude (Anthropic)** | A API **não é gratuita** e não usa a assinatura do app. Precisa de chave do console da Anthropic com crédito carregado. O modelo mais barato é o `claude-haiku-5-5`, que aceita ferramentas. Com cerca de 1,4 mil tokens por pergunta, deve custar centavos. |
| **OpenAI (GPT)** | Sem página oficial nos resultados. Uma fonte diz que contas novas ainda ganham US$ 5 em créditos; outra diz que o nível gratuito foi praticamente encerrado e exige cartão. Limites citados de 3 a 20 requisições por minuto e de 200 a 500 por dia. Tratar como pago. |
| **Groq** | Plano gratuito com modelos grandes (por exemplo GPT-OSS-120B). O limite é por modelo, e o teto real costuma ser tokens por minuto. |
| **OpenRouter** | Cerca de 50 requisições por dia e 20 por minuto na conta gratuita (uma fonte avisa que o limite mudou). Tem o `openrouter/free`, que escolhe um modelo gratuito que aceite ferramentas. |
| **Cerebras** | Catálogo gratuito instável: um blog diz que caiu de uma dúzia de modelos para dois sem aviso. |
| **Mistral** | Acesso gratuito com limites por conta e ressalvas por modelo. |
| **Gemini** | Segue gratuito só para Flash e Flash-Lite (os modelos Pro saíram do nível gratuito em abril de 2026, segundo uma fonte). |

### Riscos

- Modelos abertos gratuitos erram mais em function calling e em português que o Gemini e o Claude, então precisam de sonda antes de confiar.
- Limites e catálogos gratuitos mudam sem aviso, o que é ruim para uma demo.
- O tempo: faltam 4 dias para a entrega, e a Task 7B e a Task 8 ainda estão pendentes. O fallback custa cerca de 1 dia.

### Recomendação (ainda não decidida pelo usuário)

- Se aceitar pôr crédito pequeno numa chave Anthropic: Claude Haiku como reserva é a opção mais robusta para a demo.
- Se quiser gratuito: Groq ou OpenRouter via o adaptador OpenAI-compatible, com o Gemini lite como principal.
- Alternativa sem código novo: ativar a cobrança do Gemini no AI Studio (resolve a cota diária, não o 503).
- Alternativa pequena, só Gemini: lista de modelos reserva (`GEMINI_FALLBACK_MODELS`, cerca de 40 linhas). Multiplica a cota, mas não cobre uma queda geral do Gemini.

### Para decidir e começar

1. O usuário decide o provedor e se tem chave com crédito (Anthropic) ou cria uma chave gratuita (Groq em console.groq.com ou OpenRouter) e coloca no `backend/.env`.
2. O plano passa pelo Opus, porque troca a stack fixada no CLAUDE.md §5.
3. Antes de codar, uma sonda curta no provedor escolhido confirma se a ferramenta funciona e quanto custa em requisições (como foi feito com o Gemini).
4. Decidir se o fallback entra antes ou depois da Task 7B.

### Fontes da pesquisa

- [Free LLM APIs Compared: Rate Limits, Models, and Real Costs (2026), OpenRouter](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)
- [OpenAI rate limits guide, Inference](https://inference.net/content/openai-rate-limits-guide/)
- [5 Free LLM API Providers You Can Use in 2026, KDnuggets](https://kdnuggets.com/5-free-llm-api-providers-you-can-use-in-2026)
- [Free LLM API Comparison 2026, Novita](https://blogs.novita.ai/free-llm-api-comparison-2026/)
- [Free LLM APIs in 2026, tkmxai](https://tkmxai.it.com/free-llm-apis-in-2026-3)

## 6. Como subir o ambiente

Cada comando roda na pasta indicada, em PowerShell. O projeto usa o venv do backend, que é Python 3.12, e não o Python 3.14 do terminal. Sem o venv, o `pytest` nem está no PATH.

```powershell
# backend (porta 8000, Swagger em /docs)
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# front (porta 5173)
cd frontend
npm run dev

# testes
cd backend;  .venv\Scripts\python.exe -m pytest tests -q
cd frontend; npm test
```

O backend sobe o poller contra o IP elástico da EC2 que está no `backend/.env` (`FIWARE_HOST`). Com a EC2 desligada, o painel mostra "FIWARE desligado".

Cuidados:
- **Memória:** o sistema ficou com pouca memória e o Claude Code encerrou os servidores em segundo plano. Se acontecer de novo, feche programas pesados (o Edge, por exemplo).
- **Reiniciar o backend** é necessário depois de trocar o `GEMINI_MODEL` ou qualquer valor do `.env`, porque o `--reload` só observa arquivos `.py`.
- **Cuidado ao encerrar processos por porta:** durante as verificações visuais, um comando de limpeza que encerrava "tudo na porta 5173" derrubou o servidor do front que estava rodando para o usuário. Encerre só o processo que você mesmo iniciou.
- As verificações visuais foram feitas com o Edge headless por protocolo de depuração (CDP), com scripts descartáveis fora do repositório.
