# Spec — Task 6: Visão geral, detalhe com gráficos, faixa, comandos e alertas

> Método spec-driven: esta spec diz **o que** a Task 6 entrega e **como saber que está certo**. O passo a passo fica em [`plan.md`](plan.md), que segue esta spec item por item. Se as duas divergirem, a spec manda e o executor para e devolve para planejamento.
>
> Fonte: Task 6 de [`PLANO-CP5-VINHERIA.md`](../../../PLANO-CP5-VINHERIA.md), PRD (RF04, RF05, RF06, RF09, RF10, RF11, RF12), design system da Task 5B ([`../task-5b-design-system/spec.md`](../task-5b-design-system/spec.md), [`design-dna.json`](../task-5b-design-system/design-dna.json)) e as decisões tomadas com o usuário em 19/10/2026. Formato do `CLAUDE.md` §3.

---

## 1. Contexto

**Por que existe.** O backend já cadastra, lê, guarda faixa, dispara comandos e registra alertas, mas no painel só existem a tela de dispositivos e os placeholders. Esta task entrega as três telas centrais da demo: a visão geral da frota, o detalhe de uma vinheria (valores, gráficos do STH, score, faixa e alerta manual) e o histórico de alertas.

**O que já está pronto.**
- **Backend** (285 testes), endpoints usados aqui:
  - `GET /api/fleet` → `{ fiware_online, fiware_offline_since, updated_at, vinherias: [{ device_id, name, city, status: ok|alerta|offline|configurando, offline_reason: sem_leitura|fiware|null, last_seen, seconds_since, current: { temperature, humidity, luminosity }, score, active_alerts: [{ attr, value, since }] }] }`.
  - `GET /api/devices/{id}` → `{ device_id, name, city, ..., limits }`; 404 se não existe.
  - `GET /api/devices/{id}/history?attr=temperature|humidity|luminosity&last_n=1..500` **ou** `&date_from=ISO&date_to=ISO` → `[{ ts, value }]`. O parâmetro é `last_n` (snake_case).
  - `GET /api/devices/{id}/score` → `{ device_id, score: number|null, available, message, attrs: { temperature, humidity, luminosity }, limits }`.
  - `GET /api/devices/{id}/triggers` → `{ temperature: {min,max}, humidity: {min,max}, luminosity: {min,max} }`.
  - `PUT /api/devices/{id}/triggers` (mesmo corpo) → `{ device_id, limits, device_sync: "enviado"|"pendente" }`; 422 se min ≥ max.
  - `POST /api/devices/{id}/commands { command: blink_temp|blink_hum|blink_lux|alert_off }` → 202; **409** se a vinheria está offline ou configurando.
  - `GET /api/alerts?device_id=&limit=1..500` → `[{ id, device_id, attr: temperature|humidity|luminosity|offline, value, opened_at, closed_at, duration_seconds }]`, do mais novo ao mais velho. `device_id=fiware` registra a queda da EC2.
  - Erros saem como `{ detail, service }` e já viram `ApiError` no `client.js`.
- **Front** (41 testes):
  - `api/client.js` (`request`, `api.*`), `usePolling`, `useAcao`, `useContagem`, `FleetContext` (frota a cada 5 s), `criarContexto`;
  - kit `components/ui/` (`Titulo`, `Subtitulo`, `Overline`, `Campo`, `Botao`, `BotaoIcone`, `Cartao`, `CartaoKpi`, `GradeBento`, `SeloStatus`, `Heroi`, `ImagemReservada`, `EstadoVazio`, `Esqueleto`, `LinkInterno`, `LinkVinheria`, `MensagemErro`, `Nota`), `estilo.js`, tokens no `styles.css`;
  - herói com a foto da adega (`IMAGEM_HEROI`).

**O que depende desta task.** Task 7A (chat usa as mesmas rotas e o mesmo visual), Task 7B (botão de exportar no detalhe) e o ensaio do hands-on.

## 2. Objetivo

Com o backend, a EC2 e ao menos dois Wokwi ligados, `/` mostra o herói, quatro indicadores da frota e um cartão por vinheria (status, valores, score, "visto há"), com quem está em alerta no topo. Clicar num cartão abre `/vinherias/:id`, que mostra:
- o score em rosca, os valores atuais e três gráficos do STH-Comet que se atualizam sozinhos, com as linhas da faixa;
- o formulário da faixa, que salva e move as linhas;
- os botões de alerta manual;
- a linha do tempo da vinheria.

