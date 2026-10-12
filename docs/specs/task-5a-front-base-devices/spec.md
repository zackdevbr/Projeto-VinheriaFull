# Spec — Task 5A: Front-end React — base, configuração do FIWARE, aviso global e cadastro de vinherias

> Método spec-driven: esta spec diz **o que** a Task 5A entrega e **como saber que está certo**. O passo a passo fica em [`plan.md`](plan.md), que segue esta spec item por item. Se as duas divergirem, a spec manda e o executor para e devolve para planejamento.
>
> Fonte: Task 5 de [`PLANO-CP5-VINHERIA.md`](../../../PLANO-CP5-VINHERIA.md), PRD (RF01, RF02, RF12 parcial, RF14) e as decisões tomadas com o usuário em 10/10/2026. Formato do `CLAUDE.md` §3: Contexto → Objetivo → Detalhes técnicos → Ferramentas e requisitos → Passos (no plano) → Como verificar.

---

## 1. Contexto

**Por que existe.** O backend das Tasks 2 a 4 já cadastra, vigia e alerta, mas só dá para usá-lo pelo Swagger. Esta task cria o painel web: a casca da aplicação (rotas e navegação), o indicador de saúde do FIWARE com a troca do IP em runtime, o aviso global de alerta e offline, e a tela de cadastro e remoção de vinherias.

**Divisão 5A / 5B (decisão do usuário em 10/10/2026).** O gate de design (`CLAUDE.md` §5) proíbe decisões visuais antes de o usuário enviar referências. Por isso a Task 5 foi dividida:
- **5A (esta spec):** estrutura e comportamento, com CSS mínimo e neutro, marcado como provisório.
- **5B (depois das referências):** design system (cores, fontes, componentes) e o visual das telas da 5A, planejado em Opus.

**O que já está pronto.**
- Backend (281 testes): `GET|PUT /api/config`, `GET /api/config/health`, `GET|POST /api/devices`, `GET|DELETE /api/devices/{id}`, `GET /api/fleet`. Erros saem como `{ "detail": "...", "service": "..." }` (handler central) ou, na validação do Pydantic, como `{ "detail": [ { "loc": [...], "msg": "..." } ] }` com status 422.
- CORS do backend liberado para `http://localhost:5173` (não será usado: ver D3).
- `.gitignore` já ignora `node_modules/`, `dist/` e `.env` em qualquer pasta.
- Máquina: Node 24.19, npm 11.17.

**Fatos verificados no código em 10/10/2026.**
- F1: `GET /api/fleet` devolve `{ fiware_online, fiware_offline_since, updated_at, vinherias: [VinheriaStatus] }`; `status` ∈ `ok | alerta | offline | configurando`; `offline_reason` ∈ `sem_leitura | fiware | null`. Vinheria recém-cadastrada só aparece no ciclo seguinte do poller (até `poll_seconds`).
- F2: com a EC2 fora, **todas** as vinherias ficam `offline` com motivo `fiware` e `fiware_online: false`.
- F3: `GET /api/config/health` responde 200 com `{ ok, ec2_ip, orion, iota, sth }` mesmo com o FIWARE fora; cada serviço pode levar até `HTTP_TIMEOUT_SECONDS` (5 s).
- F4: `POST /api/devices` provisiona no FIWARE (várias chamadas HTTP); leva alguns segundos. Cadastro repetido no SQLite dá 409; FIWARE fora dá 503.
- F5: `DELETE /api/devices/{id}` devolve 204 sem corpo.

**O que depende desta task.**
- Task 5B: aplica o design sobre os componentes desta task.
- Task 6: usa `client.js`, `FleetContext`, `usePolling` e as rotas reservadas (`/`, `/vinherias/:id`, `/alertas`).
- Task 7A: usa a rota `/chat`.

## 2. Objetivo

Com o backend e a EC2 ligados, `npm run dev` abre `http://localhost:5173` com o título "Smart Solutions — Monitoramento de Vinherias", uma barra fixa mostrando "FIWARE online" e o IP em uso, e a navegação entre as cinco rotas. Na rota `/dispositivos`, o usuário cadastra e remove uma vinheria e vê o status de cada uma. Trocar o IP para um endereço inexistente no painel "Avançado" deixa o indicador em "FIWARE fora do ar"; parar um Wokwi faz aparecer, em até ~40 s, uma faixa fixa e um toast de offline com link para a vinheria. `npm test` passa inteiro sem rede.

