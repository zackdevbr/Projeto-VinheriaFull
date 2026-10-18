# Spec — Task 5B: Design system Smart Solutions e visual das telas da 5A

> Método spec-driven: esta spec diz **o que** a Task 5B entrega e **como saber que está certo**. O passo a passo fica em [`plan.md`](plan.md), que segue esta spec item por item. Se as duas divergirem, a spec manda e o executor para e devolve para planejamento.
>
> Fonte: Task 5 de [`PLANO-CP5-VINHERIA.md`](../../../PLANO-CP5-VINHERIA.md) (gate de design), as duas referências enviadas pelo usuário em 18/10/2026, a análise em [`design-dna.json`](design-dna.json) e as decisões tomadas com o usuário na mesma data. Formato do `CLAUDE.md` §3: Contexto → Objetivo → Detalhes técnicos → Ferramentas e requisitos → Passos (no plano) → Como verificar.

---

## 1. Contexto

**Por que existe.** A Task 5A entregou estrutura e comportamento do painel com visual neutro e provisório, porque o gate de design (`CLAUDE.md` §5) proíbe decisões visuais antes das referências. O usuário enviou as referências em 18/10/2026. Esta task cria o design system e o aplica às telas da 5A, deixando um kit de componentes pronto para a Task 6.

**Referências (arquivos locais do usuário, não versionados).**
- **A — base de marca** (cores, fontes, tom): "Nocturne winery: UX/UI design". Creme, bordô, serifa didone grande, faixas de rótulo bordô sobre o produto, seção de números grandes em serifa.
- **B — organização do painel**: "Dark Mode SaaS Dashboard UI: Red Bento Box Layout". Cartões KPI com ícone, gráfico de área com gradiente, grade bento, cartão de destaque em cor sólida, rosca de desempenho, lista com valor à direita.
- Regra de mistura: **A manda em cor, fonte e tom; B manda em organização.** O vermelho neon e o brilho de B não são copiados.

**O que já está pronto (5A, verificada com EC2 e Wokwi em 18/10/2026).**
- Rotas `/`, `/vinherias/:id`, `/alertas`, `/dispositivos`, `/chat` e 404; `ConfigContext`, `FleetContext`, `usePolling`, `useAcao`, `criarContexto`.
- `components/ui.jsx` (`Titulo`, `Campo`, `Botao`, `MensagemErro`, `Nota`, `LinkVinheria`) e `estilo.js` (`COR_STATUS`, `COR_SAUDE`, `BORDA_TOAST`) concentram todo o visual: foram feitos para a 5B trocar o visual num lugar só.
- Telas: `FiwareBar`, `AlertBanner` (faixa + toasts), `Devices` (`DeviceForm` + `DeviceList`), `Placeholder`.
- 30 testes do Vitest (client, validação, eventos), build ok.

**O que depende desta task.**
- Task 6: Visão geral, detalhe e alertas nascem com os tokens e o kit desta task (`Cartao`, `CartaoKpi`, `SeloStatus`, `GradeBento`, `Esqueleto`, `useContagem`).
- Task 7A: tela de chat no mesmo visual.
- Envio das imagens pelo usuário: troca os slots `ImagemReservada` do logo e do herói por fotos, sem mexer no layout.

## 2. Objetivo

Com `npm run dev`, o painel abre em fundo creme com a marca Smart Solutions em serifa bordô. A navegação fica na barra inferior com ícones em telas abaixo de 768 px e no topo nas maiores. A Visão geral mostra o herói com o espaço reservado da imagem. `/dispositivos` mostra o cadastro e as vinherias como cartões no celular e como linhas alinhadas no desktop, com selo de status de ícone e texto. Todo o comportamento da 5A segue idêntico. Em 375, 768, 1024 e 1440 px não há rolagem horizontal, o foco por teclado é visível, os textos têm contraste ≥ 4,5:1 e, com `prefers-reduced-motion`, nada se anima. `npm test` e `npm run build` passam.

## 3. Requisitos e critérios de aceite

Formato: **QUANDO** <situação>, o sistema **DEVE** <comportamento>. Testes automáticos estão no `plan.md`; os itens marcados *(manual)* são conferidos no navegador.

