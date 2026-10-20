# Task 5B — Design system Smart Solutions e visual das telas da 5A — Plano de execução

> **Estado em 18/10/2026:** feitas as subtarefas 5B.1 a 5B.12 e a parte automática da 5B.13; ensaio manual com EC2, Wokwi e navegador real feito em 19/10/2026, tudo funcionando.

> **Para quem executa (Sonnet):** use `superpowers:executing-plans`. Os passos usam checkbox (`- [ ]`). Execute **uma subtarefa por vez**, informe o resultado de cada passo e **pare para revisão do usuário ao fim de cada subtarefa** (`CLAUDE.md` §2 e §4). Se algo não bater com a [`spec.md`](spec.md), pare e devolva para planejamento; não improvise. Toda decisão visual já está na spec e neste plano: **não invente cor, fonte, espaçamento ou componente novo**. Se faltar algo, pare e reporte.

**Objetivo:** aplicar o design system Smart Solutions (creme + bordô, Playfair Display + Inter, bento) às telas da 5A, com navegação inferior no celular, herói e logo com imagem reservada, e um kit de componentes pronto para a Task 6, sem mudar nenhum comportamento.

**Arquitetura:**
- Os tokens ficam no `@theme` do `src/styles.css` (Tailwind v4) e viram classes (`bg-creme`, `text-bordo`, `font-display`, `text-overline`, `shadow-media`, `animate-entrar`).
- O kit sai de `components/ui.jsx` para a pasta `components/ui/` (cinco arquivos por assunto + `index.js`).
- `src/estilo.js` mapeia status → classes de token e ícones Lucide.
- A lógica nova é pura e testada no Vitest: `lib/contagem.js`, `lib/status.js` e `contarAtencao` em `lib/fleetEvents.js`.
- Contexts, client e hooks da 5A não mudam.

**Stack:** React 19 + react-router-dom + Vite + Tailwind CSS v4, JavaScript puro, `lucide-react`, `@fontsource/*`, Vitest (ambiente `node`, só `src/**/*.test.js`).

**Spec:** [`docs/specs/task-5b-design-system/spec.md`](spec.md) (requisitos R1–R8, decisões D1–D8) e [`design-dna.json`](design-dna.json).

## Restrições globais

- Sem TypeScript; arquivos `.jsx`/`.js`.
- Comentário em português no topo de todo arquivo novo e em toda função não óbvia (`CLAUDE.md` §6).
- Cor só por token (R1.1). Proibido em `.jsx`: hex, `rgb(`, `style={` (R1.7). Classes Tailwind sempre escritas por inteiro (nada de `` `bg-${cor}` ``), para o Tailwind achá-las.
- Alvo de toque ≥ 44 px (`min-h-11`, `size-11`) em todo botão, link de menu e campo.
- Status de vinheria só via `SeloStatus` (ícone + texto), nunca só cor (R4.3, D6).
- Navegação só por `NavLink`/`Link`/`useNavigate`. `fetch` só em `src/api/client.js`.
- Arquivo de `src/` com no máximo ~250 linhas.
- `<h1>`, `<h2>`, `<input>` e `<button>` só dentro de `components/ui/`.
- Breakpoints do Tailwind padrão: `md` = 768 px, `lg` = 1024 px.
- Commits em português, no imperativo, uma linha, **sem** `Co-Authored-By` (`CLAUDE.md` §8).
- Nenhuma mudança no backend. Nenhum arquivo de imagem novo.

## Riscos que os testes cobrem (Review Focus)

1. **Status desconhecido vindo do backend** (ex.: um status novo numa versão futura). `SeloStatus` não pode quebrar a tela; ele mostra "Aguardando 1º ciclo". Coberto por `lib/status.test.js` (5B.3).
2. **Frota ainda `null`** (primeiro carregamento ou backend fora): o selo da barra inferior mostra nada, sem erro. Coberto por `contarAtencao` (5B.6).
3. **EC2 fora**: todas as vinherias ficam offline por motivo `fiware`, e o selo do menu NÃO pode mostrar "5" (a faixa já fala da EC2). Coberto por `contarAtencao` (5B.6).
4. **Valor de sensor negativo ou nulo no KPI**: a contagem anima negativos e mostra `—` para `null`. Negativos em `lib/contagem.test.js` (5B.4); o `null` é conferido no ensaio manual da 5B.5.
5. **Nome de 60 caracteres no celular de 375 px**: a lista quebra a linha sem rolagem horizontal. Conferido manualmente na 5B.9 (`break-words` + `min-w-0`).

## Mapa de arquivos

| arquivo | ação | responsabilidade |
|---|---|---|
| `frontend/package.json` | modificar | + `lucide-react`, `@fontsource/playfair-display`, `@fontsource/inter`, `@fontsource/jetbrains-mono` |
| `src/main.jsx` | modificar | importa as fontes |
| `src/styles.css` | modificar | `@theme` (tokens), base, foco, movimento reduzido, cascata |
| `src/constants.js` | modificar | `LOGO_SRC`, `IMAGEM_HEROI` (slots, `null`) |
| `src/estilo.js` | modificar | mapas de cor por token + `ICONE_STATUS`, `ICONE_TOAST` |
| `src/navegacao.js` | criar | `MENU` único (rota, rótulo, ícone) |
| `src/lib/contagem.js` + `.test.js` | criar | `interpolar` (pura) |
| `src/lib/status.js` + `.test.js` | criar | `statusConhecido` (pura) |
| `src/lib/fleetEvents.js` + `.test.js` | modificar | + `contarAtencao` |
| `src/hooks/useContagem.js` | criar | contagem animada com `requestAnimationFrame` |
| `src/components/ui.jsx` | apagar | vira a pasta abaixo |
| `src/components/ui/index.js` | criar | reexporta o kit |
| `src/components/ui/base.jsx` | criar | `Overline`, `Titulo`, `Subtitulo`, `Nota`, `MensagemErro`, `LinkInterno`, `LinkVinheria` |
| `src/components/ui/formulario.jsx` | criar | `Campo`, `Botao`, `BotaoIcone` |
| `src/components/ui/cartoes.jsx` | criar | `GradeBento`, `Cartao`, `CartaoKpi`, `SeloStatus` |
| `src/components/ui/imagem.jsx` | criar | `Logo`, `ImagemReservada`, `Heroi` |
| `src/components/ui/estados.jsx` | criar | `EstadoVazio`, `Esqueleto` |
| `src/components/MenuTopo.jsx` | criar | menu do topo (≥ 768 px) |
| `src/components/NavInferior.jsx` | criar | barra inferior (< 768 px) com selo de atenção |
| `src/components/PainelAvancado.jsx` | criar | formulário do IP + saúde dos serviços (saiu do `FiwareBar`) |
| `src/components/FiwareBar.jsx` | modificar | barra superior: logo, selo de saúde, menu, botão do Avançado |
| `src/components/AlertBanner.jsx` | modificar | faixa e toasts no novo visual |
| `src/App.jsx` | modificar | `<main>` com largura máxima, `NavInferior`, herói na rota `/` |
| `src/pages/Devices.jsx` | modificar | bento com formulário + lista |
| `src/components/DeviceForm.jsx` | modificar | campos empilhados, botão em largura total |
| `src/components/DeviceList.jsx` | modificar | `<ul>` em grid, cartão no celular |
| `src/pages/Placeholder.jsx` | modificar | `EstadoVazio`, herói, 404 |

Testes ao fim: 30 da 5A + 5 de `contagem` + 3 de `status` + 3 de `contarAtencao` = **41**.

---

## Subtarefa 5B.1 — Dependências, fontes e tokens (R1, D4)

**Files:** modificar `frontend/package.json` (via npm), `src/main.jsx`, `src/styles.css`.

- [ ] **Passo 1: anunciar e ler a skill `frontend-design`** (direção visual, anti-template). Ela orienta; as decisões já estão na spec.

- [ ] **Passo 2: instalar as dependências**

```bash
cd frontend
npm install lucide-react @fontsource/playfair-display @fontsource/inter @fontsource/jetbrains-mono
```
Esperado: as quatro aparecem em `dependencies` do `package.json`, sem erro de peer.

- [ ] **Passo 3: importar as fontes em `src/main.jsx`.** Troque o comentário do topo e acrescente os imports antes de `./styles.css`:

```jsx
/**
 * Ponto de entrada do painel: carrega as fontes do design system (empacotadas
 * no build pelo @fontsource, sem depender do CDN do Google na demo), liga o
 * roteador (BrowserRouter) e o Tailwind e monta o App.
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import '@fontsource/playfair-display/400.css';
import '@fontsource/playfair-display/600.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/jetbrains-mono/400.css';
import App from './App.jsx';
import './styles.css';
```
(o `createRoot(...)` abaixo fica igual)

- [ ] **Passo 4: substituir `src/styles.css` inteiro**