## 3. Requisitos e critérios de aceite

Formato: **QUANDO** <situação>, o sistema **DEVE** <comportamento>. Testes automáticos estão no `plan.md`; os itens marcados *(manual)* são conferidos no navegador.

### R1 — Projeto e build
- **R1.1** `frontend/` DEVE ser um projeto Vite + React em JavaScript puro (`.jsx`/`.js`), sem TypeScript, com os scripts `dev`, `build`, `preview` e `test`.
- **R1.2** `npm run dev` DEVE servir na porta 5173 (fixa) e encaminhar `/api/*` para o backend (proxy). O destino do proxy DEVE vir da variável `BACKEND_URL` (arquivo `frontend/.env`), com padrão `http://localhost:8000`. `npm run preview` DEVE usar o mesmo proxy.
- **R1.3** `npm run build` DEVE terminar sem erros nem avisos de import.
- **R1.4** O `<title>` DEVE ser "Smart Solutions — Monitoramento de Vinherias".
- **R1.5** O estilo DEVE usar Tailwind CSS v4, instalado já na 5A.1 pelo plugin `@tailwindcss/vite` (sem `tailwind.config.js` nem PostCSS). O único `.css` é `src/styles.css`, com `@import "tailwindcss"`; os componentes usam só classes utilitárias.

### R2 — Cliente HTTP (`src/api/client.js`)
- **R2.1** Toda chamada ao backend DEVE passar por `request(path, { method, body })`. Nenhum componente ou context chama `fetch` direto.
- **R2.2** `request` DEVE mandar o corpo em JSON com `Content-Type: application/json` quando houver corpo, devolver o JSON da resposta e devolver `null` em 204.
  Testes: `GET devolve o JSON da resposta`, `POST envia o corpo em JSON com o cabeçalho certo`, `204 devolve null`.
- **R2.3** QUANDO a resposta não é 2xx, `request` DEVE lançar `ApiError` com `status`, `message` e `service`: `detail` em texto vira a mensagem; `detail` em lista (422) vira `campo: msg` unidos por `; `; sem corpo JSON, `Erro HTTP <status>` (4xx) ou uma mensagem dizendo que o backend não respondeu (5xx, caso do proxy sem backend).
  Testes: os quatro de `errorFromResponse` e `status de erro vira ApiError com o detail`.
- **R2.4** QUANDO o `fetch` falha (rede), `request` DEVE lançar `ApiError` com `status` 0.
  Teste: `falha de rede vira ApiError com status 0`.
- **R2.5** `client.js` DEVE expor `api.getConfig`, `api.saveConfig`, `api.getHealth`, `api.getFleet`, `api.listDevices`, `api.createDevice`, `api.deleteDevice`.

### R3 — Configuração e saúde (`ConfigContext`, `FiwareBar`)
- **R3.1** `ConfigContext` DEVE carregar `GET /api/config` e `GET /api/config/health` ao montar e repetir a cada 30 s, expondo `config`, `health`, `healthState` (`verificando | online | offline | sem_backend`) e `salvarIp(ip)`.
- **R3.2** `salvarIp` DEVE chamar `PUT /api/config` com `{ ec2_ip }` e revalidar a saúde na hora, sem esperar os 30 s. Erros de validação DEVEM aparecer no formulário. *(manual)*
- **R3.3** `FiwareBar` DEVE ficar no topo de todas as telas com o nome **Smart Solutions**, o indicador de saúde com o rótulo do estado e o IP em uso, e um painel "Avançado" recolhido por padrão com o campo do IP, o botão Salvar e o detalhe por serviço (Orion, IoT Agent, STH-Comet). *(manual)*
- **R3.4** QUANDO o backend não responde, o indicador DEVE mostrar "Backend indisponível" e voltar sozinho quando o backend voltar, sem recarregar a página. *(manual)*

### R4 — Eventos da frota (`src/lib/fleetEvents.js`, funções puras)
- **R4.1** `diffFleet(anterior, atual)` DEVE devolver `[]` na primeira leitura (`anterior` nulo).
- **R4.2** Por vinheria presente nos dois retratos e com status diferente:
  - entrou em `alerta` → evento `alerta`;
  - entrou em `offline` com motivo `sem_leitura` → evento `offline`;
  - saiu de `offline` (motivo `sem_leitura`) para `ok` ou `configurando` → evento `normal`;
  - saiu de `alerta` para `ok` → evento `normal`;
  - qualquer outra transição (ex.: `configurando → ok`) → nada.