### R1 — Tokens (`src/styles.css`, bloco `@theme` do Tailwind v4)
- **R1.1** Cores, com estes nomes e valores exatos:

  | token | hex | uso | contraste sobre `creme` |
  |---|---|---|---|
  | `creme` | `#F4E8E0` | fundo da página | — |
  | `papel` | `#FBF5F0` | cartões, barras | — |
  | `linha` | `#EBDAD0` | bordas, divisores | decorativo |
  | `rose` | `#B5838D` | preenchimento de gráfico, ilustração | decorativo, nunca texto |
  | `bordo` | `#7A1F2B` | marca, títulos, número grande, botão primário, cartão destaque | 8,49:1 |
  | `vinho` | `#3A1A1C` | texto principal | 12,99:1 |
  | `taupe` | `#5E4843` | texto secundário, status offline/aguardando | 7,03:1 |
  | `ok` | `#4F6B3A` | status ok, EC2 online | 4,99:1 |
  | `config` | `#8A5A12` | status configurando | 4,92:1 |
  | `alerta` | `#A4161A` | status alerta, erros, EC2 fora | 6,45:1 |

  Creme sobre bordô: 9,44:1. `alerta` e `bordo` têm só 1,32:1 entre si, por isso a R4.3 exige ícone e texto em todo status.
- **R1.2** Fontes: `--font-display` Playfair Display (400, 600), `--font-sans` Inter (400, 500, 600) e `--font-mono` JetBrains Mono (400), carregadas pelos pacotes `@fontsource` importados em `main.jsx`. DEVE não haver `<link>` para fonts.googleapis.com.
- **R1.3** Tipografia (classes utilitárias ou `@utility` no `styles.css`):
  - `display`: `clamp(2.75rem, 10vw, 6rem)`, peso 400, altura de linha 0.95;
  - `titulo`: `clamp(2rem, 6vw, 3rem)`, 400, 1.05;
  - `subtitulo`: `clamp(1.5rem, 4vw, 2rem)`, 400, 1.15;
  - corpo: 1rem / 1.55;
  - `overline`: 0.6875rem, peso 600, caixa alta, `tracking` 0.14em.

  Valores de sensor e contagens usam `tabular-nums`.
- **R1.4** Forma e profundidade: raio de 4 px em botão e input, 16 px em cartão, pílula em selo. Três sombras quentes:
  - `--shadow-baixa`: `0 1px 2px rgb(58 26 28 / .06)`;
  - `--shadow-media`: `0 4px 16px rgb(58 26 28 / .08)`;
  - `--shadow-alta`: `0 16px 40px rgb(58 26 28 / .14)`.
- **R1.5** Movimento: durações de 150, 250 e 450 ms, easing `cubic-bezier(.22,1,.36,1)`. Animações nomeadas:
  - `entrar`: fade-up de 8 px;
  - `pulsar`: opacidade/escala do ponto de alerta;
  - `brilho`: varredura lenta do esqueleto.

  QUANDO `prefers-reduced-motion: reduce`, todas DEVEM ser desligadas (bloco `@media` único no `styles.css`).
- **R1.6** `body` com fundo `creme`, texto `vinho`, fonte `sans`, `antialiased`. Margem lateral de 16 px abaixo de 768 px e de 24 px acima; conteúdo com largura máxima de 1200 px, centralizado.
- **R1.7** DEVE não haver hex cru, `rgb(` ou `style={` em `.jsx`; cor só por token.

### R2 — Casca (`App.jsx`, `FiwareBar`, nova `NavInferior`)
- **R2.1** A barra superior é fixa no topo, com fundo `papel` e borda inferior `linha`. À esquerda, o slot do logo: `ImagemReservada` de 32 px de altura. Sem `src`, mostra "Smart Solutions" em `font-display` `bordo`.
- **R2.2** O selo de saúde do FIWARE é ponto + texto com a cor por estado (`COR_SAUDE`).
  - Abaixo de 768 px, só o ponto + "FIWARE".
  - A partir de 768 px, o rótulo completo da 5A + o IP em `font-mono`.
- **R2.3** O "Avançado" vira botão de ícone (`Settings`, com `aria-label` "Configurações avançadas" e `aria-expanded`). Ele abre um painel sob a barra: largura total abaixo de 768 px, caixa de 360 px alinhada à direita acima disso. O conteúdo e o comportamento são os da 5A: campo de IP, Salvar, mensagem de salvo/erro, status dos três serviços.
  - Fecha com Esc e com o mesmo botão.
  - O foco vai para o campo ao abrir e volta ao botão ao fechar.
  - *(manual)*