```css
/*
 * Design system Smart Solutions (Task 5B) sobre o Tailwind CSS v4.
 * Os tokens do @theme viram classes: bg-creme, text-bordo, font-display,
 * text-overline, shadow-media, max-w-pagina, animate-entrar etc. Cor ou
 * medida nova entra aqui, nunca como valor solto dentro de um componente.
 * Valores e porquês: docs/specs/task-5b-design-system/spec.md (R1).
 */
@import "tailwindcss";

@theme {
  /* Cores da marca (referência A) e de status; contraste conferido na spec R1.1 */
  --color-creme: #f4e8e0;
  --color-papel: #fbf5f0;
  --color-linha: #ebdad0;
  --color-rose: #b5838d;
  --color-bordo: #7a1f2b;
  --color-vinho: #3a1a1c;
  --color-taupe: #5e4843;
  --color-ok: #4f6b3a;
  --color-config: #8a5a12;
  --color-alerta: #a4161a;

  /* Famílias: serifa didone para títulos e números, sans para o resto, mono para ids e IP */
  --font-display: "Playfair Display", Georgia, serif;
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* Escala tipográfica fluida, do celular ao desktop */
  --text-display: clamp(2.75rem, 10vw, 6rem);
  --text-display--line-height: 0.95;
  --text-titulo: clamp(2rem, 6vw, 3rem);
  --text-titulo--line-height: 1.05;
  --text-subtitulo: clamp(1.5rem, 4vw, 2rem);
  --text-subtitulo--line-height: 1.15;
  --text-overline: 0.6875rem;
  --text-overline--line-height: 1.3;
  --text-overline--letter-spacing: 0.14em;
  --text-overline--font-weight: 600;

  /* Largura máxima do conteúdo */
  --container-pagina: 1200px;

  /* Sombras quentes, puxadas para o vinho em vez do cinza */
  --shadow-baixa: 0 1px 2px rgb(58 26 28 / 0.06);
  --shadow-media: 0 4px 16px rgb(58 26 28 / 0.08);
  --shadow-alta: 0 16px 40px rgb(58 26 28 / 0.14);

  /* Movimento: entrada dos cartões, pulso do alerta, brilho do esqueleto */
  --ease-suave: cubic-bezier(0.22, 1, 0.36, 1);
  --animate-entrar: entrar 250ms cubic-bezier(0.22, 1, 0.36, 1) both;
  --animate-pulsar: pulsar 1.6s ease-in-out infinite;
  --animate-brilho: brilho 1.4s linear infinite;

  @keyframes entrar {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes pulsar {
    0%,
    100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.55;
      transform: scale(0.85);
    }
  }

  @keyframes brilho {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }
}

@layer base {
  body {
    @apply bg-creme font-sans text-vinho antialiased;
  }

  /* Foco visível por teclado em todo elemento interativo */
  :focus-visible {
    @apply outline-2 outline-offset-2 outline-bordo;
  }
}

/* Quem pede menos movimento no sistema não vê nenhuma animação (spec R1.5) */
@media (prefers-reduced-motion: reduce) {
  *,
  ::before,
  ::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- [ ] **Passo 5: verificar**

```bash
npm test          # 30 passed (nada de lógica mudou)
npm run build     # sem erro
grep -o "fbf5f0\|Playfair Display" dist/assets/*.css | sort -u
```
Esperado: o CSS gerado contém `fbf5f0` e `Playfair Display`. Em `npm run dev`, a página fica creme, e o texto em Inter e vinho. As telas da 5A continuam funcionando, ainda com as classes cinza.

- [ ] **Passo 6: commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/main.jsx frontend/src/styles.css
git commit -m "chore: adiciona os tokens do design system, as fontes locais e os icones"
```

---

## Subtarefa 5B.2 — Kit vira a pasta `components/ui/` (R4.4, mudança mecânica)

Só move código, sem mudar o visual. O kit vai passar de 250 linhas, então a divisão vem antes de crescer.

**Files:** criar `src/components/ui/index.js`, `ui/base.jsx`, `ui/formulario.jsx`; apagar `src/components/ui.jsx`; modificar os imports de `FiwareBar.jsx`, `AlertBanner.jsx`, `DeviceForm.jsx`, `DeviceList.jsx`, `pages/Devices.jsx`, `pages/Placeholder.jsx`.

- [ ] **Passo 1: criar `ui/base.jsx`** com `Titulo`, `MensagemErro`, `Nota` e `LinkVinheria` copiados **sem mudança** de `ui.jsx`. Comentário do topo:

```jsx
/**
 * Peças de texto do design system: título de página, texto secundário,
 * mensagem de erro e links internos. Antes de escrever um destes à mão
 * numa tela, use o daqui (ou acrescente uma variação aqui).
 */
```

- [ ] **Passo 2: criar `ui/formulario.jsx`** com `Campo` e `Botao` copiados sem mudança. Comentário do topo:

```jsx
/**
 * Peças de formulário do design system: campo com rótulo e botões.
 */
```

- [ ] **Passo 3: criar `ui/index.js`**

```js
/**
 * Kit de componentes do design system Smart Solutions (Task 5B).
 * Telas e componentes importam sempre daqui: '../components/ui/index.js'.
 */
export * from './base.jsx';
export * from './formulario.jsx';
```

- [ ] **Passo 4: apagar `src/components/ui.jsx` e trocar os imports** nos 6 arquivos:
  - em `components/*`: `from './ui.jsx'` vira `from './ui/index.js'`;
  - em `pages/*`: `from '../components/ui.jsx'` vira `from '../components/ui/index.js'`.

- [ ] **Passo 5: verificar**

```bash
grep -rn "ui.jsx'" src      # esperado: nada
npm test && npm run build   # 30 passed, build ok
```
No `npm run dev`, as telas ficam idênticas às do passo anterior.

- [ ] **Passo 6: commit**

```bash
git add -A frontend/src
git commit -m "chore: divide o kit de componentes em uma pasta por assunto"
```

---

## Subtarefa 5B.3 — Peças de texto e formulário, mapas de estilo e `statusConhecido` (R4.1, R5)

**Files:** criar `src/lib/status.js`, `src/lib/status.test.js`; modificar `src/estilo.js`, `ui/base.jsx`, `ui/formulario.jsx`.

**Produz:** `statusConhecido(status) -> string`, `Overline({ icone, invertido, children })`, `Titulo({ overline, children })`, `Subtitulo({ children })`, `LinkInterno({ to, children })`, `Botao({ variante, className, ... })`, `BotaoIcone({ icone, rotulo, className, ...props })`, mapas `COR_STATUS`, `COR_SAUDE`, `BORDA_TOAST`, `ICONE_STATUS`, `ICONE_TOAST`.

- [ ] **Passo 1: escrever o teste que falha, `src/lib/status.test.js`**

```js
/** Testes de statusConhecido: status novo do backend não pode quebrar a tela (Task 5B). */
import { describe, expect, it } from 'vitest';
import { statusConhecido } from './status.js';

describe('statusConhecido', () => {
  it('mantém os status que o painel sabe desenhar', () => {
    for (const status of ['ok', 'alerta', 'offline', 'configurando', 'aguardando']) {
      expect(statusConhecido(status)).toBe(status);
    }
  });

  it('troca status desconhecido ou ausente por aguardando', () => {
    expect(statusConhecido('manutencao')).toBe('aguardando');
    expect(statusConhecido(undefined)).toBe('aguardando');
  });

  it('não aceita nomes herdados de Object', () => {
    expect(statusConhecido('toString')).toBe('aguardando');
    expect(statusConhecido('__proto__')).toBe('aguardando');
  });
});
```

- [ ] **Passo 2: rodar e ver falhar**

Rode `npm test -- status`. Esperado: FAIL, porque `./status.js` não existe.

- [ ] **Passo 3: implementar `src/lib/status.js`**

```js
/**
 * Normalização do status de uma vinheria para a interface. O backend pode
 * ganhar status novos; o painel desenha só os que conhece (STATUS_ROTULO)
 * e trata qualquer outro como "aguardando", em vez de quebrar a tela.
 */
import { STATUS_ROTULO } from '../constants.js';

export function statusConhecido(status) {
  return Object.hasOwn(STATUS_ROTULO, status) ? status : 'aguardando';
}
```

- [ ] **Passo 4: rodar e ver passar**

Rode `npm test`. Esperado: 33 passed.

- [ ] **Passo 5: substituir `src/estilo.js` inteiro**

```js
/**
 * Mapas de estilo por estado: classes Tailwind dos tokens do design system
 * (styles.css) e ícones Lucide. As classes ficam escritas por inteiro de
 * propósito, para o Tailwind encontrá-las ao gerar o CSS. As peças de
 * tela (título, botão, cartão...) moram em components/ui/.
 */
import {
  CircleCheck,
  Hourglass,
  Server,
  ServerCrash,
  SlidersHorizontal,
  TriangleAlert,
  WifiOff,
} from 'lucide-react';

// Selo de status de uma vinheria: texto, fundo a 10 % e borda na cor do estado
export const COR_STATUS = {
  ok: 'border-ok/30 bg-ok/10 text-ok',
  alerta: 'border-alerta/30 bg-alerta/10 text-alerta',
  configurando: 'border-config/30 bg-config/10 text-config',
  offline: 'border-taupe/30 bg-taupe/10 text-taupe',
  aguardando: 'border-taupe/30 bg-taupe/10 text-taupe',
};

// Ícone do selo de status (sempre junto do texto: a cor sozinha não basta)
export const ICONE_STATUS = {
  ok: CircleCheck,
  alerta: TriangleAlert,
  configurando: SlidersHorizontal,
  offline: WifiOff,
  aguardando: Hourglass,
};

// Cor do ponto do indicador de saúde do FIWARE
export const COR_SAUDE = {
  verificando: 'bg-taupe',
  online: 'bg-ok',
  offline: 'bg-alerta',
  sem_backend: 'bg-alerta',
};

// Cor da faixa esquerda de cada toast
export const BORDA_TOAST = {
  alerta: 'border-l-alerta',
  fiware_offline: 'border-l-alerta',
  offline: 'border-l-taupe',
  normal: 'border-l-ok',
  fiware_online: 'border-l-ok',
};

// Ícone de cada toast
export const ICONE_TOAST = {
  alerta: TriangleAlert,
  offline: WifiOff,
  normal: CircleCheck,
  fiware_offline: ServerCrash,
  fiware_online: Server,
};
```

- [ ] **Passo 6: substituir `ui/base.jsx` inteiro**

```jsx
/**
 * Peças de texto do design system: rótulo em caixa alta (Overline), título
 * e subtítulo em serifa bordô, texto secundário, mensagem de erro e links
 * internos. Antes de escrever um destes à mão numa tela, use o daqui.
 */
import { CircleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';

/** Rótulo curto em caixa alta espaçada. `icone` é um componente Lucide; `invertido` para fundo bordô. */
export function Overline({ icone: Icone, invertido = false, children }) {
  const cor = invertido ? 'text-papel/80' : 'text-taupe';
  return (
    <p className={`flex items-center gap-1.5 text-overline uppercase ${cor}`}>
      {Icone && <Icone size={14} strokeWidth={1.5} aria-hidden="true" />}
      {children}
    </p>
  );
}

/** Título de página em serifa bordô, com `overline` opcional acima. */
export function Titulo({ overline, children }) {
  return (
    <div className="mb-6">
      {overline && <Overline>{overline}</Overline>}
      <h1 className="mt-1 font-display text-titulo text-bordo">{children}</h1>
    </div>
  );
}

/** Subtítulo de seção ou de cartão. */
export function Subtitulo({ children }) {
  return <h2 className="mb-4 font-display text-subtitulo text-bordo">{children}</h2>;
}

/** Texto secundário: avisos, "Carregando…". */
export function Nota({ children }) {
  return <p className="text-taupe">{children}</p>;
}

/** Mensagem de erro com ícone; não desenha nada quando `erro` está vazio. */
export function MensagemErro({ erro }) {
  if (!erro) {
    return null;
  }
  return (
    <p className="mb-2 flex basis-full items-start gap-1.5 text-sm text-alerta" role="alert">
      <CircleAlert size={16} strokeWidth={1.5} className="mt-0.5 shrink-0" aria-hidden="true" />
      {erro}
    </p>
  );
}

/** Link interno (React Router, sem recarregar a página) no estilo da marca. */
export function LinkInterno({ to, children }) {
  return (
    <Link to={to} className="text-bordo underline-offset-4 hover:underline focus-visible:underline">
      {children}
    </Link>
  );
}

/** Link para o detalhe de uma vinheria. */
export function LinkVinheria({ deviceId, children }) {
  return <LinkInterno to={`/vinherias/${deviceId}`}>{children}</LinkInterno>;
}
```

- [ ] **Passo 7: substituir `ui/formulario.jsx` inteiro**

```jsx
/**
 * Peças de formulário do design system: campo com rótulo, botão com
 * variantes e botão só de ícone. Todos têm pelo menos 44 px de altura,
 * para o toque no celular. Em React 19, `ref` chega como prop comum e
 * vai junto do `...props` para o elemento nativo.
 */

// Cores de cada variante do Botao (classes inteiras para o Tailwind achar)
const VARIANTES = {
  primario: 'border-bordo bg-bordo text-papel hover:bg-vinho hover:border-vinho',
  secundario: 'border-bordo bg-transparent text-bordo hover:bg-bordo/8',
  perigo: 'border-alerta bg-transparent text-alerta hover:bg-alerta/8',
};

/** Campo de texto com o rótulo em caixa alta em cima; as demais props vão para o <input>. */
export function Campo({ rotulo, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-overline uppercase text-taupe">{rotulo}</span>
      <input
        className="min-h-11 rounded border border-linha bg-papel px-3 text-vinho placeholder:text-taupe/70 focus:border-bordo"
        {...props}
      />
    </label>
  );
}

/** Botão padrão. Com `carregando`, fica desabilitado e mostra `textoCarregando`. */
export function Botao({
  variante = 'primario',
  carregando = false,
  textoCarregando,
  disabled,
  type = 'button',
  className = '',
  children,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || carregando}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded border px-4 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTES[variante]} ${className}`}
      {...props}
    >
      {carregando && textoCarregando ? textoCarregando : children}
    </button>
  );
}

/** Botão só de ícone (Lucide), redondo, 44 px; `rotulo` vira o nome acessível. */
export function BotaoIcone({ icone: Icone, rotulo, className = '', ...props }) {
  return (
    <button
      type="button"
      aria-label={rotulo}
      title={rotulo}
      className={`inline-flex size-11 shrink-0 items-center justify-center rounded-full text-taupe transition-colors duration-150 hover:bg-bordo/8 hover:text-bordo ${className}`}
      {...props}
    >
      <Icone size={20} strokeWidth={1.5} aria-hidden="true" />
    </button>
  );
}
```

- [ ] **Passo 8: verificar**

```bash
npm test && npm run build   # 33 passed, build ok
```
No `npm run dev`, em `/dispositivos`:
- título em Playfair bordô;
- campos com rótulo em caixa alta;
- botões bordô sólidos (o Excluir também, até a 5B.9);
- o status da tabela ainda em texto (`COR_STATUS` agora traz fundo e borda; a tabela vira lista na 5B.9).

Cadastrar com o id `abc` mostra o erro com ícone.

- [ ] **Passo 9: commit**

```bash
git add frontend/src
git commit -m "feat: aplica a tipografia e as cores da marca nas pecas de texto e formulario"
```

---

## Subtarefa 5B.4 — Contagem animada (R6)

**Files:** criar `src/lib/contagem.js`, `src/lib/contagem.test.js`, `src/hooks/useContagem.js`.

**Produz:** `interpolar(de, para, progresso) -> number` e `useContagem(valor, duracaoMs = 450) -> number | valor original`.

- [ ] **Passo 1: escrever o teste que falha, `src/lib/contagem.test.js`**

```js
/** Testes da interpolação usada na contagem animada dos números (spec R6.1). */
import { describe, expect, it } from 'vitest';
import { interpolar } from './contagem.js';

describe('interpolar', () => {
  it('devolve o valor inicial no começo e o final no fim', () => {
    expect(interpolar(0, 10, 0)).toBe(0);
    expect(interpolar(0, 10, 1)).toBe(10);
  });

  it('prende o progresso fora de 0..1', () => {
    expect(interpolar(0, 10, -1)).toBe(0);
    expect(interpolar(0, 10, 1.5)).toBe(10);
  });

  it('é ease-out: no meio do tempo já passou da metade', () => {
    expect(interpolar(0, 10, 0.5)).toBeCloseTo(8.75);
  });

  it('funciona com valores negativos (temperatura)', () => {
    expect(interpolar(-5, 5, 0.5)).toBeCloseTo(3.75);
  });

  it('com início igual ao fim devolve o fim', () => {
    expect(interpolar(7, 7, 0.3)).toBe(7);
  });
});
```

- [ ] **Passo 2: rodar e ver falhar**

Rode `npm test -- contagem`. Esperado: FAIL, porque o módulo não existe.

- [ ] **Passo 3: implementar `src/lib/contagem.js`**

```js
/**
 * Interpolação dos números que "contam" até o valor novo (valor de sensor,
 * score). Função pura, testada; o hook useContagem cuida do tempo.
 */

/** Valor entre `de` e `para` com easing ease-out cúbico; `progresso` vai de 0 a 1. */
export function interpolar(de, para, progresso) {
  if (de === para || progresso >= 1) {
    return para;
  }
  if (progresso <= 0) {
    return de;
  }
  const curva = 1 - (1 - progresso) ** 3;
  return de + (para - de) * curva;
}
```

- [ ] **Passo 4: rodar e ver passar**

Rode `npm test`. Esperado: 38 passed.

- [ ] **Passo 5: criar `src/hooks/useContagem.js`**

```js
/**
 * Hook da contagem animada: quando `valor` muda, devolve números
 * intermediários a cada quadro (requestAnimationFrame) até chegar nele.
 * Na primeira vez conta a partir de 0. Devolve `valor` direto quando ele
 * não é número (null vira "—" na tela) ou quando o sistema pede menos
 * movimento (prefers-reduced-motion).
 */
import { useEffect, useRef, useState } from 'react';
import { interpolar } from '../lib/contagem.js';

function prefereMenosMovimento() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

export function useContagem(valor, duracaoMs = 450) {
  const numerico = typeof valor === 'number' && Number.isFinite(valor);
  const [exibido, setExibido] = useState(numerico ? 0 : valor);
  // Último número mostrado: a próxima animação parte dele
  const ultimo = useRef(0);

  useEffect(() => {
    if (!numerico || prefereMenosMovimento()) {
      setExibido(valor);
      if (numerico) {
        ultimo.current = valor;
      }
      return undefined;
    }
    const de = ultimo.current;
    const inicio = performance.now();
    let quadro;
    function passo(agora) {
      const progresso = (agora - inicio) / duracaoMs;
      const atual = interpolar(de, valor, progresso);
      ultimo.current = atual;
      setExibido(atual);
      if (progresso < 1) {
        quadro = requestAnimationFrame(passo);
      }
    }
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, [valor, numerico, duracaoMs]);

  return exibido;
}
```

- [ ] **Passo 6: verificar**

```bash
npm test && npm run build   # 38 passed, build ok
```
O hook ainda não é usado em tela. A conferência visual fica na 5B.5.

- [ ] **Passo 7: commit**

```bash
git add frontend/src/lib/contagem.js frontend/src/lib/contagem.test.js frontend/src/hooks/useContagem.js
git commit -m "feat: adiciona a contagem animada dos numeros do painel"
```

---

## Subtarefa 5B.5 — Cartões, bento, selo, imagem reservada e estados (R4.2, R8)

**Files:** criar `ui/cartoes.jsx`, `ui/imagem.jsx`, `ui/estados.jsx`; modificar `ui/index.js`, `src/constants.js`.

**Consome:** `useContagem` (5B.4), `statusConhecido`, `COR_STATUS`, `ICONE_STATUS` (5B.3), `Overline` (5B.3).
**Produz:** `GradeBento({ children })`, `Cartao({ variante, larg, className, children })`, `CartaoKpi({ rotulo, icone, valor, unidade, rodape, variante, larg })`, `SeloStatus({ status })`, `Logo({ src })`, `ImagemReservada({ proporcao, rotulo, src, alt, className })`, `Heroi({ titulo, subtitulo, imagem })`, `EstadoVazio({ titulo, texto, acao })`, `Esqueleto({ className })`, constantes `LOGO_SRC`, `IMAGEM_HEROI`.

- [ ] **Passo 1: acrescentar ao fim de `src/constants.js`**

```js
// Imagens enviadas pelo usuário depois (Task 5B, spec R8): caminho do
// arquivo em frontend/public (ex.: '/logo.svg') ou null enquanto não chegam
export const LOGO_SRC = null;
export const IMAGEM_HEROI = null;
```

- [ ] **Passo 2: criar `ui/cartoes.jsx`**

```jsx
/**
 * Peças de painel no estilo bento (referência B, nas cores da referência A):
 * grade, cartão, cartão de indicador (KPI) e selo de status de vinheria.
 * A Task 6 monta a Visão geral e o detalhe só com estas peças.
 */
import { STATUS_ROTULO } from '../../constants.js';
import { COR_STATUS, ICONE_STATUS } from '../../estilo.js';
import { useContagem } from '../../hooks/useContagem.js';
import { statusConhecido } from '../../lib/status.js';
import { Overline } from './base.jsx';

// Quantas colunas o item ocupa: 2 no md e até 4 no lg (classes inteiras para o Tailwind achar)
const LARGURA = {
  1: '',
  2: 'md:col-span-2',
  3: 'md:col-span-2 lg:col-span-3',
  4: 'md:col-span-2 lg:col-span-4',
};

/** Grade bento: 1 coluna no celular, 2 no md, 4 no lg. Os filhos se entregam em cascata. */
export function GradeBento({ children }) {
  return <div className="cascata grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 lg:grid-cols-4">{children}</div>;
}

/** Cartão do bento. `destaque` = fundo bordô sólido (o cartão vermelho da referência B). */
export function Cartao({ variante = 'padrao', larg = 1, className = '', children }) {
  const cores = variante === 'destaque' ? 'border-bordo bg-bordo text-papel' : 'border-linha bg-papel';
  return (
    <section className={`min-w-0 animate-entrar rounded-2xl border p-4 shadow-baixa md:p-6 ${cores} ${LARGURA[larg]} ${className}`}>
      {children}
    </section>
  );
}

/** Formata o número com as casas do valor final (inteiro fica inteiro, decimal com 1 casa). */
function formatar(numero, valorFinal) {
  const casas = Number.isInteger(valorFinal) ? 0 : 1;
  return numero.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

/** Cartão de indicador: rótulo com ícone, número grande em serifa que conta até o valor, unidade e rodapé. */
export function CartaoKpi({ rotulo, icone, valor, unidade, rodape, variante = 'padrao', larg = 1 }) {
  const exibido = useContagem(valor);
  const invertido = variante === 'destaque';
  const temNumero = typeof exibido === 'number';
  return (
    <Cartao variante={variante} larg={larg}>
      <Overline icone={icone} invertido={invertido}>{rotulo}</Overline>
      <p className="mt-3 font-display text-titulo tabular-nums">
        {temNumero ? formatar(exibido, valor) : '—'}
        {temNumero && unidade && <span className="ml-1 font-sans text-base">{unidade}</span>}
      </p>
      {rodape && <p className={`mt-2 text-sm ${invertido ? 'text-papel/80' : 'text-taupe'}`}>{rodape}</p>}
    </Cartao>
  );
}

/** Selo de status de uma vinheria: ícone + texto + cor. Em alerta, o ícone pulsa. */
export function SeloStatus({ status }) {
  const chave = statusConhecido(status);
  const Icone = ICONE_STATUS[chave];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${COR_STATUS[chave]}`}>
      <Icone size={14} strokeWidth={1.75} aria-hidden="true" className={chave === 'alerta' ? 'animate-pulsar' : ''} />
      {STATUS_ROTULO[chave]}
    </span>
  );
}
```

- [ ] **Passo 3: criar `ui/imagem.jsx`**

```jsx
/**
 * Imagens do painel. Nesta fase as fotos ainda não chegaram (spec R8):
 * cada lugar de imagem é um espaço reservado com proporção fixa, então a
 * foto real entra só passando `src` e `alt`, sem a página "pular".
 */