- **R4.3** QUANDO a EC2 cai (`fiware_online` de `true` para `false`), DEVE sair **um único** evento `fiware_offline`, sem eventos por vinheria (motivo `fiware`). QUANDO volta, um único `fiware_online`, sem eventos `normal` das vinherias que estavam offline por causa dela.
- **R4.4** Vinheria que aparece ou some entre dois retratos (cadastro ou remoção) NÃO DEVE gerar evento.
- **R4.5** Cada evento DEVE ter `id` = `<tipo>:<device_id ou "fiware">:<updated_at>`, mais `tipo`, `device_id`, `name`, `city` e `at`.
- **R4.6** `textoDoEvento(evento)` DEVE gerar a frase em português de cada tipo; `empilharToasts(atuais, novos, limite=5)` DEVE pôr os novos primeiro, não repetir `id` e cortar no limite; `bannerSummary(frota)` DEVE devolver `null` sem frota, ou `{ fiwareOffline, emAlerta, offline, visivel }`, com `offline` excluindo o motivo `fiware`.
  Testes: os 17 de `fleetEvents.test.js`.

### R5 — Polling da frota e aviso global (`FleetContext`, `AlertBanner`)
- **R5.1** `FleetContext` DEVE buscar `GET /api/fleet` a cada 5 s, sem sobrepor requisições (a próxima só começa 5 s depois que a anterior terminou), guardar o retrato anterior, gerar eventos com `diffFleet` e expor `fleet`, `error`, `toasts`, `fecharToast(id)` e `atualizar()`.
- **R5.2** `AlertBanner` DEVE mostrar uma faixa fixa enquanto `bannerSummary(fleet).visivel`, listando as vinherias em alerta e offline com link para `/vinherias/:id`, ou a mensagem da EC2 fora do ar. *(manual)*
- **R5.3** Cada evento DEVE virar um toast empilhado (no máximo 5, o mais novo em cima), com a frase do evento, link "Ver detalhe" quando houver vinheria e botão de fechar. Toasts não somem sozinhos. *(manual)*

### R6 — Cadastro de vinherias (`/dispositivos`)
- **R6.1** `validarCadastro(campos)` DEVE limpar espaços, passar o id para minúsculas e recusar id fora de `^vinheria\d{3}$`, nome ou cidade vazios e textos com mais de 60 caracteres, sem chamar o backend.
  Testes: os 4 de `validation.test.js`.
- **R6.2** `DeviceForm` DEVE enviar `POST /api/devices`, mostrar "Provisionando no FIWARE…" com o botão desabilitado enquanto espera, limpar os campos no sucesso e mostrar a mensagem do `ApiError` na falha (ex.: 409 de cadastro repetido). *(manual)*
- **R6.3** `DeviceList` DEVE mostrar id, nome, cidade e status (do `FleetContext`; "Aguardando 1º ciclo" enquanto a vinheria ainda não aparece na frota) e um botão Excluir que pede confirmação explicando o que é apagado e o que fica (STH), mostra "Removendo…" e tira a linha no sucesso. *(manual)*
- **R6.4** Depois de cadastrar ou remover, a página DEVE recarregar a lista e pedir uma atualização imediata da frota. *(manual)*

### R7 — Rotas e camadas
- **R7.1** Rotas: `/` (Visão geral), `/vinherias/:id` (Detalhe), `/alertas`, `/dispositivos`, `/chat`, e `*` (página não encontrada). Todas menos `/dispositivos` são um `Placeholder` que diz em qual task a tela chega.
- **R7.2** Navegação com `NavLink` marcando a rota ativa. *(manual)*
- **R7.5** Sem código redundante (pedido do usuário, 10/10/2026). As peças repetidas DEVEM existir uma vez só e ser reaproveitadas: `components/ui.jsx` (`Titulo`, `Campo`, `Botao`, `MensagemErro`, `Nota`, `LinkVinheria`), `hooks/useAcao.js` (ação assíncrona com executando/erro, nunca lança), `hooks/usePolling.js` e `context/criarContexto.js` (Provider + hook que falha fora dele). Componentes e páginas não têm `try/catch` próprio nem `<h1>`/`<input>`/`<button>` soltos (exceção: o × do toast). *(grep na 5A.9)*
- **R7.4** A troca de página DEVE ser sempre pelo `react-router-dom` (`BrowserRouter`, `Routes`, `NavLink`, `Link`, `useNavigate`), sem recarregar o documento; nenhum `<a href>` nem `window.location` para páginas do painel. Assim os toasts e o polling sobrevivem à navegação. Voltar e Avançar do navegador DEVEM funcionar. *(manual + grep na 5A.9)*
- **R7.3** Arquivos com no máximo ~250 linhas; comentários em português no topo de cada módulo e em cada função não óbvia.