- **R2.4** A partir de 768 px, os 4 itens do menu ficam na barra superior, à direita do selo. O item ativo é `bordo` com sublinhado, os inativos `taupe`. A navegação é só por `NavLink`.
- **R2.5** Abaixo de 768 px, a `NavInferior` fica fixa no rodapé, com fundo `papel` e borda superior `linha`.
  - 4 itens com ícone Lucide + rótulo: `LayoutGrid` Visão geral, `Cpu` Dispositivos, `BellRing` Alertas, `MessageCircle` Chat.
  - Cada alvo tem ≥ 44×44 px. O padding inferior usa `env(safe-area-inset-bottom)`.
  - O ativo é `bordo` com traço de 2 px no topo.
  - O item Alertas mostra um selo numérico com `emAlerta.length + offline.length` de `bannerSummary(fleet)`, escondido quando zero. A contagem DEVE vir do `FleetContext`, sem nova chamada HTTP.
  - O `<main>` ganha recuo inferior igual à altura da barra.
  - A partir de 768 px, a barra DEVE não ser renderizada visualmente (`md:hidden`).
- **R2.6** A lista de menu (rótulo, rota, ícone) é uma constante única, compartilhada pelo menu do topo e pela `NavInferior`.

### R3 — Aviso global (`AlertBanner`)
- **R3.1** A faixa fica sob a barra superior: fundo `alerta` a 8 % (`bg-alerta/8`), borda inferior `alerta`, ícone `TriangleAlert` e texto `vinho`. O conteúdo e as regras são os da 5A (`bannerSummary`), e os links continuam via `LinkVinheria`.
  - Abaixo de 768 px, uma linha de resumo ("N vinherias precisam de atenção" ou a mensagem da EC2) seguida da lista de links, que quebra linha.
  - *(manual)*
- **R3.2** Os toasts têm fundo `papel`, sombra média, faixa lateral de 4 px na cor do tipo, ícone do tipo (`ICONE_TOAST`), texto e link "Ver detalhe".
  - O botão fechar é ícone `X` com `aria-label` "Fechar aviso" e alvo ≥ 44 px.
  - Abaixo de 768 px: largura total menos as margens, posicionados acima da `NavInferior`.
  - A partir de 768 px: canto inferior direito, até 384 px.
  - Entram com a animação `entrar`. As regras de evento e o limite são os da 5A, sem mudança.

### R4 — Kit de componentes (`components/ui.jsx`)
- **R4.1** Reestilizadas, com a mesma API da 5A (nenhuma tela quebra):
  - `Titulo` ganha a prop opcional `overline`.
  - `Campo` tem rótulo em estilo overline, input de 44 px de altura, fundo `papel`, borda `linha` e foco com anel de 2 px `bordo`.
  - `Botao` ganha a prop `variante` = `primario` (padrão: `bordo` sólido, texto `papel`) | `secundario` (contorno `bordo`) | `perigo` (contorno `alerta`), com altura mínima de 44 px e `disabled` a 50 % de opacidade.
  - `MensagemErro` ganha o ícone `CircleAlert` + texto `alerta`.
  - `Nota` usa texto `taupe`.
  - `LinkVinheria` fica `bordo`, com sublinhado no hover e no foco.
- **R4.2** Novas:
  - `Overline({ children, icone })`.
  - `Cartao({ variante = 'padrao' | 'destaque', larg, children })`: `papel`, raio de 16 px, borda `linha`, padding de 16 px (24 px a partir de `md`). `destaque` é fundo `bordo` com texto `papel`. `larg` repassa para a `GradeBento`.
  - `CartaoKpi({ rotulo, icone, valor, unidade, rodape, variante })`: `Overline` com ícone, valor em `font-display` com `tabular-nums`, unidade menor ao lado e rodapé opcional em `taupe`. Mostra `—` quando `valor` é `null`.
  - `SeloStatus({ status })`: pílula com ícone (`ICONE_STATUS`), rótulo (`STATUS_ROTULO`) e cor (`COR_STATUS`). Em `alerta`, o ponto/ícone tem a animação `pulsar`.
  - `GradeBento({ children })`: `grid` de 1 coluna, 2 em `md` e 4 em `lg`, com gap de 12/16 px. Os filhos aceitam `larg` = 1 | 2 | 3 | 4, mapeado para classes `lg:col-span-*` escritas por inteiro.
  - `ImagemReservada({ proporcao, rotulo, src, alt })`: caixa com a proporção fixa por classe (`aspect-*`).
    - Sem `src`: gradiente `bordo` → `creme` + `rotulo` discreto em overline.
    - Com `src`: `<img>` com `object-cover`, `loading="lazy"` e o `alt`.
  - `Heroi({ titulo, subtitulo, imagem })`: `ImagemReservada` em 4:3 abaixo de 768 px e 21:9 acima, véu em gradiente de baixo para cima (`vinho` a 85 % → `bordo` a 40 % → transparente, para o subtítulo pequeno manter ≥ 4,5:1 sobre qualquer foto) e o título `display` + subtítulo em `papel` por cima.
  - `EstadoVazio({ titulo, texto, acao })`: texto central em `taupe` com ação opcional (`Botao` ou link do router).
  - `Esqueleto({ className })`: bloco `linha` com a animação `brilho`.