// Proporção de cada uso (classes inteiras para o Tailwind achar)
const PROPORCAO = {
  quadrada: 'aspect-square',
  '4/3': 'aspect-[4/3]',
  heroi: 'aspect-[4/3] md:aspect-[21/9]',
};

/** Logo da Smart Solutions; sem imagem, o nome em serifa bordô faz o papel de logo. */
export function Logo({ src }) {
  if (src) {
    return <img src={src} alt="Smart Solutions" className="h-8 w-auto" />;
  }
  return <span className="font-display text-xl whitespace-nowrap text-bordo">Smart Solutions</span>;
}

/** Imagem com proporção fixa; sem `src`, desenha um gradiente da marca com o `rotulo` no canto. */
export function ImagemReservada({ proporcao = '4/3', rotulo, src, alt = '', className = '' }) {
  if (src) {
    return <img src={src} alt={alt} loading="lazy" className={`w-full object-cover ${PROPORCAO[proporcao]} ${className}`} />;
  }
  return (
    <div
      role="img"
      aria-label={rotulo}
      className={`flex w-full items-start justify-end bg-linear-to-br from-bordo via-rose to-creme p-3 ${PROPORCAO[proporcao]} ${className}`}
    >
      <span className="text-overline uppercase text-papel/80">{rotulo}</span>
    </div>
  );
}

/** Herói da Visão geral (referência A): imagem larga com título display por cima e véu escuro para leitura. */
export function Heroi({ titulo, subtitulo, imagem }) {
  return (
    <section className="relative mb-8 animate-entrar overflow-hidden rounded-2xl shadow-media">
      <ImagemReservada proporcao="heroi" rotulo="imagem do vinhedo" src={imagem} alt="" />
      <div className="absolute inset-0 flex flex-col justify-end bg-linear-to-t from-vinho/85 via-bordo/40 to-transparent p-5 md:p-10">
        <h1 className="font-display text-display text-papel">{titulo}</h1>
        <p className="mt-2 max-w-md text-papel/90">{subtitulo}</p>
      </div>
    </section>
  );
}
```

- [ ] **Passo 4: criar `ui/estados.jsx`**

```jsx
/**
 * Estados de tela sem conteúdo: vazio (nada a mostrar, com ação opcional)
 * e esqueleto (carregando), no lugar de spinner solto.
 */

/** Bloco central para lista vazia, tela em construção ou 404. `acao` é um botão ou link opcional. */
export function EstadoVazio({ titulo, texto, acao }) {
  return (
    <div className="flex animate-entrar flex-col items-center gap-3 rounded-2xl border border-dashed border-linha px-6 py-12 text-center">
      <p className="font-display text-subtitulo text-bordo">{titulo}</p>
      {texto && <p className="max-w-sm text-taupe">{texto}</p>}
      {acao}
    </div>
  );
}