`/alertas` lista o histórico com filtro por vinheria. Esquentar o sensor de um Wokwi altera só o cartão, os gráficos, o selo, a linha do tempo e o ESP32 daquela vinheria.

## 3. Requisitos e critérios de aceite

Formato: **QUANDO** <situação>, o sistema **DEVE** <comportamento>. Testes automáticos estão no `plan.md`; itens *(manual)* são conferidos no navegador.

### R1 — Cliente HTTP (`src/api/client.js`)
- **R1.1** `api` DEVE ganhar: `getDevice(id)`, `getHistory(id, { attr, lastN, dateFrom, dateTo })`, `getScore(id)`, `getTriggers(id)`, `saveTriggers(id, limits)`, `sendCommand(id, command)`, `getAlerts({ deviceId, limit })`.
- **R1.2** `getHistory` DEVE montar `?attr=<attr>&last_n=<n>` quando `lastN` existe, senão `?attr=<attr>&date_from=<iso>&date_to=<iso>`, sempre com `URLSearchParams`. `getAlerts` DEVE omitir `device_id` quando `deviceId` é vazio.
  - Testes: a query de `last_n`, a de datas e a de alertas sem e com `device_id`.

### R2 — Lógica pura (`src/lib/`)
- **R2.1** `resumoFrota(frota)` → `{ total, ok, alerta, offline, configurando }`. Com frota `null`, todos 0.
- **R2.2** `ordenarFrota(vinherias)` → nova lista: alerta, offline, configurando, ok (status desconhecido por último); empate por `device_id`. Não altera a lista recebida.
- **R2.3** `vistoHa(segundos)`:

  | entrada | saída |
  |---|---|
  | `null` | "sem leitura" |
  | < 5 | "agora" |
  | < 60 | "há N s" |
  | < 3600 | "há N min" |
  | demais | "há N h" |

- **R2.3a** `textoVisto(vinheria)` → "EC2 fora" quando `offline_reason === 'fiware'`, senão `vistoHa(seconds_since)`. Usado no cartão e no cabeçalho do detalhe.
- **R2.4** `validarFaixa(faixa)` → `{ dados, erros }`.
  - Cada `min`/`max` vem como texto do input, aceitando vírgula ou ponto, e vira número. Vazio ou não numérico dá erro "Informe um número".
  - Nos 3 atributos, `min ≥ max` dá erro "O mínimo precisa ser menor que o máximo" no campo `max`.
  - Com erro, `dados` é `null`. `erros` é um objeto `{ "temperature.min": "...", ... }`, vazio quando válido.
- **R2.5** `parametrosJanela(janela)`:
  - `{ tipo: 'ultimos', n }` → `{ lastN: n }`;
  - `{ tipo: 'datas', de, ate }` (strings `datetime-local`) → `{ dateFrom, dateTo }` em ISO;
  - datas vazias ou `de ≥ ate` → `{ erro: "..." }`.
- **R2.6** `paraSerie(pontos)` → `{ rotulos: ['HH:mm:ss'...], valores: [...] }`, no fuso local. Lista vazia → listas vazias.
- **R2.7** `duracao(segundos)`:

  | entrada | saída |
  |---|---|
  | `null` | "em aberto" |
  | < 60 | "N s" |
  | < 3600 | "N min N s" |
  | demais | "N h N min" |

- **R2.8** `rotuloAlerta(alerta)`:
  - "Temperatura 21,4 °C", "Umidade 75 %", "Luminosidade 40 %", com vírgula decimal pt-BR;
  - "Offline" para `attr=offline`;
  - "EC2 / FIWARE fora do ar" quando `device_id === 'fiware'`;
  - valor `null` → só o nome do atributo.
- **R2.9** `foraDaFaixa(valor, faixa)` → `true` se `valor < min` ou `valor > max`; `false` com `valor` ou `faixa` nulos.