- **R4.3** Todo status de vinheria mostrado na interface DEVE usar `SeloStatus` (ícone + texto, nunca só cor).
- **R4.4** QUANDO `ui.jsx` passar de ~250 linhas, ele DEVE virar a pasta `components/ui/` (um arquivo por grupo) com um `index.js` que reexporta tudo. Os imports das telas mudam só de `./ui.jsx` para `./ui` (mudança mecânica).

### R5 — Mapas de estilo (`src/estilo.js`)
- **R5.1** `COR_STATUS`, `COR_SAUDE` e `BORDA_TOAST` usam só classes de token:

  | estado | cor |
  |---|---|
  | ok, online, normal, fiware_online | `ok` |
  | alerta, offline/sem_backend da saúde, fiware_offline | `alerta` |
  | configurando | `config` |
  | offline da vinheria, aguardando, verificando | `taupe` |

  `COR_STATUS` passa a ter as classes do selo (texto + fundo a 10 % + borda).
- **R5.2** Novos mapas de ícones Lucide:
  - `ICONE_STATUS`: ok `CircleCheck`, alerta `TriangleAlert`, configurando `SlidersHorizontal`, offline `WifiOff`, aguardando `Hourglass`.
  - `ICONE_TOAST`: alerta `TriangleAlert`, offline `WifiOff`, normal `CircleCheck`, fiware_offline `ServerCrash`, fiware_online `Server`.

### R6 — Contagem animada (`lib/contagem.js`, `hooks/useContagem.js`)
- **R6.1** `interpolar(de, para, progresso)` é pura e devolve o valor com easing ease-out cúbico.
  - Para `progresso` ≤ 0, devolve `de`; para ≥ 1, devolve `para`.
  - Para `de === para`, devolve `para`.
  - Testes: extremos, ponto médio maior que o linear (ease-out), valores negativos (temperatura), `de === para`.
- **R6.2** `useContagem(valor, duracaoMs = 450)` anima de forma suave do valor anterior até o novo com `requestAnimationFrame` e cancela o quadro ao desmontar ou quando o valor muda.
  - Com `prefers-reduced-motion` ou `valor` não numérico, devolve `valor` direto.
  - Usado em `CartaoKpi`.

### R7 — Telas da 5A
- **R7.1** `Devices`:
  - `Titulo` com overline "Cadastro" e título "Dispositivos".
  - Abaixo de 1024 px: um `Cartao` "Nova vinheria" e, abaixo dele, a lista.
  - A partir de 1024 px: uma `GradeBento` com o formulário (`larg=1`) e a lista (`larg=3`) lado a lado, somando as 4 colunas.
  - O comportamento é o da 5A, incluindo "Provisionando no FIWARE…" e o recarregamento da frota.
- **R7.2** `DeviceForm`: os campos ficam empilhados abaixo de 1024 px e o botão primário ocupa a largura total. A validação, os textos e o fluxo são os da 5A.
- **R7.3** `DeviceList` deixa de usar `<table>` e vira uma lista (`<ul>`) de linhas em CSS grid, com marcação única para todos os tamanhos.
  - Abaixo de 768 px: cada linha é um cartão com nome em `font-display`, cidade, `device_id` em `font-mono`, `SeloStatus` e `Botao variante="perigo"` Excluir.
  - A partir de 768 px: as linhas alinham em colunas (Id · Nome · Cidade · Status · ação), com um cabeçalho em overline visível só nesse tamanho.
  - Lista vazia: `EstadoVazio` "Nenhuma vinheria cadastrada" com o texto "Cadastre a primeira no formulário.".
  - A confirmação continua por `window.confirm`, com o mesmo texto.