## 4. Decisões

- **D1** Divisão 5A/5B (usuário, 10/10/2026). O visual desta task é provisório: utilitários Tailwind neutros (cinzas, bordas, espaçamento) e só as cores semânticas do indicador e dos status (verde, vermelho, âmbar, cinza). As classes repetidas e os mapas de cor ficam em `src/estilo.js`, para a 5B trocar num lugar só.
- **D11** Tailwind CSS v4 instalado já na 5A (pedido do usuário, 10/10/2026), em vez de esperar a 5B. A 5B só acrescenta o `@theme` (cores e fontes da marca) em `src/styles.css` e ajusta as classes; não há migração de CSS.
- **D12** Navegação só pelo `react-router-dom` (pedido do usuário, 10/10/2026): regra explícita e conferida por grep.
- **D13** Reaproveitamento (pedido do usuário, 10/10/2026): as peças da R7.5 nascem na 5A.5, antes das telas, e as classes Tailwind de título, campo, botão etc. moram nos componentes de `ui.jsx`, não em constantes soltas (`estilo.js` fica só com os mapas de cor por status). Assim a 5B troca o visual num lugar só. A tabela continua local em `DeviceList` até existir uma segunda tabela (Task 6), quando vira componente em `ui.jsx`. `useAcao` e `criarContexto` usam React e ficam sem teste automático (o Vitest roda sem DOM, D2); são cobertos pelas verificações no navegador.
- **D2** Vitest só para a lógica pura (`client.js`, `fleetEvents.js`, `validation.js`), ambiente `node`, sem DOM (usuário, 10/10/2026). Componentes são conferidos no navegador.
- **D3** O cliente usa caminhos relativos (`/api/...`) e o Vite faz proxy para o backend. Substitui a "base URL em `localStorage`" do plano original: o backend sempre roda no mesmo notebook, o proxy elimina CORS e não há nada para o usuário configurar. O IP do **FIWARE** continua trocável no painel Avançado (é ele que muda; o do backend não).
- **D4** Scaffold escrito à mão (`package.json`, `vite.config.js`, `index.html`, `src/main.jsx`) em vez de `npm create vite`, que é interativo e cria arquivos de exemplo que teriam de ser apagados.
- **D5** Polling por cadeia de `setTimeout` (hook `usePolling`), não `setInterval`: com a EC2 fora, o health leva até 5 s por chamada e as requisições não podem se acumular.
- **D6** Regras de evento da R4, incluindo `alerta → ok` como `normal` (o RF14 pede aviso de "volta ao normal", o plano original só citava `offline → ok`) e o evento único da EC2 (sem ele, a queda da EC2 geraria um toast por vinheria).
- **D7** Toasts no máximo 5, fechamento manual, sem sumir sozinhos: alerta não pode passar despercebido na demo.
- **D8** `chart.js` e `react-chartjs-2` ficam para a Task 6, que é quem os usa.
- **D9** O health de 30 s também recarrega o `config`: se o backend estava fora na abertura da página, o IP aparece sozinho quando ele volta.
- **D10** Confirmação da remoção com `window.confirm` (sem modal próprio antes do design).

## 5. Ferramentas e requisitos

- Node 20+ (máquina: 24.19) e npm.
- Dependências: `react`, `react-dom`, `react-router-dom`; dev: `vite`, `@vitejs/plugin-react`, `vitest`, `tailwindcss` (4.x), `@tailwindcss/vite`. Versões: as estáveis mais recentes no momento da instalação, registradas no `package.json` e no `package-lock.json` (commitado).
- Para a verificação manual: backend rodando (`uvicorn app.main:app --reload` em `backend/`), EC2 ligada, ao menos um Wokwi (`vinheria001`) rodando.
- Nenhuma mudança no backend.

## 6. Como verificar

1. `cd frontend && npm test` → **30 testes passando** (9 do client, 4 da validação, 17 dos eventos).
2. `npm run build` → termina sem erros.
3. Checklist manual do `plan.md` (subtarefa 5A.8), que cobre R3, R5, R6 e R7 no navegador, com o console sem erros.