### R3 — Gráficos (`lib/graficos.js`, `lib/tema.js`, `SensorChart`)
- **R3.1** `chart.js` e `react-chartjs-2` instalados. Registro só dos módulos usados (`CategoryScale`, `LinearScale`, `PointElement`, `LineElement`, `LineController`, `Filler`, `Tooltip`, `Legend`, `ArcElement`, `DoughnutController`), feito uma vez em `lib/graficos.js`.
- **R3.2** As cores do Chart.js DEVEM vir dos tokens CSS lidos em runtime (`getComputedStyle(document.documentElement).getPropertyValue('--color-bordo')`) por `corDoTema(nome)` em `lib/tema.js`. Nenhum hex em `.js`/`.jsx` fora do `styles.css`.
- **R3.3** `SensorChart({ deviceId, attr, janela, faixa })`:
  - **Linha:** área com gradiente vertical bordô (opacidade 0,35 → 0), linha bordô de 2 px, `tension` 0.3.
  - **Faixa:** duas séries tracejadas `taupe` no mínimo e no máximo de `faixa`, legenda "mín"/"máx".
  - **Fora da faixa:** pontos com círculo `alerta` de 4 px; os demais sem ponto.
  - **Eixos e tooltip:** eixos em Inter `taupe` 11 px, grade `linha`, tooltip "HH:mm:ss · 21,4 °C".
  - **Layout:** `maintainAspectRatio: false` dentro de uma caixa de 224 px (288 px a partir de `md`).
  - **Estados:** lista vazia → `EstadoVazio` "Sem leituras nesta janela"; erro → `MensagemErro`; carregando → `Esqueleto` do mesmo tamanho.
- **R3.4** `useHistorico(deviceId, attr, janela)`: com `ultimos`, relê a cada 10 s (`usePolling`); com `datas`, lê uma vez por mudança de janela.

### R4 — Visão geral (`pages/Overview.jsx`, `components/VinheriaCard.jsx`)
- **R4.1** A ordem da página é: `Heroi` (5B, com `IMAGEM_HEROI`), depois `GradeBento` com 4 `CartaoKpi`:
  - "Vinherias" (`LayoutGrid`) = total;
  - "OK" (`CircleCheck`), com rodapé "N configurando" quando > 0;
  - "Em alerta" (`TriangleAlert`), na variante `destaque` quando > 0;
  - "Offline" (`WifiOff`).

  Depois vem a `GradeBento` dos cartões, ordenados por `ordenarFrota`.
- **R4.2** `VinheriaCard({ vinheria })` ocupa `larg=2`. Ele é um único `Link` para `/vinherias/:id` com foco visível e hover (sobe 2 px, sombra média).
  - **Cabeçalho:** faixa `bordo` com nome em Playfair `papel` e `SeloStatus`. A cidade fica abaixo, em `taupe`.
  - **Corpo:** os três valores em `font-display` com unidade (°C, %, %) e `—` quando nulos. Um atributo com alerta ativo (`active_alerts[].attr`) fica `text-alerta` com ícone `TriangleAlert`.
  - **Rodapé:** "Score N" (ou "Score —") e `vistoHa(seconds_since)`. Com `offline_reason === 'fiware'`, mostra "EC2 fora".
- **R4.3** Estados:
  - frota `null` → 4 `Esqueleto` de KPI + 2 de cartão;
  - frota sem vinherias → `EstadoVazio` "Nenhuma vinheria cadastrada" com link "Cadastrar vinheria" para `/dispositivos`.

### R5 — Detalhe (`pages/VinheriaDetail.jsx`)
- **R5.1** Os dados vêm de lugares diferentes:
  - nome, cidade, status e valores atuais saem do `FleetContext` (sem chamada nova);
  - a faixa sai de `getTriggers` e o score de `useScore` (10 s).
- **R5.2** O cabeçalho tem o link "Visão geral" (`LinkInterno` + `ArrowLeft`), `Titulo` com `overline` = cidade e texto = nome, `SeloStatus` e `vistoHa`.
- **R5.3** O id `:id` que não está na frota: se `getDevice` responde, a vinheria acabou de ser cadastrada → `EstadoVazio` com o nome e "Aguardando o primeiro ciclo do monitoramento"; se falha (404) → `EstadoVazio` "Vinheria não encontrada" com link para `/`.
- **R5.4** Topo em `GradeBento`:
  - `GaugeScore` (cartão `destaque`): rosca `Doughnut` com `cutout` 78 %, arco `papel` sobre trilho `papel` a 20 %, número central com `useContagem` e as notas por atributo abaixo ("T 100 · U 85 · L 92"). Score `null` → `—` + `message`.
  - 3 `CartaoKpi` (Temperatura `Thermometer` °C, Umidade `Droplets` %, Luminosidade `Sun` %), com rodapé "Faixa 12–18 °C". Quando `foraDaFaixa`, o rodapé vira "Fora da faixa 12–18 °C" em `alerta`, com ícone.