- **R7.4** `Placeholder`:
  - Rotas das Tasks 6 e 7A: `Titulo` + `EstadoVazio` "Esta tela chega na <task>.".
  - 404: `Titulo` "Página não encontrada" + `EstadoVazio` com link para a Visão geral.
  - Na rota `/`, o `Heroi` (título "Smart Solutions", subtítulo "Monitoramento de vinherias", sem imagem) vem antes do `EstadoVazio`.

### R8 — Imagens
- **R8.1** Só existem dois slots nesta task: o logo (R2.1) e o herói (R7.4). DEVE não haver arquivo de imagem novo no repositório. O favicon segue ausente (o 404 de `/favicon.ico` continua sendo o único erro de console aceito).
- **R8.2** Trocar um slot por imagem real DEVE exigir só passar `src` e `alt`, sem mexer em layout.

## 4. Decisões (com o porquê)

- **D1 Só tema claro** (usuário, 18/10). A Ref A é a marca; o escuro de B aparece só no cartão `destaque` em bordô. O `ui-ux-pro-max` sugeriu escuro OLED genérico para IoT e foi descartado por contradizer a Ref A.
- **D2 Barra inferior no celular** (usuário). Alcance do polegar, 4 itens, dentro do limite de 5.
- **D3 Imagens só no logo e no herói** (usuário). Foto por vinheria e ilustração de vazio ficam fora.
- **D4 Dependências novas** (usuário): `lucide-react` (ícones SVG lineares, sem emoji) e `@fontsource/*` (fontes no build, sem depender do CDN na demo).
- **D5 Tokens no `@theme` + kit em `ui.jsx`**, em vez de biblioteca de componentes (shadcn/daisyUI), que deixaria o visual genérico, brigaria com a serifa editorial e acrescentaria dependência.
- **D6 Alerta ≠ marca.** Bordô e vermelho de alerta são quase iguais em luminância (1,32:1), então status sempre leva ícone e texto (R4.3). O bordô nunca indica status.
- **D7 Movimento só em CSS + `requestAnimationFrame`**, sem GSAP: performance leve e nenhuma dependência a mais.
- **D8 Lista de dispositivos em grid, não tabela.** A mesma marcação serve de cartão no celular e de linha no desktop, sem duplicar JSX.

## 5. Ferramentas e requisitos

- Dependências novas: `lucide-react`; `@fontsource/playfair-display`, `@fontsource/inter`, `@fontsource/jetbrains-mono`. Versão estável mais recente na instalação, registrada no `package.json` e no `package-lock.json` (commitado).
- Skills na execução (anunciadas pelo executor):
  - `frontend-design` antes da primeira subtarefa visual;
  - `cast` na subtarefa de movimento;
  - `impeccable-design-polish` na auditoria final;
  - checklist `pro-rules.md` do `ui-ux-pro-max` na verificação.
- Para o ensaio manual: backend rodando, EC2 ligada, ao menos um Wokwi (`vinheria001`).
- Nenhuma mudança no backend.

## 6. Fora do escopo

Fotos reais, foto por vinheria, ilustração de estado vazio, favicon, modo escuro, gráficos, `GaugeScore`, telas de Visão geral/detalhe/alertas (Task 6) e chat (Task 7A).

## 7. Como verificar

1. `cd frontend && npm test` → os 30 testes da 5A + os novos de `contagem.js`, todos passando.
2. `npm run build` → sem erros.
3. Conferências estáticas (comandos no `plan.md`):
   - nenhum hex/`rgb(`/`style={` em `.jsx`;
   - nenhum `fetch(` fora de `api/client.js`;
   - nenhum `<table>`;
   - nenhum link para fonts.googleapis.com;
   - nenhum arquivo de `src/` acima de ~250 linhas;
   - nenhum `.ts`/`.tsx`.
4. Navegador, em 375, 768, 1024 e 1440 px *(manual)*:
   - sem rolagem horizontal;
   - `NavInferior` só abaixo de 768 px;
   - menu no topo a partir dela;
   - foco visível em todo elemento interativo por Tab;
   - Avançado fecha com Esc;
   - contraste dos textos conforme R1.1;
   - com "Emulate prefers-reduced-motion" no DevTools, nada anima.
5. Ensaio da 5A repetido com EC2 e Wokwi *(manual)*: troca de IP, cadastro e remoção de `vinheria099`, toast e faixa de offline e de volta, backend parado e voltando. O comportamento DEVE ser idêntico ao da 5A.
6. Auditoria `impeccable-design-polish` feita, com os achados corrigidos ou registrados no `plan.md`.