/** Bloco de carregamento com brilho lento; a altura vem do `className` (ex.: "h-14"). */
export function Esqueleto({ className = '' }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-brilho rounded-lg bg-linear-to-r from-linha via-papel to-linha bg-size-[200%_100%] ${className}`}
    />
  );
}
```

- [ ] **Passo 5: acrescentar a `ui/index.js`**

```js
export * from './cartoes.jsx';
export * from './imagem.jsx';
export * from './estados.jsx';
```

- [ ] **Passo 6: verificar**

Rode `npm test && npm run build`. Esperado: 38 passed e build ok.

Conferência visual temporária (não commitar): em `pages/Placeholder.jsx`, coloque por um minuto este bloco depois do `<Nota>`:
```jsx
<GradeBento>
  <CartaoKpi rotulo="Temperatura" valor={-2.5} unidade="°C" rodape="faixa 12–18 °C" />
  <CartaoKpi rotulo="Umidade" valor={null} unidade="%" />
  <CartaoKpi rotulo="Score" valor={87} variante="destaque" larg={2} />
  <Cartao larg={4}><SeloStatus status="alerta" /> <SeloStatus status="xyz" /> <Esqueleto className="mt-3 h-10" /></Cartao>
</GradeBento>
```
Com os imports correspondentes. Abra `/alertas` e confira:
- os números contam a partir de 0, e o `-2,5` chega com vírgula;
- a umidade mostra `—`;
- o cartão destaque é bordô com texto creme;
- o selo de alerta pulsa e o `xyz` aparece como "Aguardando 1º ciclo";
- em 375 px os cartões empilham; em 768 px ficam 2 por linha; em 1024 px ficam 4.

Depois, desfaça a conferência (`git checkout frontend/src/pages/Placeholder.jsx`).

- [ ] **Passo 7: commit**

```bash
git add frontend/src/constants.js frontend/src/components/ui
git commit -m "feat: adiciona cartoes bento, selo de status, imagem reservada e estados vazios"
```

---

## Subtarefa 5B.6 — Menu único, barra inferior e selo de atenção (R2.4, R2.5, R2.6)

**Files:** modificar `src/lib/fleetEvents.js`, `src/lib/fleetEvents.test.js`, `src/App.jsx`; criar `src/navegacao.js`, `src/components/MenuTopo.jsx`, `src/components/NavInferior.jsx`.

**Produz:** `contarAtencao(frota) -> number`, `MENU` (array de `{ to, rotulo, icone, contaAtencao? }`), `<MenuTopo />`, `<NavInferior />`.

- [ ] **Passo 1: escrever os testes que falham, acrescentando ao fim de `src/lib/fleetEvents.test.js`.** Some `contarAtencao` ao import de `./fleetEvents.js` que já existe no topo do arquivo.

```js
describe('contarAtencao', () => {
  // Vinheria mínima para os testes do selo do menu
  const v = (device_id, status, offline_reason = null) => ({ device_id, name: device_id, status, offline_reason });

  it('sem frota carregada devolve 0', () => {
    expect(contarAtencao(null)).toBe(0);
  });

  it('conta vinherias em alerta e offline por falta de leitura', () => {
    const frota = {
      fiware_online: true,
      vinherias: [v('vinheria001', 'alerta'), v('vinheria002', 'offline', 'sem_leitura'), v('vinheria003', 'ok')],
    };
    expect(contarAtencao(frota)).toBe(2);
  });

  it('com a EC2 fora não conta as vinherias offline por causa dela', () => {
    const frota = {
      fiware_online: false,
      vinherias: [v('vinheria001', 'offline', 'fiware'), v('vinheria002', 'offline', 'fiware')],
    };
    expect(contarAtencao(frota)).toBe(0);
  });
});
```

- [ ] **Passo 2: rodar e ver falhar**

Rode `npm test -- fleetEvents`. Esperado: FAIL com `contarAtencao is not a function` (ou um erro de import).

- [ ] **Passo 3: implementar, acrescentando ao fim de `src/lib/fleetEvents.js`**

```js
/**
 * Quantas vinherias pedem atenção (em alerta ou offline por falta de
 * leitura), para o selo do item Alertas no menu. Usa as mesmas regras da
 * faixa (bannerSummary): a queda da EC2 aparece na faixa, não no selo.
 */
export function contarAtencao(frota) {
  const resumo = bannerSummary(frota);
  return resumo ? resumo.emAlerta.length + resumo.offline.length : 0;
}
```

- [ ] **Passo 4: rodar e ver passar**

Rode `npm test`. Esperado: 41 passed.

- [ ] **Passo 5: criar `src/navegacao.js`**

```js
/**
 * Itens do menu do painel, compartilhados pelo menu do topo (desktop) e
 * pela barra inferior (celular), para os dois nunca divergirem.
 * `contaAtencao` marca o item que mostra o selo com o número de vinherias
 * em alerta ou offline.
 */
import { BellRing, Cpu, LayoutGrid, MessageCircle } from 'lucide-react';

export const MENU = [
  { to: '/', rotulo: 'Visão geral', icone: LayoutGrid },
  { to: '/dispositivos', rotulo: 'Dispositivos', icone: Cpu },
  { to: '/alertas', rotulo: 'Alertas', icone: BellRing, contaAtencao: true },
  { to: '/chat', rotulo: 'Chat', icone: MessageCircle },
];
```

- [ ] **Passo 6: criar `src/components/MenuTopo.jsx`**

```jsx
/**
 * Menu do topo, só a partir de 768 px (no celular quem navega é a
 * NavInferior). O item ativo fica bordô e sublinhado, como na referência A.
 */
import { NavLink } from 'react-router-dom';
import { MENU } from '../navegacao.js';

function classeDoItem({ isActive }) {
  const cor = isActive ? 'text-bordo underline' : 'text-taupe hover:text-bordo';
  return `flex min-h-11 items-center text-sm decoration-2 underline-offset-8 ${cor}`;
}

export default function MenuTopo() {
  return (
    <nav aria-label="Navegação principal" className="hidden items-center gap-6 md:flex">
      {MENU.map(({ to, rotulo }) => (
        <NavLink key={to} to={to} end={to === '/'} className={classeDoItem}>
          {rotulo}
        </NavLink>
      ))}
    </nav>
  );
}
```

- [ ] **Passo 7: criar `src/components/NavInferior.jsx`**

```jsx
/**
 * Barra de navegação inferior do celular (abaixo de 768 px): quatro ícones
 * com rótulo ao alcance do polegar. O item Alertas mostra quantas vinherias
 * pedem atenção, contadas do FleetContext (sem chamada HTTP nova).
 */
import { NavLink } from 'react-router-dom';
import { useFleet } from '../context/FleetContext.jsx';
import { contarAtencao } from '../lib/fleetEvents.js';
import { MENU } from '../navegacao.js';

function classeDoItem({ isActive }) {
  const cor = isActive ? 'border-bordo text-bordo' : 'border-transparent text-taupe';
  return `relative flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 border-t-2 text-xs font-medium ${cor}`;
}

export default function NavInferior() {
  const { fleet } = useFleet();
  const atencao = contarAtencao(fleet);

  return (
    <nav
      aria-label="Navegação principal"
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-linha bg-papel pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      {MENU.map(({ to, rotulo, icone: Icone, contaAtencao }) => (
        <NavLink key={to} to={to} end={to === '/'} className={classeDoItem}>
          <Icone size={22} strokeWidth={1.5} aria-hidden="true" />
          {rotulo}
          {contaAtencao && atencao > 0 && (
            <span className="absolute top-1.5 left-1/2 ml-2 min-w-5 rounded-full bg-alerta px-1 text-center leading-5 text-papel">
              {atencao}
              <span className="sr-only"> vinherias precisam de atenção</span>
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
```

- [ ] **Passo 8: substituir o `App.jsx`** (some o `<nav>` antigo, o `MENU` local e `classeDoMenu`; entra a `NavInferior`; o `<main>` ganha largura máxima e recuo para a barra inferior; a rota `/` ganha a prop `heroi`, usada na 5B.10)

```jsx
/**
 * Layout e rotas do painel Smart Solutions.
 *
 * Rotas: / Visão geral · /vinherias/:id Detalhe · /alertas · /dispositivos
 * · /chat. As telas das Tasks 6 e 7A ainda são Placeholder.
 * A troca de página é sempre pelo react-router-dom (NavLink/Link/useNavigate),
 * sem recarregar: os toasts e o polling da frota continuam vivos.
 * Navegação: menu na barra do topo a partir de 768 px (FiwareBar) e barra
 * inferior abaixo disso (NavInferior); os dois leem o mesmo MENU.
 */
import { Route, Routes } from 'react-router-dom';
import AlertBanner from './components/AlertBanner.jsx';
import FiwareBar from './components/FiwareBar.jsx';
import NavInferior from './components/NavInferior.jsx';
import { ConfigProvider } from './context/ConfigContext.jsx';
import { FleetProvider } from './context/FleetContext.jsx';
import Devices from './pages/Devices.jsx';
import Placeholder from './pages/Placeholder.jsx';

export default function App() {
  return (
    <ConfigProvider>
      <FleetProvider>
        <FiwareBar />
        <AlertBanner />
        <main className="mx-auto w-full max-w-pagina px-4 pt-6 pb-28 md:px-6 md:pt-10 md:pb-16">
          <Routes>
            <Route path="/" element={<Placeholder titulo="Visão geral" task="Task 6" heroi />} />
            <Route path="/vinherias/:id" element={<Placeholder titulo="Detalhe da vinheria" task="Task 6" />} />
            <Route path="/alertas" element={<Placeholder titulo="Alertas" task="Task 6" />} />
            <Route path="/dispositivos" element={<Devices />} />
            <Route path="/chat" element={<Placeholder titulo="Chat" task="Task 7A" />} />
            <Route path="*" element={<Placeholder titulo="Página não encontrada" />} />
          </Routes>
        </main>
        <NavInferior />
      </FleetProvider>
    </ConfigProvider>
  );
}
```

- [ ] **Passo 9: plugar o `MenuTopo` no `FiwareBar`, de forma provisória.** Importe `MenuTopo` e coloque `<MenuTopo />` logo antes do `<details>`. A 5B.7 reescreve a barra inteira.

- [ ] **Passo 10: verificar**

```bash
npm test && npm run build   # 41 passed, build ok
```
No navegador, com o DevTools em modo dispositivo:
- **375 px:** barra inferior com 4 ícones; o ativo é bordô com traço no topo; a última linha do conteúdo não fica escondida atrás da barra. Com o Wokwi da `vinheria002` offline, o item Alertas mostra o selo "1".
- **768 px ou mais:** a barra inferior some, e o menu aparece no topo com o ativo sublinhado.
- **Voltar/Avançar** do navegador trocam a página sem recarregar.

- [ ] **Passo 11: commit**

```bash
git add frontend/src
git commit -m "feat: adiciona a barra de navegacao inferior no celular e o menu unico"
```

---

## Subtarefa 5B.7 — Barra superior e painel Avançado (R2.1–R2.3)

**Files:** criar `src/components/PainelAvancado.jsx`; substituir `src/components/FiwareBar.jsx`.

**Consome:** `useConfig()` → `{ config, health, healthState, salvarIp }` (5A), `Logo` (5B.5), `BotaoIcone`, `Campo`, `Botao`, `MensagemErro`, `Overline` (5B.3), `MenuTopo` (5B.6), `LOGO_SRC` (5B.5), `COR_SAUDE` (5B.3).

- [ ] **Passo 1: criar `src/components/PainelAvancado.jsx`** (lógica idêntica à do `<details>` da 5A; só muda o lugar e o visual)

```jsx
/**
 * Painel "Avançado" aberto pela engrenagem da barra superior: troca do IP
 * do FIWARE (EC2) em runtime e resultado do health de cada serviço. O IP
 * padrão vem do .env do backend (IP elástico); este é o único lugar onde
 * ele pode ser trocado. Ao abrir, o foco vai para o campo do IP.
 */
import { useEffect, useRef, useState } from 'react';
import { useConfig } from '../context/ConfigContext.jsx';
import { useAcao } from '../hooks/useAcao.js';
import { Botao, Campo, MensagemErro, Overline } from './ui/index.js';

const SERVICOS = [
  ['orion', 'Orion'],
  ['iota', 'IoT Agent'],
  ['sth', 'STH-Comet'],
];

/** Texto do resultado de um serviço no health. */
function descreverServico(servico) {
  if (servico.ok) {
    return `ok (${servico.latency_ms} ms)`;
  }
  return servico.error ? `falhou — ${servico.error}` : 'falhou';
}

export default function PainelAvancado() {
  const { config, health, salvarIp } = useConfig();
  const [ip, setIp] = useState('');
  const [salvo, setSalvo] = useState(null);
  const salvar = useAcao(salvarIp);
  const campo = useRef(null);

  useEffect(() => {
    campo.current?.focus();
  }, []);

  async function aoSalvar(evento) {
    evento.preventDefault();
    setSalvo(null);
    const resultado = await salvar.executar(ip);
    if (resultado.ok) {
      setSalvo(`IP salvo: ${resultado.valor.ec2_ip}`);
      setIp('');
    }
  }

  return (
    <div
      id="painel-avancado"
      className="animate-entrar border-t border-linha bg-papel px-4 py-4 shadow-media md:absolute md:top-full md:right-6 md:w-90 md:rounded-2xl md:border"
    >
      <Overline>FIWARE na EC2</Overline>
      <form onSubmit={aoSalvar} className="mt-3 flex flex-col gap-3">
        <Campo
          ref={campo}
          rotulo="IP do FIWARE (EC2)"
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          placeholder={config?.ec2_ip ?? ''}
          required
        />
        <Botao type="submit" carregando={salvar.executando} textoCarregando="Salvando…">
          Salvar
        </Botao>
      </form>
      <div className="mt-2">
        <MensagemErro erro={salvar.erro} />
      </div>
      {salvo && <p role="status" className="text-sm text-ok">{salvo}</p>}
      {health && (
        <ul className="mt-3 space-y-1 border-t border-linha pt-3 text-sm">
          {SERVICOS.map(([chave, nome]) => (
            <li key={chave} className="flex justify-between gap-3">
              <span>{nome}</span>
              <span className="text-right font-mono text-xs text-taupe">{descreverServico(health[chave])}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Passo 2: substituir `src/components/FiwareBar.jsx` inteiro**

```jsx
/**
 * Barra fixa do topo: logo Smart Solutions, indicador de saúde do FIWARE
 * (com o IP em uso a partir de 768 px), menu do desktop e a engrenagem que
 * abre o painel Avançado. O painel fecha pela engrenagem ou pela tecla Esc,
 * e o foco volta para a engrenagem.
 */
import { Settings } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { LOGO_SRC } from '../constants.js';
import { useConfig } from '../context/ConfigContext.jsx';
import { COR_SAUDE } from '../estilo.js';
import MenuTopo from './MenuTopo.jsx';
import PainelAvancado from './PainelAvancado.jsx';
import { BotaoIcone, Logo } from './ui/index.js';

const ROTULO = {
  verificando: 'Verificando FIWARE…',
  online: 'FIWARE online',
  offline: 'FIWARE fora do ar',
  sem_backend: 'Backend indisponível',
};

/** Ponto colorido + texto; no celular só "FIWARE", para caber na barra. */
function SeloSaude({ estado, ip }) {
  return (
    <span className="flex items-center gap-2 text-sm" title={ROTULO[estado]}>
      <span className={`size-2.5 shrink-0 rounded-full ${COR_SAUDE[estado]}`} aria-hidden="true" />
      <span className="md:hidden">
        FIWARE<span className="sr-only">: {ROTULO[estado]}</span>
      </span>
      <span className="hidden md:inline">
        {ROTULO[estado]}
        {ip && <span className="ml-2 font-mono text-xs text-taupe">{ip}</span>}
      </span>
    </span>
  );
}

export default function FiwareBar() {
  const { config, healthState } = useConfig();
  const [aberto, setAberto] = useState(false);
  const engrenagem = useRef(null);

  const fechar = useCallback(() => {
    setAberto(false);
    engrenagem.current?.focus();
  }, []);

  // Esc fecha o painel enquanto ele estiver aberto
  useEffect(() => {
    if (!aberto) {
      return undefined;
    }
    function aoTeclar(evento) {
      if (evento.key === 'Escape') {
        fechar();
      }
    }
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [aberto, fechar]);

  return (
    <header className="sticky top-0 z-30 border-b border-linha bg-papel">
      <div className="mx-auto flex min-h-14 max-w-pagina items-center gap-3 px-4 md:gap-6 md:px-6">
        <Logo src={LOGO_SRC} />
        <SeloSaude estado={healthState} ip={config?.ec2_ip} />
        <div className="ml-auto flex items-center gap-4">
          <MenuTopo />
          <BotaoIcone
            ref={engrenagem}
            icone={Settings}
            rotulo="Configurações avançadas"
            aria-expanded={aberto}
            aria-controls="painel-avancado"
            onClick={() => (aberto ? fechar() : setAberto(true))}
          />
        </div>
      </div>
      {aberto && <PainelAvancado />}
    </header>
  );
}
```

- [ ] **Passo 3: verificar**

```bash
npm test && npm run build      # 41 passed, build ok
wc -l src/components/FiwareBar.jsx src/components/PainelAvancado.jsx   # cada um < 250
```
No navegador:
- **375 px:** logo, ponto + "FIWARE" e a engrenagem cabem numa linha. A engrenagem abre o painel em largura total sob a barra, com o foco no campo do IP.
- **1024 px:** o painel abre como caixa de 360 px à direita, e o IP aparece em mono ao lado de "FIWARE online".
- Esc fecha o painel e o foco volta à engrenagem.
- **Comportamento da 5A:** salvar um IP inválido deixa o ponto vermelho em até 30 s; voltar para `3.215.3.216` deixa verde. Precisa da EC2 ligada; se ela estiver desligada, registre a pendência.

- [ ] **Passo 4: commit**

```bash
git add frontend/src/components/FiwareBar.jsx frontend/src/components/PainelAvancado.jsx
git commit -m "feat: aplica o visual da marca na barra superior e no painel avancado"
```

---

## Subtarefa 5B.8 — Faixa de aviso e toasts (R3)

**Files:** substituir `src/components/AlertBanner.jsx`.

**Consome:** `useFleet()` → `{ fleet, toasts, fecharToast }`, `bannerSummary`, `textoDoEvento`, `contarAtencao` (5B.6), `BORDA_TOAST`, `ICONE_TOAST` (5B.3), `BotaoIcone`, `LinkVinheria`.

- [ ] **Passo 1: substituir `src/components/AlertBanner.jsx` inteiro**

```jsx
/**
 * Aviso global (RF14): faixa fixa enquanto houver vinheria em alerta ou
 * offline (ou a EC2 fora do ar) e toasts empilhados, um por evento, com
 * link para o detalhe da vinheria. Os toasts só somem quando fechados.
 * No celular, a faixa abre com um resumo ("2 vinherias precisam de
 * atenção") e os toasts ficam acima da barra de navegação inferior.
 */
import { TriangleAlert, X } from 'lucide-react';
import { Fragment } from 'react';
import { useFleet } from '../context/FleetContext.jsx';
import { BORDA_TOAST, ICONE_TOAST } from '../estilo.js';
import { bannerSummary, contarAtencao, textoDoEvento } from '../lib/fleetEvents.js';
import { BotaoIcone, LinkVinheria } from './ui/index.js';

/** Nomes das vinherias separados por vírgula, cada um com link para o detalhe. */
function listaDeLinks(vinherias) {
  return vinherias.map((v, indice) => (
    <Fragment key={v.device_id}>
      {indice > 0 && ', '}
      <LinkVinheria deviceId={v.device_id}>{v.name}</LinkVinheria>
    </Fragment>
  ));
}

/** Frase de resumo do celular. */
function resumoCurto(total) {
  return total === 1 ? '1 vinheria precisa de atenção' : `${total} vinherias precisam de atenção`;
}

export default function AlertBanner() {
  const { fleet, toasts, fecharToast } = useFleet();
  const resumo = bannerSummary(fleet);
  const total = contarAtencao(fleet);

  return (
    <>
      {resumo?.visivel && (
        <div className="border-b border-alerta bg-alerta/8" role="alert">
          <div className="mx-auto flex max-w-pagina flex-wrap items-start gap-x-4 gap-y-1 px-4 py-2.5 text-sm md:px-6">
            <TriangleAlert size={18} strokeWidth={1.75} className="mt-0.5 shrink-0 text-alerta" aria-hidden="true" />
            {resumo.fiwareOffline && (
              <span className="font-medium">EC2/FIWARE fora do ar: todas as vinherias offline.</span>
            )}
            {!resumo.fiwareOffline && <span className="font-medium md:hidden">{resumoCurto(total)}</span>}
            {resumo.emAlerta.length > 0 && (
              <span className="basis-full md:basis-auto">Em alerta: {listaDeLinks(resumo.emAlerta)}</span>
            )}
            {resumo.offline.length > 0 && (
              <span className="basis-full md:basis-auto">Offline: {listaDeLinks(resumo.offline)}</span>
            )}
          </div>
        </div>
      )}
      <div
        className="fixed inset-x-4 bottom-20 z-40 flex flex-col gap-2 md:inset-x-auto md:right-6 md:bottom-6 md:w-96"
        aria-live="polite"
      >
        {toasts.map((toast) => {
          const Icone = ICONE_TOAST[toast.tipo];
          return (
            <div
              key={toast.id}
              className={`flex animate-entrar items-center gap-3 rounded-lg border border-l-4 border-linha bg-papel py-1 pl-3 text-sm shadow-media ${BORDA_TOAST[toast.tipo]}`}
            >
              <Icone size={18} strokeWidth={1.5} className="shrink-0" aria-hidden="true" />
              <span className="min-w-0 flex-1">
                {textoDoEvento(toast)}{' '}
                {toast.device_id && <LinkVinheria deviceId={toast.device_id}>Ver detalhe</LinkVinheria>}
              </span>
              <BotaoIcone icone={X} rotulo="Fechar aviso" onClick={() => fecharToast(toast.id)} />
            </div>
          );
        })}
      </div>
    </>
  );
}
```

- [ ] **Passo 2: verificar**

Rode `npm test && npm run build`. Esperado: 41 passed e build ok. Com o backend, a EC2 e o Wokwi ligados:
- Com a `vinheria002` offline (já está), a faixa aparece com fundo rosado claro e ícone.
  - Em 375 px: "1 vinheria precisa de atenção" e, na linha de baixo, "Offline: Vinheria Mineira" com link.
  - Em 1024 px: tudo numa linha.
- Parar o Wokwi da `vinheria001` faz aparecer, em até ~35 s, um toast com faixa taupe e ícone de wifi cortado. Em 375 px ele fica acima da barra inferior. O X (44 px) fecha.
- Trocar o IP para um inválido no Avançado faz aparecer um toast de EC2 fora e a faixa "EC2/FIWARE fora do ar". O selo do menu não conta as vinherias.

- [ ] **Passo 3: commit**

```bash
git add frontend/src/components/AlertBanner.jsx
git commit -m "feat: aplica o visual da marca na faixa de aviso e nos toasts"
```

---

## Subtarefa 5B.9 — Tela Dispositivos (R7.1–R7.3)

**Files:** modificar `src/pages/Devices.jsx`, `src/components/DeviceForm.jsx`, `src/components/DeviceList.jsx`.

**Consome:** `GradeBento`, `Cartao`, `Subtitulo`, `Titulo`, `Esqueleto`, `EstadoVazio`, `SeloStatus`, `Botao` (variante `perigo`), `statusConhecido`.

- [ ] **Passo 1: `DeviceForm.jsx`, trocar só o `return`** (lógica, `CAMPOS` e validação ficam iguais)

```jsx
  return (
    <form className="flex flex-col gap-4" onSubmit={aoEnviar}>
      {CAMPOS.map(([nome, rotulo, exemplo, maximo]) => (
        <Campo
          key={nome}
          rotulo={rotulo}
          name={nome}
          value={campos[nome]}
          onChange={alterar}
          placeholder={exemplo}
          maxLength={maximo}
        />
      ))}
      <MensagemErro erro={cadastrar.erro} />
      <Botao type="submit" className="w-full" carregando={cadastrar.executando} textoCarregando="Provisionando no FIWARE…">
        Cadastrar vinheria
      </Botao>
    </form>
  );
```

- [ ] **Passo 2: `DeviceList.jsx`, substituir inteiro**

```jsx
/**
 * Lista das vinherias cadastradas (RF02) com o status vindo da frota e o
 * botão de remover. A remoção apaga o cadastro local, o device no IoT Agent
 * e a entidade no Orion; o histórico do STH-Comet é mantido.
 *
 * Uma única marcação para todos os tamanhos: no celular cada vinheria é um
 * cartão empilhado; a partir de 768 px as mesmas linhas alinham em colunas
 * (CSS grid) sob um cabeçalho.
 */
import { useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { statusConhecido } from '../lib/status.js';
import { Botao, EstadoVazio, MensagemErro, SeloStatus } from './ui/index.js';

// Colunas a partir de md, iguais no cabeçalho e nas linhas: Id · Nome · Cidade · Status · ação
const COLUNAS = 'md:grid md:grid-cols-[8.5rem_minmax(0,1fr)_minmax(0,1fr)_10rem_auto] md:items-center md:gap-4';

const CABECALHO = ['Id', 'Nome', 'Cidade', 'Status', ''];

export default function DeviceList({ devices, statusPorId, onDeleted }) {
  // device_id em remoção, para o texto "Removendo…" sair só na linha certa
  const [removendo, setRemovendo] = useState(null);
  const excluir = useAcao(api.deleteDevice);

  async function remover(device) {
    const confirmado = window.confirm(
      `Remover ${device.name} (${device.device_id})?\n\n` +
        'Serão apagados o cadastro, o device no IoT Agent e a entidade no Orion. ' +
        'O histórico no STH-Comet é mantido.',
    );
    if (!confirmado) {
      return;
    }
    setRemovendo(device.device_id);
    const resultado = await excluir.executar(device.device_id);
    setRemovendo(null);
    if (resultado.ok) {
      await onDeleted(device.device_id);
    }
  }

  if (devices.length === 0) {
    return <EstadoVazio titulo="Nenhuma vinheria cadastrada" texto="Cadastre a primeira no formulário." />;
  }

  return (
    <>
      <MensagemErro erro={excluir.erro} />
      <div className={`hidden border-b border-linha pb-2 ${COLUNAS}`} aria-hidden="true">
        {CABECALHO.map((rotulo) => (
          <span key={rotulo || 'acao'} className="text-overline uppercase text-taupe">
            {rotulo}
          </span>
        ))}
      </div>
      <ul className="flex flex-col gap-3 md:gap-0">
        {devices.map((device) => {
          // Recém-cadastrada só entra na frota no próximo ciclo do poller
          const status = statusConhecido(statusPorId[device.device_id] ?? 'aguardando');
          return (
            <li
              key={device.device_id}
              className={`flex min-w-0 flex-col gap-2 rounded-xl border border-linha p-4 md:rounded-none md:border-0 md:border-b md:px-0 md:py-3 ${COLUNAS}`}
            >
              <span className="order-1 font-mono text-xs text-taupe md:order-none">{device.device_id}</span>
              <span className="font-display text-lg break-words text-vinho">{device.name}</span>
              <span className="text-sm break-words text-taupe">{device.city}</span>
              <span className="order-2 md:order-none">
                <SeloStatus status={status} />
              </span>
              <Botao
                variante="perigo"
                className="order-3 self-start md:order-none md:self-auto"
                onClick={() => remover(device)}
                disabled={removendo !== null}
                carregando={removendo === device.device_id}
                textoCarregando="Removendo…"
              >
                Excluir
              </Botao>
            </li>
          );
        })}
      </ul>
    </>
  );
}
```

- [ ] **Passo 3: `Devices.jsx`, trocar os imports de UI e o `return`** (a lógica fica igual)

```jsx
import { Cartao, Esqueleto, GradeBento, MensagemErro, Nota, Subtitulo, Titulo } from '../components/ui/index.js';
```

```jsx
  return (
    <section>
      <Titulo overline="Cadastro">Dispositivos</Titulo>
      <GradeBento>
        <Cartao className="md:col-span-2 lg:col-span-1">
          <Subtitulo>Nova vinheria</Subtitulo>
          <DeviceForm onCreated={aposMudanca} />
        </Cartao>
        <Cartao larg={3}>
          <Subtitulo>Vinherias</Subtitulo>
          <MensagemErro erro={listar.erro} />
          {devices === null ? (
            listar.erro ? (
              <Nota>Não foi possível carregar a lista.</Nota>
            ) : (
              <div className="flex flex-col gap-3">
                <Esqueleto className="h-16" />
                <Esqueleto className="h-16" />
                <Esqueleto className="h-16" />
              </div>
            )
          ) : (
            <DeviceList devices={devices} statusPorId={statusPorId} onDeleted={aposMudanca} />
          )}
        </Cartao>
      </GradeBento>
    </section>
  );
```

- [ ] **Passo 4: verificar**

Rode `npm test && npm run build`. Esperado: 41 passed e build ok. No navegador, em `/dispositivos`:
- **375 px:**
  - o cartão "Nova vinheria" fica em cima, com o botão em largura total;
  - abaixo, cada vinheria vira um cartão na ordem nome, cidade, id em mono, selo e Excluir em contorno vermelho;
  - não há rolagem horizontal.
- **768 px:** os dois cartões em largura total, empilhados; a lista em colunas com o cabeçalho em caixa alta.
- **1024 px:** formulário à esquerda (1/4) e lista à direita (3/4).
- **Nome longo:** cadastrar `vinheria098` com nome de 60 letras `x` mostra o nome quebrando dentro do cartão em 375 px, sem rolagem. Depois, remova a `vinheria098`.
- **Comportamento da 5A** (EC2 ligada):
  - cadastrar a `vinheria099` mostra "Provisionando no FIWARE…", sem duplo envio, e o selo "Aguardando 1º ciclo" vira o status real;
  - Excluir pede confirmação e remove.
- **Carregamento:** com o backend parado e a página recarregada, aparecem os esqueletos e depois o erro.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/pages/Devices.jsx frontend/src/components/DeviceForm.jsx frontend/src/components/DeviceList.jsx
git commit -m "feat: aplica o layout bento e a lista responsiva na tela de dispositivos"
```

---

## Subtarefa 5B.10 — Placeholders, herói e 404 (R7.4, R8)

**Files:** substituir `src/pages/Placeholder.jsx`.

- [ ] **Passo 1: substituir `src/pages/Placeholder.jsx` inteiro**

```jsx
/**
 * Tela provisória das rotas que outras tasks ainda vão preencher
 * (Visão geral, Detalhe e Alertas na Task 6; Chat na Task 7A).
 * Com `heroi` (rota /), abre com o herói da marca no lugar do título.
 * Sem `task`, serve de página "não encontrada".
 */
import { IMAGEM_HEROI } from '../constants.js';
import { EstadoVazio, Heroi, LinkInterno, Titulo } from '../components/ui/index.js';

export default function Placeholder({ titulo, task, heroi = false }) {
  if (!task) {
    return (
      <section>
        <Titulo overline="Erro 404">Página não encontrada</Titulo>
        <EstadoVazio
          titulo="Nada por aqui"
          texto="Confira o endereço ou volte para o painel."
          acao={<LinkInterno to="/">Ir para a Visão geral</LinkInterno>}
        />
      </section>
    );
  }

  return (
    <section>
      {heroi ? (
        <Heroi titulo="Smart Solutions" subtitulo="Monitoramento de vinherias" imagem={IMAGEM_HEROI} />
      ) : (
        <Titulo overline="Em construção">{titulo}</Titulo>
      )}
      <EstadoVazio titulo={titulo} texto={`Esta tela chega na ${task}.`} />
    </section>
  );
}
```

- [ ] **Passo 2: verificar**

Rode `npm test && npm run build`. Esperado: 41 passed e build ok. No navegador:
- `/` mostra o herói com o gradiente bordô e a etiqueta "IMAGEM DO VINHEDO" no canto superior direito. O título "Smart Solutions" fica grande em creme, legível sobre o véu.
  - Em 375 px a proporção é 4:3; em 1024 px, 21:9.
- `/alertas` e `/chat` mostram título + bloco tracejado "Esta tela chega na…".
- `/qualquer` mostra o 404, e o link volta para `/` sem recarregar.
- **Slot (R8.2):** teste trocar `IMAGEM_HEROI` por `'/x.jpg'` com qualquer imagem em `frontend/public/`. A foto ocupa a mesma caixa, sem pular o layout. Depois, desfaça a troca e apague a imagem.

- [ ] **Passo 3: commit**

```bash
git add frontend/src/pages/Placeholder.jsx
git commit -m "feat: adiciona o heroi da visao geral e o visual das telas em construcao"
```

---

## Subtarefa 5B.11 — Movimento com a skill `cast` (R1.5, D7)

**Files:** modificar `src/styles.css`.

- [ ] **Passo 1: anunciar e rodar a skill `cast`** com este escopo fechado:
  - só CSS e `requestAnimationFrame`, sem GSAP nem dependência nova;
  - só os movimentos da spec: entrada dos cartões (`entrar`) em cascata, pulso do alerta (`pulsar`), contagem (`useContagem`), entrada do toast e do painel Avançado, brilho do esqueleto.

  Se a skill propuser algo fora disso, registre como sugestão no fim deste plano e **não implemente**.

- [ ] **Passo 2: acrescentar a cascata ao fim de `src/styles.css`** (a `GradeBento` já usa a classe `cascata` desde a 5B.5)

```css
/* Entrada em cascata dos cartões de uma GradeBento: cada filho atrasa 40 ms */
@layer components {
  .cascata > :nth-child(2) { animation-delay: 40ms; }
  .cascata > :nth-child(3) { animation-delay: 80ms; }
  .cascata > :nth-child(4) { animation-delay: 120ms; }
  .cascata > :nth-child(5) { animation-delay: 160ms; }
  .cascata > :nth-child(6) { animation-delay: 200ms; }
  .cascata > :nth-child(7) { animation-delay: 240ms; }
  .cascata > :nth-child(n + 8) { animation-delay: 280ms; }
}
```

- [ ] **Passo 3: verificar**

Rode `npm run build`. Esperado: build ok. No navegador:
- em `/dispositivos`, os dois cartões entram um depois do outro;
- abrir o Avançado e chegar um toast têm fade-up curto.

No DevTools, em Rendering, ligue "Emulate CSS media feature prefers-reduced-motion: reduce" e recarregue:
- nada se move;
- o selo de alerta fica parado;
- os números aparecem já no valor final.

- [ ] **Passo 4: commit**

```bash
git add frontend/src/styles.css
git commit -m "feat: adiciona a entrada em cascata dos cartoes"
```

---

## Subtarefa 5B.12 — Auditoria com `impeccable-design-polish`

**Files:** os que os achados apontarem; acrescentar a seção "Achados da auditoria 5B" no fim deste `plan.md`.

- [ ] **Passo 1: anunciar e rodar a skill `impeccable-design-polish`** sobre as telas `/`, `/dispositivos`, `/alertas`, 404, o Avançado aberto, a faixa e um toast, em 375, 768, 1024 e 1440 px.

- [ ] **Passo 2: registrar os achados** no fim deste plano, numa tabela `# | tela | achado | ação`. A ação é uma de três:
  - **corrigir agora:** o achado cabe nos tokens e componentes desta spec;
  - **Task 6:** o achado depende de conteúdo que ainda não existe;
  - **devolver ao planejamento:** o achado exige uma decisão nova (cor, fonte, componente ou comportamento que não está na spec).

  Se houver qualquer "devolver ao planejamento", pare aqui e reporte.

- [ ] **Passo 3: corrigir os achados "corrigir agora"**, um commit por achado, com `fix: <achado>`. Depois de cada um, rode `npm test && npm run build`.

- [ ] **Passo 4: commit do registro**

```bash
git add docs/specs/task-5b-design-system/plan.md
git commit -m "docs: registra os achados da auditoria de design da task 5b"
```

---

## Subtarefa 5B.13 — Verificação final e fechamento

- [ ] **Passo 1: suíte e build**

```bash
cd frontend
npm test        # 41 passed
npm run build   # sem erro
```

- [ ] **Passo 2: conferências estáticas**

```bash
grep -rnE "#[0-9a-fA-F]{3,8}\b|rgb\(" src --include=*.jsx    # esperado: nada
grep -rn "style={" src                                        # esperado: nada
grep -rln "fetch(" src                                        # esperado: só src/api/client.js e src/api/client.test.js
grep -rn "<table" src                                         # esperado: nada
grep -rn "fonts.googleapis" src index.html                    # esperado: nada
grep -rn "<h1\|<h2\|<input\|<button" src --include=*.jsx | grep -v "components/ui/"   # esperado: nada
grep -rn "ui.jsx'" src                                        # esperado: nada
find src -name "*.ts" -o -name "*.tsx"                        # esperado: nada
find src -name "*.js*" | xargs wc -l | sort -n | tail -5      # nenhum acima de ~250
ls public 2>/dev/null                                         # esperado: nada novo (sem imagens)
```

- [ ] **Passo 3: checklist do `ui-ux-pro-max`.** Leia `C:\Users\isacn\.claude\skills\ui-ux-pro-max\references\pro-rules.md` (Pre-Delivery Checklist) e confira cada item aplicável à web. Anote os que não se aplicam.

- [ ] **Passo 4: ensaio completo no navegador** (backend, EC2 e Wokwi ligados), numa sessão só:
  1. Em 375, 768, 1024 e 1440 px:
     - sem rolagem horizontal em nenhuma rota;
     - barra inferior só abaixo de 768 px.
  2. Tab do topo ao fim de `/dispositivos`: todo elemento interativo mostra o anel bordô de foco.
  3. Com o Avançado aberto, Esc fecha o painel.
  4. Comportamento da 5A, idêntico:
     - troca de IP (vermelho/verde);
     - cadastro e remoção da `vinheria099`;
     - toast e faixa de offline e de volta ao parar e religar um Wokwi;
     - backend parado e voltando, com o painel se recuperando sem F5.
  5. Movimento reduzido ligado: nada anima.

  Anote o que divergir.

- [ ] **Passo 5: documentar**
  - Em `PLANO-CP5-VINHERIA.md`, na seção da Task 5, acrescente sob a nota da 5A: `> **5B FEITA em <data>** — commits <primeiro>..<último>; 41 testes do front; desvios: …` (ou "nenhum").
  - No topo deste `plan.md`, acrescente a linha `> **Estado em <data>:** feitas as subtarefas 5B.1 a 5B.13.`

- [ ] **Passo 6: commit**

```bash
git add PLANO-CP5-VINHERIA.md docs/specs/task-5b-design-system/plan.md
git commit -m "docs: fecha a task 5b com o design system aplicado ao painel"
```

Pare aqui e espere a revisão do usuário.

---

## Achados da auditoria 5B (subtarefa 5B.12, 18/10/2026)

Auditoria feita sobre capturas do Edge headless de `/` (500 e 1280 px) e `/dispositivos` (375 e 1280 px), com a EC2 fora do ar (o que exercitou a faixa e o selo de "EC2 fora"). O Edge headless não desce de ~500 px de largura de janela, então a ausência de rolagem horizontal em 375 px **não** foi provada por captura e fica para o ensaio manual da 5B.13.

| # | tela | achado | ação |
|---|---|---|---|
| 1 | `/dispositivos` (≥ 768 px) | Colunas Cidade e Status do cabeçalho deslocadas em relação às linhas: a última coluna `auto` ficava vazia no cabeçalho e larga nas linhas, e as colunas `1fr` se dividiam diferente. | corrigido: última coluna fixa em `7.5rem`, botão com `md:w-full` (commit `fix: alinha as colunas…`) |
| 2 | `EstadoVazio` | Borda tracejada `linha` quase invisível sobre o creme. | corrigido: `border-rose/60` |
| 3 | `/` | Título do herói e logo da barra repetem "Smart Solutions". | mantido: está na spec (R7.4); some quando o herói ganhar a foto e o logo virar imagem |
| 4 | todas | Painel Avançado, toasts e a barra inferior com selo de atenção não aparecem em captura estática. | ensaio manual 5B.13 |