- **R5.5** Abaixo do topo vêm o `SeletorJanela` e os 3 `SensorChart`, um por `Cartao larg=4`, todos com a mesma janela. A janela padrão é `{ tipo: 'ultimos', n: 50 }`.
- **R5.6** Depois vêm `TriggerPanel` e `PainelComandos` (`larg=2` cada) e, por fim, `AlertTimeline` da vinheria (`larg=4`, `limit=20`) com o link "Ver todos os alertas" para `/alertas?vinheria=<id>`.

### R6 — Seletor de janela (`components/SeletorJanela.jsx`)
- **R6.1** `BotoesSegmentados` com "20", "50", "100" e "Datas"; o ativo fica com `aria-pressed="true"` e fundo `bordo`.
- **R6.2** "Datas" mostra dois `Campo type="datetime-local"` ("De", "Até") + `Botao` "Aplicar". O erro de `parametrosJanela` aparece via `MensagemErro`, e a janela só muda com dados válidos.

### R7 — Faixa ideal (`components/TriggerPanel.jsx`)
- **R7.1** O formulário mostra 3 linhas (Temperatura °C, Umidade %, Luminosidade %), cada uma com `Campo` "Mín" e "Máx", `inputMode="decimal"`, preenchidos por `getTriggers`. Enquanto carrega: `Esqueleto`.
- **R7.2** Salvar valida com `validarFaixa`. Os erros aparecem sob o campo correspondente e nada é enviado. Válido → `saveTriggers`.
  - Sucesso com `device_sync === 'enviado'` → "Faixa salva e enviada ao ESP32".
  - `pendente` → "Faixa salva. O ESP32 recebe quando voltar a ficar online.".
  - Ambas as mensagens saem em `role="status"`. Depois, chama `onSalvo()`, que relê o score (as linhas tracejadas mudam na hora).
- **R7.3** O botão fica com "Salvando…" e desabilitado durante o envio (`useAcao`).

### R8 — Alerta manual (`components/PainelComandos.jsx`)
- **R8.1** Quatro botões:
  - "Piscar temperatura" (`blink_temp`), "Piscar umidade" (`blink_hum`) e "Piscar luz" (`blink_lux`), em `secundario`;
  - "Desligar alerta" (`alert_off`), em `perigo`.
- **R8.2** Com `status` `offline` ou `configurando`, todos ficam desabilitados com a nota "Vinheria offline: os comandos voltam quando ela reconectar." ou "Vinheria aguardando a faixa (configurando).".
- **R8.3** Sucesso → "Comando enviado" (`role="status"`, some em 4 s). Erro (incluindo 409) → `MensagemErro` com o `detail` do backend. Um envio por vez.

### R9 — Linha do tempo (`components/AlertTimeline.jsx`) e página Alertas
- **R9.1** `AlertTimeline({ deviceId, limite, mostrarVinheria })` lê `getAlerts` a cada 10 s. Cada item (`<li>`) mostra:
  - ícone do atributo (`Thermometer`, `Droplets`, `Sun`, `WifiOff`; `ServerCrash` para fiware) e `rotuloAlerta`;
  - início `dd/mm HH:mm`, e fim ou um selo "em aberto" com `animate-pulsar`;
  - `duracao(duration_seconds)`;
  - com `mostrarVinheria`, o nome da vinheria via `LinkVinheria`, ou "EC2" para fiware.

  Vazio → "Nenhum alerta registrado".
- **R9.2** Página `/alertas`:
  - `Titulo` com `overline` "Histórico" e título "Alertas".
  - `Seletor` "Vinheria" com "Todas", cada vinheria da frota ("Nome · Cidade") e "EC2 / FIWARE". O valor fica em `?vinheria=` (`useSearchParams`), e trocar não recarrega a página.
  - Dois `CartaoKpi`: "Em aberto" (`destaque` quando > 0) e "Registrados" (quantidade listada).
  - `AlertTimeline` com `limite=100` e `mostrarVinheria` quando o filtro é "Todas".

### R10 — Kit (`components/ui/`)
- **R10.1** `Seletor({ rotulo, opcoes: [{valor, rotulo}], ...props })`: `<select>` com o mesmo visual do `Campo` (overline, 44 px, borda `linha`, foco bordô).
- **R10.2** `BotoesSegmentados({ opcoes, valor, aoMudar, rotulo })`: grupo `role="group"` com `aria-label`; cada botão tem ≥ 44 px e `aria-pressed`.
- **R10.3** `Cartao` ganha a prop opcional `para` (rota): com ela, o cartão inteiro vira um `Link` do router, com hover (sobe 2 px, `shadow-media`, transição de 150 ms) e foco visível. Usada pelo `VinheriaCard`. O caminho do detalhe sai de `caminhoVinheria(id)` (`lib/rotas.js`), também usado pelo `LinkVinheria`.

### R11 — Qualidade
- **R11.1** Restrições da 5B continuam:
  - sem hex, `rgb(` nem `style={` em `.jsx`;
  - `fetch` só no client;
  - `<h1>`/`<h2>`/`<input>`/`<select>`/`<button>` só no kit;
  - arquivos ≤ ~250 linhas;
  - status sempre por `SeloStatus`;
  - alvos ≥ 44 px;
  - `prefers-reduced-motion` respeitado.
- **R11.2** O Chart.js com movimento reduzido usa `animation: false`.

## 4. Decisões (com o porquê)

- **D1 Uma spec, várias subtarefas** (usuário, 19/10): execução contínua como a 5B.
- **D2 Visão geral com herói + KPIs + cartões** (usuário): os KPIs seguem a Ref B, e o cartão de alerta em destaque chama o olho.
- **D3 Três gráficos visíveis** (usuário): na demo, os três reagem juntos; custa 3 leituras do STH a cada 10 s por vinheria aberta.
- **D4 Um seletor de janela para os três** (usuário): compara janelas iguais e polui menos o celular.
- **D5 Hooks sobre `usePolling`**, sem React Query ou SWR: reaproveita o que existe e evita dependência nova.
- **D6 Rótulos `HH:mm:ss` em eixo de categoria**, sem eixo de tempo do Chart.js: evita o adaptador de datas (dependência a mais). As leituras chegam a cada ~2 s, quase uniformes, então o eixo de categoria não distorce a leitura.
- **D7 Valores atuais da frota**, não de `/current`: já chegam a cada 5 s sem chamada nova.
- **D8 Comandos manuais no detalhe (RF09)**: o plano original da Task 6 não os listava, mas o PRD pede e o endpoint existe.
- **D9 Cores do gráfico lidas dos tokens CSS em runtime**: a paleta continua com fonte única no `styles.css`.

## 5. Ferramentas e requisitos

- Dependências novas: `chart.js`, `react-chartjs-2` (estáveis mais recentes, registradas no `package-lock.json`).
- Skills na execução: `superpowers:executing-plans` e `superpowers:test-driven-development`; `dataviz` antes da primeira subtarefa de gráfico; `impeccable-design-polish` na auditoria.
- Ensaio manual: backend, EC2 e ao menos dois Wokwi (`vinheria001`, `vinheria002`) ligados.
- Nenhuma mudança no backend. Se faltar algo, o executor para e devolve ao planejamento.

## 6. Fora do escopo

Relatórios CSV/PDF (7B), chat (7A), deploy (planejado por último), comparação entre vinherias no mesmo gráfico, zoom e pan nos gráficos, edição de nome ou cidade.

## 7. Como verificar

1. `cd frontend && npm test`: os 41 da 5B + os novos de client e `lib/`, todos passando.
2. `npm run build` sem erros.
3. Conferências estáticas da 5B (comandos no `plan.md`), mais `<select>` só no kit.
4. Auditoria `impeccable-design-polish` com capturas do Edge headless (`/`, `/vinherias/vinheria001`, `/alertas`) em 500 e 1280 px, com os achados registrados no `plan.md`.
5. Ensaio *(manual)* com 2 Wokwi:
   1. esquentar o DHT da `vinheria002`: só o cartão, os gráficos, o selo, a linha do tempo e o ESP32 dela reagem; o cartão sobe para o topo da Visão geral; o KPI "Em alerta" fica bordô;
   2. no detalhe, baixar o máximo de temperatura abaixo do valor atual e salvar: as linhas tracejadas descem, o alerta dispara e a faixa chega ao LCD;
   3. "Piscar luz" faz o ESP32 piscar, e "Desligar alerta" para o buzzer;
   4. parar um Wokwi: o cartão vai para offline, os comandos ficam desabilitados e a linha do tempo mostra "Offline em aberto";
   5. `/alertas?vinheria=vinheria002` filtra, e o Voltar do navegador volta para "Todas";
   6. janela "Datas" com início depois do fim mostra o erro; um intervalo válido mostra os pontos.
