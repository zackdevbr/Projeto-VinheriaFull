# Task 6 — Visão geral, detalhe com gráficos, faixa, comandos e alertas — Plano de execução

> **Estado em 20/10/2026:** Task 6 fechada pelo usuário (subtarefas 6.1 a 6.13 e ajustes posteriores; ver a nota da Task 6 no PLANO). O ensaio formal com 2 Wokwi não foi registrado.

> **Para quem executa (Sonnet):** use `superpowers:executing-plans` e `superpowers:test-driven-development`. Os passos usam checkbox (`- [ ]`). Execute as subtarefas em ordem; informe o resultado de cada passo e faça um commit por subtarefa. Se algo não bater com a [`spec.md`](spec.md), pare e devolva para planejamento; não improvise. Toda decisão visual já está na spec, na spec da 5B e neste plano: **não invente cor, fonte, espaçamento ou componente**.

**Objetivo:** entregar `/` (herói + KPIs + cartões), `/vinherias/:id` (score, valores, três gráficos do STH, faixa, alerta manual, linha do tempo) e `/alertas` (histórico filtrável) no design system da 5B.

**Arquitetura:**
- A lógica pura e testada fica em `src/lib/`: `frota`, `faixa`, `serie`, `alertas`, `numero`, `tema`, `atributos`, `rotas`, `movimento`.
- `hooks/useLeitura.js` lê dados do backend com estado pronto (`dados`, `erro`, `carregando`, `recarregar`) e polling opcional.
- `lib/graficos.js` registra o Chart.js uma vez, e as cores dos gráficos vêm dos tokens CSS (`lib/tema.js`).
- Os componentes de domínio ficam em `components/`, as páginas em `pages/` e as peças genéricas novas no kit `components/ui/`.
- Nome, status e valores atuais vêm do `FleetContext`.

**Stack:** React 19, react-router-dom, Vite, Tailwind v4, `chart.js` + `react-chartjs-2` (novas), `lucide-react`, Vitest (ambiente `node`, só `src/**/*.test.js`).

**Spec:** [`spec.md`](spec.md). Base visual: [`../task-5b-design-system/spec.md`](../task-5b-design-system/spec.md).

## Restrições globais

- JavaScript puro (`.jsx`/`.js`), comentário em português no topo de todo arquivo novo e em funções não óbvias.
- Em `.jsx`: sem hex, `rgb(` nem `style={`. Cores do Chart.js só via `corDoTema` (`lib/tema.js`).
- `<h1>`, `<h2>`, `<input>`, `<select>` e `<button>` só dentro de `components/ui/`. Caminho `/vinherias/<id>` só por `caminhoVinheria` (`lib/rotas.js`).
- `fetch` só em `api/client.js`; telas usam `api.*`.
- Classes Tailwind escritas por inteiro. Alvos ≥ 44 px. Status sempre por `SeloStatus`.
- Arquivos de `src/` com no máximo ~250 linhas.
- Commits em português, imperativo, uma linha, **sem** `Co-Authored-By` (`CLAUDE.md` §8).
- Nenhuma mudança no backend.

## Riscos que os testes cobrem (Review Focus)

1. **Texto de número digitado com vírgula ("12,5") ou campo vazio na faixa**: não pode ir ao backend como `NaN`. Coberto por `faixa.test.js` (6.3).
2. **Intervalo de datas invertido ou vazio**: não pode virar uma consulta ao STH. Coberto por `serie.test.js` (6.4).
3. **Status desconhecido vindo do backend**: não pode quebrar a ordenação dos cartões (vai para o fim). Coberto por `frota.test.js` (6.2).
4. **Alerta da EC2** (`device_id=fiware`) e alerta sem valor (`value: null`): não podem mostrar "undefined" na linha do tempo. Coberto por `alertas.test.js` (6.4).
5. **Parâmetro `last_n` e datas com `:` na URL**: o backend usa snake_case, e as datas precisam de codificação. Coberto por `client.test.js` (6.5).

## Mapa de arquivos

| arquivo | ação | responsabilidade |
|---|---|---|
| `frontend/package.json` | modificar | + `chart.js`, `react-chartjs-2` |
| `src/styles.css` | modificar | `@theme` → `@theme static` (todos os tokens viram variáveis CSS, lidas pelo Chart.js) |
| `src/constants.js` | modificar | `LEITURA_POLL_MS`, `ID_FIWARE`, `JANELA_PADRAO` |
| `src/estilo.js` | modificar | + `ICONE_ATRIBUTO` |
| `src/lib/movimento.js` | criar | `prefereMenosMovimento()` (extraída do `useContagem`) |
| `src/lib/tema.js` + test | criar | `comAlfa`, `lerToken`, `corDoTema` |
| `src/lib/graficos.js` | criar | registro do Chart.js + `gradienteVertical` |
| `src/lib/numero.js` + test | criar | `formatarNumero` (pt-BR) |
| `src/lib/atributos.js` | criar | metadados dos 3 atributos (rótulo, unidade, comando...) |
| `src/lib/rotas.js` | criar | `caminhoVinheria(id)` |
| `src/lib/frota.js` + test | criar | `resumoFrota`, `ordenarFrota`, `vistoHa`, `textoVisto` |
| `src/lib/faixa.js` + test | criar | `validarFaixa`, `foraDaFaixa` |
| `src/lib/serie.js` + test | criar | `parametrosJanela`, `paraSerie` |
| `src/lib/alertas.js` + test | criar | `duracao`, `rotuloAlerta`, `formatarDataHora` |
| `src/api/client.js` + test | modificar | 7 funções novas |
| `src/hooks/useContagem.js` | modificar | usa `lib/movimento.js` |
| `src/hooks/useLeitura.js` | criar | leitura com estado + polling opcional |
| `src/hooks/useAlertas.js` | criar | alertas de uma vinheria ou de todas, a cada 10 s |
| `src/components/ui/formulario.jsx` | modificar | `Campo` ganha `erro`; + `Seletor`, `BotoesSegmentados` |
| `src/components/ui/cartoes.jsx` | modificar | `Cartao` ganha `para` (cartão-link); `CartaoKpi` ganha `rodapeAlerta` e usa `formatarNumero` |
| `src/components/ui/base.jsx` | modificar | `LinkVinheria` usa `caminhoVinheria` |
| `src/components/VinheriaCard.jsx` | criar | cartão da Visão geral |
| `src/components/SeletorJanela.jsx` | criar | 20/50/100/Datas |
| `src/components/SensorChart.jsx` | criar | gráfico de um atributo |
| `src/components/GaugeScore.jsx` | criar | rosca do score |
| `src/components/TriggerPanel.jsx` | criar | faixa ideal |
| `src/components/PainelComandos.jsx` | criar | alerta manual |
| `src/components/AlertTimeline.jsx` | criar | linha do tempo |
| `src/pages/Overview.jsx` | criar | `/` |
| `src/pages/VinheriaDetail.jsx` | criar | `/vinherias/:id` |
| `src/pages/Alerts.jsx` | criar | `/alertas` |
| `src/pages/Placeholder.jsx` | modificar | perde o modo `heroi` (a `/` vira Overview) |
| `src/App.jsx` | modificar | rotas novas |

Testes ao fim: 41 da 5B + 2 (`tema`) + 2 (`numero`) + 6 (`frota`) + 6 (`faixa`) + 6 (`serie`) + 5 (`alertas`) + 5 (`client`) = **73**.

---

## Subtarefa 6.1 — Chart.js, tokens legíveis em runtime e movimento reduzido comum

**Files:** `package.json` (npm), `src/styles.css`, criar `src/lib/movimento.js`, `src/lib/tema.js`, `src/lib/tema.test.js`, `src/lib/graficos.js`; modificar `src/hooks/useContagem.js`.

**Produz:** `prefereMenosMovimento() -> boolean`, `comAlfa(hex, alfa) -> string`, `lerToken(nome) -> string`, `corDoTema(nome, alfa = 1) -> string`, `gradienteVertical(corTopo, corBase) -> function`.

- [ ] **Passo 1: instalar**

```bash
cd frontend
npm install chart.js react-chartjs-2
```
Esperado: as duas em `dependencies`.

- [ ] **Passo 2: `src/styles.css`.** Troque a linha `@theme {` por `@theme static {`. Sem `static`, o Tailwind v4 só emite as variáveis dos tokens que alguma classe usa, e o Chart.js lê variáveis CSS em runtime.

- [ ] **Passo 3: escrever o teste que falha, `src/lib/tema.test.js`**

```js
/** Testes da conversão de cor dos tokens para o Chart.js (spec R3.2). */
import { describe, expect, it } from 'vitest';
import { comAlfa } from './tema.js';

describe('comAlfa', () => {
  it('converte hex com # em rgb com transparência', () => {
    expect(comAlfa('#7a1f2b', 0.35)).toBe('rgb(122 31 43 / 0.35)');
  });

  it('aceita hex sem # e em maiúsculas', () => {
    expect(comAlfa('FBF5F0', 0.2)).toBe('rgb(251 245 240 / 0.2)');
  });
});
```

- [ ] **Passo 4: rodar e ver falhar**

Rode `npm test -- tema`. Esperado: FAIL, porque `./tema.js` não existe.

- [ ] **Passo 5: criar `src/lib/tema.js`**

```js
/**
 * Leitura dos tokens do design system (styles.css) em runtime, para o
 * Chart.js, que desenha em canvas e não entende classes Tailwind. Assim a
 * paleta continua com fonte única no @theme e nenhum hex se repete aqui.
 */

/** Cor hex (#rrggbb) com transparência, no formato rgb moderno. */
export function comAlfa(hex, alfa) {
  const limpo = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((inicio) => parseInt(limpo.slice(inicio, inicio + 2), 16));
  return `rgb(${r} ${g} ${b} / ${alfa})`;
}

/** Valor de uma variável CSS do :root (ex.: '--font-sans'). */
export function lerToken(nome) {
  return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
}

/** Cor de um token (ex.: 'bordo'), opcionalmente com transparência. */
export function corDoTema(nome, alfa = 1) {
  const hex = lerToken(`--color-${nome}`);
  return alfa === 1 ? hex : comAlfa(hex, alfa);
}
```

- [ ] **Passo 6: rodar e ver passar**

Rode `npm test`. Esperado: 43 passed.

- [ ] **Passo 7: criar `src/lib/movimento.js`**

```js
/**
 * Preferência do sistema por menos movimento (prefers-reduced-motion).
 * Usada pela contagem dos números e pelas animações do Chart.js. Fora do
 * navegador (testes), responde false.
 */
export function prefereMenosMovimento() {
  return globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}
```

- [ ] **Passo 8: `src/hooks/useContagem.js`.** Apague a função local `prefereMenosMovimento` e importe a de `../lib/movimento.js`:

```js
import { prefereMenosMovimento } from '../lib/movimento.js';
```

- [ ] **Passo 9: criar `src/lib/graficos.js`**

```js
/**
 * Registro único do Chart.js: só os módulos que o painel usa (linha com
 * área e rosca), para o bundle não levar a biblioteca inteira. Quem desenha
 * <Line> ou <Doughnut> importa este arquivo. A fonte padrão vem do token
 * --font-sans (Inter).
 */
import {
  ArcElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { lerToken } from './tema.js';

Chart.register(
  ArcElement,
  CategoryScale,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
);
Chart.defaults.font.family = lerToken('--font-sans') || 'sans-serif';
Chart.defaults.font.size = 11;

/** Preenchimento em gradiente vertical (cor no topo, outra na base), calculado na área do gráfico. */
export function gradienteVertical(corTopo, corBase) {
  return ({ chart }) => {
    const { ctx, chartArea } = chart;
    if (!chartArea) {
      return corBase;
    }
    const gradiente = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    gradiente.addColorStop(0, corTopo);
    gradiente.addColorStop(1, corBase);
    return gradiente;
  };
}
```

- [ ] **Passo 10: verificar**

```bash
npm test && npm run build
grep -o "\-\-color-rose:[^;]*" dist/assets/*.css   # esperado: --color-rose:#b5838d (token pouco usado agora aparece)
```

- [ ] **Passo 11: commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src
git commit -m "chore: adiciona o chart.js e a leitura dos tokens de cor em runtime"
```

---

## Subtarefa 6.2 — Números, atributos, rotas e frota (R2.1–R2.3)

**Files:** criar `src/lib/numero.js` + `numero.test.js`, `src/lib/atributos.js`, `src/lib/rotas.js`, `src/lib/frota.js` + `frota.test.js`.

**Produz:**
- `formatarNumero(numero, casas?) -> string`;
- `ATRIBUTOS` (array) e `ATRIBUTO` (mapa por chave) com `{ chave, rotulo, abreviado, curto, unidade, comando, botao }`;
- `caminhoVinheria(id) -> string`;
- `resumoFrota(frota)`, `ordenarFrota(vinherias)`, `vistoHa(segundos)`, `textoVisto(vinheria)`.

- [ ] **Passo 1: escrever os testes que falham.** `src/lib/numero.test.js`:

```js
/** Testes da formatação de números em pt-BR usada no painel. */
import { describe, expect, it } from 'vitest';
import { formatarNumero } from './numero.js';

describe('formatarNumero', () => {
  it('sem casas fixas usa vírgula e até uma casa', () => {
    expect(formatarNumero(21.44)).toBe('21,4');
    expect(formatarNumero(75)).toBe('75');
  });

  it('com casas fixas mantém o número de casas', () => {
    expect(formatarNumero(16.9, 1)).toBe('16,9');
    expect(formatarNumero(17, 1)).toBe('17,0');
    expect(formatarNumero(91.6, 0)).toBe('92');
  });
});
```

`src/lib/frota.test.js`:

```js
/** Testes do resumo, da ordem e do "visto há" da frota (spec R2.1–R2.3). */
import { describe, expect, it } from 'vitest';
import { ordenarFrota, resumoFrota, textoVisto, vistoHa } from './frota.js';

const v = (device_id, status) => ({ device_id, status });

describe('resumoFrota', () => {
  it('sem frota devolve tudo zero', () => {
    expect(resumoFrota(null)).toEqual({ total: 0, ok: 0, alerta: 0, offline: 0, configurando: 0 });
  });

  it('conta cada status e o total', () => {
    const frota = { vinherias: [v('a', 'ok'), v('b', 'ok'), v('c', 'alerta'), v('d', 'offline'), v('e', 'configurando')] };
    expect(resumoFrota(frota)).toEqual({ total: 5, ok: 2, alerta: 1, offline: 1, configurando: 1 });
  });
});

describe('ordenarFrota', () => {
  const lista = [
    v('vinheria005', 'ok'),
    v('vinheria003', 'alerta'),
    v('vinheria002', 'configurando'),
    v('vinheria004', 'offline'),
    v('vinheria001', 'alerta'),
    v('vinheria006', 'manutencao'),
  ];

  it('põe alerta, offline, configurando e ok nessa ordem, desconhecido no fim', () => {
    expect(ordenarFrota(lista).map((x) => x.device_id)).toEqual([
      'vinheria001', 'vinheria003', 'vinheria004', 'vinheria002', 'vinheria005', 'vinheria006',
    ]);
  });

  it('não altera a lista recebida', () => {
    ordenarFrota(lista);
    expect(lista[0].device_id).toBe('vinheria005');
  });
});

describe('vistoHa', () => {
  it('descreve o tempo desde a última leitura', () => {
    expect(vistoHa(null)).toBe('sem leitura');
    expect(vistoHa(0)).toBe('agora');
    expect(vistoHa(4)).toBe('agora');
    expect(vistoHa(12)).toBe('há 12 s');
    expect(vistoHa(59)).toBe('há 59 s');
    expect(vistoHa(60)).toBe('há 1 min');
    expect(vistoHa(3599)).toBe('há 59 min');
    expect(vistoHa(7200)).toBe('há 2 h');
  });
});

describe('textoVisto', () => {
  it('com a EC2 fora diz isso; senão o tempo desde a leitura', () => {
    expect(textoVisto({ offline_reason: 'fiware', seconds_since: 400 })).toBe('EC2 fora');
    expect(textoVisto({ offline_reason: null, seconds_since: 12 })).toBe('há 12 s');
  });
});
```

- [ ] **Passo 2: rodar e ver falhar**

Rode `npm test -- numero frota`. Esperado: FAIL, porque os módulos não existem.

- [ ] **Passo 3: criar `src/lib/numero.js`**

```js
/**
 * Formatação de números para a tela, no padrão brasileiro (vírgula decimal).
 */

/** Sem `casas`, usa até uma casa decimal; com `casas`, fixa a quantidade (evita "pular" durante a contagem). */
export function formatarNumero(numero, casas) {
  const opcoes = casas === undefined
    ? { maximumFractionDigits: 1 }
    : { minimumFractionDigits: casas, maximumFractionDigits: casas };
  return numero.toLocaleString('pt-BR', opcoes);
}
```

- [ ] **Passo 4: criar `src/lib/atributos.js`**

```js
/**
 * Os três atributos monitorados, com os nomes canônicos do FIWARE (chave),
 * o rótulo e a unidade da tela e o comando de alerta manual de cada um.
 * Fonte única para cartões, gráficos, faixa, comandos e linha do tempo.
 */
export const ATRIBUTOS = [
  { chave: 'temperature', rotulo: 'Temperatura', abreviado: 'Temp', curto: 'T', unidade: '°C', comando: 'blink_temp', botao: 'Piscar temperatura' },
  { chave: 'humidity', rotulo: 'Umidade', abreviado: 'Umid', curto: 'U', unidade: '%', comando: 'blink_hum', botao: 'Piscar umidade' },
  { chave: 'luminosity', rotulo: 'Luminosidade', abreviado: 'Luz', curto: 'L', unidade: '%', comando: 'blink_lux', botao: 'Piscar luz' },
];

// Mesmo conteúdo indexado pela chave (ex.: ATRIBUTO.temperature.unidade)
export const ATRIBUTO = Object.fromEntries(ATRIBUTOS.map((atributo) => [atributo.chave, atributo]));
```

- [ ] **Passo 5: criar `src/lib/rotas.js`**

```js
/**
 * Caminhos das rotas do painel montados num lugar só (react-router-dom).
 */

/** Rota do detalhe de uma vinheria. */
export function caminhoVinheria(deviceId) {
  return `/vinherias/${encodeURIComponent(deviceId)}`;
}
```

- [ ] **Passo 6: criar `src/lib/frota.js`**

```js
/**
 * Contas sobre o retrato da frota (GET /api/fleet) para a Visão geral:
 * quantas vinherias em cada status, em que ordem mostrar os cartões e o
 * texto de "visto há".
 */

// Quem precisa de atenção aparece primeiro; status desconhecido vai para o fim
const ORDEM = { alerta: 0, offline: 1, configurando: 2, ok: 3 };

function peso(status) {
  return Object.hasOwn(ORDEM, status) ? ORDEM[status] : 4;
}

/** Total e quantidade por status. Com frota null, tudo zero. */
export function resumoFrota(frota) {
  const resumo = { total: 0, ok: 0, alerta: 0, offline: 0, configurando: 0 };
  for (const vinheria of frota?.vinherias ?? []) {
    resumo.total += 1;
    if (Object.hasOwn(resumo, vinheria.status) && vinheria.status !== 'total') {
      resumo[vinheria.status] += 1;
    }
  }
  return resumo;
}

/** Nova lista ordenada por status (alerta, offline, configurando, ok) e depois por device_id. */
export function ordenarFrota(vinherias) {
  return [...vinherias].sort(
    (a, b) => peso(a.status) - peso(b.status) || a.device_id.localeCompare(b.device_id),
  );
}

/** Tempo desde a última leitura em texto curto. */
export function vistoHa(segundos) {
  if (segundos === null || segundos === undefined) {
    return 'sem leitura';
  }
  if (segundos < 5) {
    return 'agora';
  }
  if (segundos < 60) {
    return `há ${segundos} s`;
  }
  if (segundos < 3600) {
    return `há ${Math.floor(segundos / 60)} min`;
  }
  return `há ${Math.floor(segundos / 3600)} h`;
}

/** Rodapé de uma vinheria: "EC2 fora" quando a queda é da EC2; senão o vistoHa. */
export function textoVisto(vinheria) {
  return vinheria.offline_reason === 'fiware' ? 'EC2 fora' : vistoHa(vinheria.seconds_since);
}
```

- [ ] **Passo 7: rodar e ver passar**

Rode `npm test`. Esperado: 51 passed.

- [ ] **Passo 8: commit**

```bash
git add frontend/src/lib
git commit -m "feat: adiciona o resumo, a ordem e o tempo desde a leitura da frota"
```

---

## Subtarefa 6.3 — Validação da faixa (R2.4, R2.9)

**Files:** criar `src/lib/faixa.js` + `faixa.test.js`.

**Produz:** `validarFaixa(campos) -> { dados, erros }`, `foraDaFaixa(valor, faixa) -> boolean`.

- [ ] **Passo 1: escrever o teste que falha, `src/lib/faixa.test.js`**

```js
/** Testes da validação da faixa ideal e do "fora da faixa" (spec R2.4, R2.9). */
import { describe, expect, it } from 'vitest';
import { foraDaFaixa, validarFaixa } from './faixa.js';

const valida = {
  temperature: { min: '12,5', max: '18' },
  humidity: { min: 50, max: 70 },
  luminosity: { min: '0', max: '30' },
};

describe('validarFaixa', () => {
  it('aceita vírgula ou ponto e devolve números', () => {
    expect(validarFaixa(valida)).toEqual({
      dados: {
        temperature: { min: 12.5, max: 18 },
        humidity: { min: 50, max: 70 },
        luminosity: { min: 0, max: 30 },
      },
      erros: {},
    });
  });

  it('recusa campo vazio ou não numérico', () => {
    const resultado = validarFaixa({ ...valida, temperature: { min: '', max: '18' }, humidity: { min: 50, max: 'abc' } });
    expect(resultado.dados).toBeNull();
    expect(resultado.erros['temperature.min']).toBe('Informe um número');
    expect(resultado.erros['humidity.max']).toBe('Informe um número');
  });

  it('recusa mínimo maior ou igual ao máximo, com o erro no campo máximo', () => {
    const resultado = validarFaixa({ ...valida, luminosity: { min: '30', max: '30' } });
    expect(resultado.dados).toBeNull();
    expect(resultado.erros['luminosity.max']).toMatch(/menor que o máximo/);
  });

  it('atributo ausente dá erro nos dois campos', () => {
    const { luminosity, ...semLuz } = valida;
    const resultado = validarFaixa(semLuz);
    expect(resultado.erros['luminosity.min']).toBe('Informe um número');
    expect(resultado.erros['luminosity.max']).toBe('Informe um número');
  });
});

describe('foraDaFaixa', () => {
  const faixa = { min: 12, max: 18 };

  it('só fora quando passa do limite (limite exato está dentro)', () => {
    expect(foraDaFaixa(11.9, faixa)).toBe(true);
    expect(foraDaFaixa(18.1, faixa)).toBe(true);
    expect(foraDaFaixa(12, faixa)).toBe(false);
    expect(foraDaFaixa(18, faixa)).toBe(false);
  });

  it('valor ou faixa ausentes não contam como fora', () => {
    expect(foraDaFaixa(null, faixa)).toBe(false);
    expect(foraDaFaixa(15, null)).toBe(false);
  });
});
```

- [ ] **Passo 2: rodar e ver falhar**

Rode `npm test -- faixa`. Esperado: FAIL, porque o módulo não existe.

- [ ] **Passo 3: criar `src/lib/faixa.js`**

```js
/**
 * Faixa ideal de uma vinheria (RF06): validação do formulário antes de ir
 * ao backend e a pergunta "este valor está fora da faixa?" usada nos
 * cartões e nos gráficos.
 */
import { ATRIBUTOS } from './atributos.js';

const SEM_NUMERO = 'Informe um número';
const MIN_MAIOR = 'O mínimo precisa ser menor que o máximo';

/** Texto do campo (aceita vírgula) para número; vazio ou inválido vira NaN. */
function paraNumero(valor) {
  const texto = String(valor ?? '').trim().replace(',', '.');
  return texto === '' ? Number.NaN : Number(texto);
}

/**
 * Valida a faixa dos três atributos. Devolve { dados, erros }: `dados` com
 * números quando tudo está certo (senão null) e `erros` por campo, no
 * formato { 'temperature.min': 'mensagem' }.
 */
export function validarFaixa(campos) {
  const dados = {};
  const erros = {};
  for (const { chave } of ATRIBUTOS) {
    const min = paraNumero(campos[chave]?.min);
    const max = paraNumero(campos[chave]?.max);
    if (!Number.isFinite(min)) {
      erros[`${chave}.min`] = SEM_NUMERO;
    }
    if (!Number.isFinite(max)) {
      erros[`${chave}.max`] = SEM_NUMERO;
    }
    if (Number.isFinite(min) && Number.isFinite(max) && min >= max) {
      erros[`${chave}.max`] = MIN_MAIOR;
    }
    dados[chave] = { min, max };
  }
  return Object.keys(erros).length > 0 ? { dados: null, erros } : { dados, erros };
}

/** true quando o valor passa do mínimo ou do máximo; sem valor ou sem faixa, false. */
export function foraDaFaixa(valor, faixa) {
  if (valor === null || valor === undefined || !faixa) {
    return false;
  }
  return valor < faixa.min || valor > faixa.max;
}
```

- [ ] **Passo 4: rodar e ver passar**

Rode `npm test`. Esperado: 57 passed.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/lib/faixa.js frontend/src/lib/faixa.test.js
git commit -m "feat: adiciona a validacao da faixa ideal no navegador"
```

---

## Subtarefa 6.4 — Janela, série e textos dos alertas (R2.5–R2.8)

**Files:** criar `src/lib/serie.js` + `serie.test.js`, `src/lib/alertas.js` + `alertas.test.js`; modificar `src/constants.js`.

**Produz:** `parametrosJanela(janela)`, `paraSerie(pontos)`, `duracao(segundos)`, `rotuloAlerta(alerta)`, `formatarDataHora(iso)`, constante `ID_FIWARE`.

- [ ] **Passo 1: acrescentar ao fim de `src/constants.js`**

```js

// Leituras do detalhe e da página de alertas (histórico, score, alertas)
export const LEITURA_POLL_MS = 10000;

// device_id dos alertas que registram a EC2/FIWARE fora do ar
export const ID_FIWARE = 'fiware';

// Janela inicial dos gráficos do detalhe: os últimos 50 pontos
export const JANELA_PADRAO = { tipo: 'ultimos', n: 50 };
```

- [ ] **Passo 2: escrever os testes que falham.** `src/lib/serie.test.js`:

```js
/** Testes da janela dos gráficos e da conversão do histórico (spec R2.5, R2.6). */
import { describe, expect, it } from 'vitest';
import { paraSerie, parametrosJanela } from './serie.js';

describe('parametrosJanela', () => {
  it('últimos N pontos viram lastN', () => {
    expect(parametrosJanela({ tipo: 'ultimos', n: 50 })).toEqual({ lastN: 50 });
  });

  it('datas válidas viram ISO', () => {
    expect(parametrosJanela({ tipo: 'datas', de: '2026-10-19T10:00', ate: '2026-10-19T12:00' })).toEqual({
      dateFrom: new Date('2026-10-19T10:00').toISOString(),
      dateTo: new Date('2026-10-19T12:00').toISOString(),
    });
  });

  it('recusa datas vazias', () => {
    expect(parametrosJanela({ tipo: 'datas', de: '', ate: '2026-10-19T12:00' }).erro).toMatch(/início e o fim/);
  });

  it('recusa início igual ou depois do fim', () => {
    expect(parametrosJanela({ tipo: 'datas', de: '2026-10-19T12:00', ate: '2026-10-19T12:00' }).erro).toMatch(/antes do fim/);
    expect(parametrosJanela({ tipo: 'datas', de: '2026-10-19T13:00', ate: '2026-10-19T12:00' }).erro).toMatch(/antes do fim/);
  });
});

describe('paraSerie', () => {
  it('separa rótulos de hora e valores', () => {
    const serie = paraSerie([
      { ts: '2026-10-19T14:32:05.000Z', value: 21.4 },
      { ts: '2026-10-19T14:32:07.000Z', value: 21.5 },
    ]);
    expect(serie.valores).toEqual([21.4, 21.5]);
    expect(serie.rotulos).toHaveLength(2);
    for (const rotulo of serie.rotulos) {
      expect(rotulo).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    }
  });

  it('lista vazia dá listas vazias', () => {
    expect(paraSerie([])).toEqual({ rotulos: [], valores: [] });
  });
});
```

`src/lib/alertas.test.js`:

```js
/** Testes dos textos da linha do tempo de alertas (spec R2.7, R2.8). */
import { describe, expect, it } from 'vitest';
import { duracao, formatarDataHora, rotuloAlerta } from './alertas.js';

describe('duracao', () => {
  it('descreve a duração em texto curto', () => {
    expect(duracao(null)).toBe('em aberto');
    expect(duracao(0)).toBe('0 s');
    expect(duracao(45)).toBe('45 s');
    expect(duracao(60)).toBe('1 min 0 s');
    expect(duracao(252)).toBe('4 min 12 s');
    expect(duracao(3600)).toBe('1 h 0 min');
    expect(duracao(7380)).toBe('2 h 3 min');
  });
});

describe('rotuloAlerta', () => {
  it('sensor mostra nome, valor em pt-BR e unidade', () => {
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'temperature', value: 21.44 })).toBe('Temperatura 21,4 °C');
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'humidity', value: 75 })).toBe('Umidade 75 %');
  });

  it('offline da vinheria e queda da EC2 têm texto próprio', () => {
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'offline', value: null })).toBe('Offline');
    expect(rotuloAlerta({ device_id: 'fiware', attr: 'offline', value: null })).toBe('EC2 / FIWARE fora do ar');
  });

  it('sem valor mostra só o nome do atributo', () => {
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'luminosity', value: null })).toBe('Luminosidade');
  });
});

describe('formatarDataHora', () => {
  it('mostra dia/mês e hora:minuto', () => {
    expect(formatarDataHora('2026-10-19T14:32:00Z')).toMatch(/^\d{2}\/\d{2} \d{2}:\d{2}$/);
  });
});
```

- [ ] **Passo 3: rodar e ver falhar**

Rode `npm test -- serie alertas`. Esperado: FAIL, porque os módulos não existem.

- [ ] **Passo 4: criar `src/lib/serie.js`**

```js
/**
 * Janela dos gráficos (últimos N pontos ou intervalo de datas) e conversão
 * do histórico do STH-Comet ([{ ts, value }]) para o formato do Chart.js.
 */

/**
 * Parâmetros do GET de histórico para a janela escolhida. Datas vêm do
 * campo datetime-local (hora local) e saem em ISO. Janela inválida
 * devolve { erro } em vez dos parâmetros.
 */
export function parametrosJanela(janela) {
  if (janela.tipo === 'ultimos') {
    return { lastN: janela.n };
  }
  if (!janela.de || !janela.ate) {
    return { erro: 'Informe o início e o fim.' };
  }
  const de = new Date(janela.de);
  const ate = new Date(janela.ate);
  if (Number.isNaN(de.getTime()) || Number.isNaN(ate.getTime())) {
    return { erro: 'Data inválida.' };
  }
  if (de >= ate) {
    return { erro: 'O início precisa ser antes do fim.' };
  }
  return { dateFrom: de.toISOString(), dateTo: ate.toISOString() };
}

/** Rótulos HH:mm:ss (hora local) e valores, na ordem recebida. */
export function paraSerie(pontos) {
  return {
    rotulos: pontos.map((ponto) =>
      new Date(ponto.ts).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    ),
    valores: pontos.map((ponto) => ponto.value),
  };
}
```

- [ ] **Passo 5: criar `src/lib/alertas.js`**

```js
/**
 * Textos da linha do tempo de alertas (RF10): o que aconteceu, quando e
 * por quanto tempo. A queda da EC2 é registrada com device_id 'fiware'.
 */
import { ID_FIWARE } from '../constants.js';
import { ATRIBUTO } from './atributos.js';
import { formatarNumero } from './numero.js';

/** Duração em texto curto; null quer dizer que o alerta ainda está aberto. */
export function duracao(segundos) {
  if (segundos === null || segundos === undefined) {
    return 'em aberto';
  }
  if (segundos < 60) {
    return `${segundos} s`;
  }
  if (segundos < 3600) {
    return `${Math.floor(segundos / 60)} min ${segundos % 60} s`;
  }
  return `${Math.floor(segundos / 3600)} h ${Math.floor((segundos % 3600) / 60)} min`;
}

/** O que aconteceu: "Temperatura 21,4 °C", "Offline" ou "EC2 / FIWARE fora do ar". */
export function rotuloAlerta(alerta) {
  if (alerta.device_id === ID_FIWARE) {
    return 'EC2 / FIWARE fora do ar';
  }
  if (alerta.attr === 'offline') {
    return 'Offline';
  }
  const atributo = ATRIBUTO[alerta.attr];
  if (!atributo) {
    return alerta.attr;
  }
  if (alerta.value === null || alerta.value === undefined) {
    return atributo.rotulo;
  }
  return `${atributo.rotulo} ${formatarNumero(alerta.value)} ${atributo.unidade}`;
}

/** Data e hora curtas (dd/mm HH:mm) no fuso local. */
export function formatarDataHora(iso) {
  return new Date(iso)
    .toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    .replace(', ', ' ');
}
```

- [ ] **Passo 6: rodar e ver passar**

Rode `npm test`. Esperado: 68 passed.

- [ ] **Passo 7: commit**

```bash
git add frontend/src/constants.js frontend/src/lib
git commit -m "feat: adiciona a janela dos graficos e os textos da linha do tempo de alertas"
```

---

## Subtarefa 6.5 — Cliente HTTP (R1)

**Files:** modificar `src/api/client.js`, `src/api/client.test.js`.

**Produz:** `api.getDevice(id)`, `api.getHistory(id, { attr, lastN, dateFrom, dateTo })`, `api.getScore(id)`, `api.getTriggers(id)`, `api.saveTriggers(id, limits)`, `api.sendCommand(id, command)`, `api.getAlerts({ deviceId, limit })`.

- [ ] **Passo 1: escrever os testes que falham, acrescentando ao fim de `src/api/client.test.js`** (o arquivo já tem `respostaJson`, `afterEach` e os imports de `vi`/`api`)

```js
describe('endpoints da Task 6', () => {
  function capturar(resposta = []) {
    const fetchFalso = vi.fn(async () => respostaJson(200, resposta));
    vi.stubGlobal('fetch', fetchFalso);
    return fetchFalso;
  }

  it('histórico com últimos N usa last_n', async () => {
    const fetchFalso = capturar();
    await api.getHistory('vinheria001', { attr: 'temperature', lastN: 50 });
    expect(fetchFalso.mock.calls[0][0]).toBe('/api/devices/vinheria001/history?attr=temperature&last_n=50');
  });

  it('histórico por datas manda date_from e date_to codificados', async () => {
    const fetchFalso = capturar();
    await api.getHistory('vinheria001', {
      attr: 'humidity',
      dateFrom: '2026-10-19T13:00:00.000Z',
      dateTo: '2026-10-19T15:00:00.000Z',
    });
    const url = new URL(fetchFalso.mock.calls[0][0], 'http://painel');
    expect(url.pathname).toBe('/api/devices/vinheria001/history');
    expect(url.searchParams.get('attr')).toBe('humidity');
    expect(url.searchParams.get('date_from')).toBe('2026-10-19T13:00:00.000Z');
    expect(url.searchParams.get('date_to')).toBe('2026-10-19T15:00:00.000Z');
    expect(url.searchParams.has('last_n')).toBe(false);
  });

  it('alertas sem vinheria não mandam device_id; com vinheria, mandam', async () => {
    const fetchFalso = capturar();
    await api.getAlerts({ limit: 100 });
    await api.getAlerts({ deviceId: 'fiware', limit: 20 });
    expect(fetchFalso.mock.calls[0][0]).toBe('/api/alerts?limit=100');
    expect(fetchFalso.mock.calls[1][0]).toBe('/api/alerts?limit=20&device_id=fiware');
  });

  it('salvar a faixa faz PUT com o corpo da faixa', async () => {
    const fetchFalso = capturar({ device_sync: 'enviado' });
    const faixa = { temperature: { min: 12, max: 18 }, humidity: { min: 50, max: 70 }, luminosity: { min: 0, max: 30 } };
    await api.saveTriggers('vinheria001', faixa);
    const [url, opcoes] = fetchFalso.mock.calls[0];
    expect(url).toBe('/api/devices/vinheria001/triggers');
    expect(opcoes.method).toBe('PUT');
    expect(JSON.parse(opcoes.body)).toEqual(faixa);
  });

  it('comando manual faz POST com o nome do comando', async () => {
    const fetchFalso = capturar({});
    await api.sendCommand('vinheria002', 'alert_off');
    const [url, opcoes] = fetchFalso.mock.calls[0];
    expect(url).toBe('/api/devices/vinheria002/commands');
    expect(opcoes.method).toBe('POST');
    expect(JSON.parse(opcoes.body)).toEqual({ command: 'alert_off' });
  });
});
```

- [ ] **Passo 2: rodar e ver falhar**

Rode `npm test -- client`. Esperado: 5 FAIL com `api.getHistory is not a function` (e similares).

- [ ] **Passo 3: em `src/api/client.js`, substituir o bloco `export const api = {...}` inteiro**

```js
/** Caminho de um recurso de uma vinheria (/api/devices/<id><resto>). */
function rotaDevice(deviceId, resto = '') {
  return `/api/devices/${encodeURIComponent(deviceId)}${resto}`;
}

/** Endpoints usados pelo painel (contratos em PLANO-CP5-VINHERIA.md e nas specs das tasks). */
export const api = {
  getConfig: () => request('/api/config'),
  saveConfig: (changes) => request('/api/config', { method: 'PUT', body: changes }),
  getHealth: () => request('/api/config/health'),
  getFleet: () => request('/api/fleet'),
  listDevices: () => request('/api/devices'),
  createDevice: (device) => request('/api/devices', { method: 'POST', body: device }),
  deleteDevice: (deviceId) => request(rotaDevice(deviceId), { method: 'DELETE' }),
  getDevice: (deviceId) => request(rotaDevice(deviceId)),

  /** Histórico do STH-Comet: últimos N pontos (lastN) ou intervalo (dateFrom/dateTo, ISO). */
  getHistory: (deviceId, { attr, lastN, dateFrom, dateTo }) => {
    const query = new URLSearchParams({ attr });
    if (lastN) {
      query.set('last_n', String(lastN));
    } else {
      query.set('date_from', dateFrom);
      query.set('date_to', dateTo);
    }
    return request(rotaDevice(deviceId, `/history?${query}`));
  },

  getScore: (deviceId) => request(rotaDevice(deviceId, '/score')),
  getTriggers: (deviceId) => request(rotaDevice(deviceId, '/triggers')),
  saveTriggers: (deviceId, limits) => request(rotaDevice(deviceId, '/triggers'), { method: 'PUT', body: limits }),
  sendCommand: (deviceId, command) =>
    request(rotaDevice(deviceId, '/commands'), { method: 'POST', body: { command } }),

  /** Alertas do mais novo ao mais velho; sem deviceId, de todas as vinherias e da EC2. */
  getAlerts: ({ deviceId, limit = 100 } = {}) => {
    const query = new URLSearchParams({ limit: String(limit) });
    if (deviceId) {
      query.set('device_id', deviceId);
    }
    return request(`/api/alerts?${query}`);
  },
};
```

- [ ] **Passo 4: rodar e ver passar**

Rode `npm test`. Esperado: 73 passed.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/api
git commit -m "feat: adiciona ao cliente o historico, score, faixa, comandos e alertas"
```

---

## Subtarefa 6.6 — Hooks de leitura e peças novas do kit (R10)

**Files:** criar `src/hooks/useLeitura.js`, `src/hooks/useAlertas.js`; modificar `src/estilo.js`, `ui/formulario.jsx`, `ui/cartoes.jsx`, `ui/base.jsx`.

**Produz:**
- `useLeitura(carregar, intervaloMs = null) -> { dados, erro, carregando, recarregar }`;
- `useAlertas(deviceId, limite)`;
- `ICONE_ATRIBUTO`;
- `Campo({ erro })`, `Seletor({ rotulo, opcoes, ...props })`, `BotoesSegmentados({ rotulo, opcoes, valor, aoMudar })`;
- `Cartao({ para })`, `CartaoKpi({ rodapeAlerta })`.

**Decisão registrada:** o `useLeitura` não reaproveita o `usePolling`. O `usePolling` não reinicia quando a tarefa muda (a janela do gráfico), não lê uma vez só e não guarda estado. Os contexts continuam com o `usePolling`, sem mudança.

- [ ] **Passo 1: criar `src/hooks/useLeitura.js`**

```js
/**
 * Hook de leitura de dados do backend com estado pronto para a tela:
 * { dados, erro, carregando, recarregar }.
 *
 * Com `intervaloMs`, relê em cadeia de setTimeout depois que cada leitura
 * termina (como o usePolling, sem acumular requisições). Com null, lê uma
 * vez sempre que `carregar` muda. `carregar` null não lê nada. Quem chama
 * passa `carregar` de um useCallback: cada função nova recomeça a leitura
 * do zero (ex.: troca da janela do gráfico).
 */
import { useCallback, useEffect, useRef, useState } from 'react';

const INICIAL = { dados: null, erro: null, carregando: true };

export function useLeitura(carregar, intervaloMs = null) {
  const [estado, setEstado] = useState(INICIAL);
  const [versao, setVersao] = useState(0);
  // Para saber se a mudança foi de `carregar` (limpa a tela) ou só um recarregar
  const ultimaCarga = useRef(carregar);

  useEffect(() => {
    if (ultimaCarga.current !== carregar) {
      ultimaCarga.current = carregar;
      setEstado(INICIAL);
    }
    if (!carregar) {
      setEstado({ dados: null, erro: null, carregando: false });
      return undefined;
    }
    let ativo = true;
    let timer = null;
    async function ciclo() {
      try {
        const dados = await carregar();
        if (ativo) {
          setEstado({ dados, erro: null, carregando: false });
        }
      } catch (falha) {
        if (ativo) {
          setEstado((atual) => ({ dados: atual.dados, erro: falha.message, carregando: false }));
        }
      } finally {
        if (ativo && intervaloMs) {
          timer = setTimeout(ciclo, intervaloMs);
        }
      }
    }
    ciclo();
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [carregar, intervaloMs, versao]);

  const recarregar = useCallback(() => setVersao((atual) => atual + 1), []);
  return { ...estado, recarregar };
}
```

- [ ] **Passo 2: criar `src/hooks/useAlertas.js`**

```js
/**
 * Alertas de uma vinheria (ou de todas, com deviceId null), relidos a cada
 * 10 s, para a linha do tempo do detalhe e a página de alertas.
 */
import { useCallback } from 'react';
import { api } from '../api/client.js';
import { LEITURA_POLL_MS } from '../constants.js';
import { useLeitura } from './useLeitura.js';

export function useAlertas(deviceId, limite) {
  const carregar = useCallback(() => api.getAlerts({ deviceId, limit: limite }), [deviceId, limite]);
  return useLeitura(carregar, LEITURA_POLL_MS);
}
```

- [ ] **Passo 3: `src/estilo.js`.** Acrescente `Droplets` e `Sun`, `Thermometer` ao import do `lucide-react` (em ordem alfabética) e, no fim:

```js
// Ícone de cada atributo e dos tipos de alerta (offline da vinheria e queda da EC2)
export const ICONE_ATRIBUTO = {
  temperature: Thermometer,
  humidity: Droplets,
  luminosity: Sun,
  offline: WifiOff,
  fiware: ServerCrash,
};
```

- [ ] **Passo 4: `ui/formulario.jsx`.** Substitua o `Campo` e acrescente `Seletor` e `BotoesSegmentados` ao fim:

```jsx
/** Campo de texto com o rótulo em caixa alta em cima; `erro` aparece embaixo; as demais props vão para o <input>. */
export function Campo({ rotulo, erro, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-overline uppercase text-taupe">{rotulo}</span>
      <input
        aria-invalid={erro ? true : undefined}
        className={`min-h-11 rounded border bg-papel px-3 text-vinho placeholder:text-taupe/70 focus:border-bordo ${erro ? 'border-alerta' : 'border-linha'}`}
        {...props}
      />
      {erro && <span className="text-xs text-alerta">{erro}</span>}
    </label>
  );
}
```

```jsx
/** Lista de escolha com o mesmo visual do Campo; `opcoes` = [{ valor, rotulo }]. */
export function Seletor({ rotulo, opcoes, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-overline uppercase text-taupe">{rotulo}</span>
      <select className="min-h-11 rounded border border-linha bg-papel px-3 text-vinho focus:border-bordo" {...props}>
        {opcoes.map((opcao) => (
          <option key={opcao.valor} value={opcao.valor}>
            {opcao.rotulo}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Botões lado a lado em que só um fica ativo (aria-pressed), como 20 | 50 | 100. */
export function BotoesSegmentados({ rotulo, opcoes, valor, aoMudar }) {
  return (
    <div role="group" aria-label={rotulo} className="inline-flex self-start rounded border border-linha bg-papel p-0.5">
      {opcoes.map((opcao) => {
        const ativo = opcao.valor === valor;
        return (
          <button
            key={opcao.valor}
            type="button"
            aria-pressed={ativo}
            onClick={() => aoMudar(opcao.valor)}
            className={`min-h-11 min-w-11 rounded-sm px-3 text-sm font-medium transition-colors duration-150 ${ativo ? 'bg-bordo text-papel' : 'text-taupe hover:text-bordo'}`}
          >
            {opcao.rotulo}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Passo 5: `ui/cartoes.jsx`.**
  - Acrescente `import { TriangleAlert } from 'lucide-react';`, `import { Link } from 'react-router-dom';` e `import { formatarNumero } from '../../lib/numero.js';`.
  - Apague a função local `formatar`.
  - Substitua `Cartao` e `CartaoKpi` por:

```jsx
/**
 * Cartão do bento. `destaque` = fundo bordô sólido (o cartão vermelho da
 * referência B). Com `para`, o cartão inteiro vira link (React Router) e
 * sobe 2 px no hover.
 */
export function Cartao({ variante = 'padrao', larg = 1, para, className = '', children }) {
  const cores = variante === 'destaque' ? 'border-bordo bg-bordo text-papel' : 'border-linha bg-papel';
  const interativo = para ? 'block transition duration-150 hover:-translate-y-0.5 hover:shadow-media' : '';
  const classes = `min-w-0 animate-entrar overflow-hidden rounded-2xl border p-4 shadow-baixa md:p-6 ${cores} ${interativo} ${LARGURA[larg]} ${className}`;
  if (para) {
    return (
      <Link to={para} className={classes}>
        {children}
      </Link>
    );
  }
  return <section className={classes}>{children}</section>;
}

/**
 * Cartão de indicador: rótulo com ícone, número grande em serifa que conta
 * até o valor, unidade e rodapé. `rodapeAlerta` pinta o rodapé de vermelho
 * com ícone (ex.: valor fora da faixa).
 */
export function CartaoKpi({ rotulo, icone, valor, unidade, rodape, rodapeAlerta = false, variante = 'padrao', larg = 1 }) {
  const exibido = useContagem(valor);
  const invertido = variante === 'destaque';
  const temNumero = typeof exibido === 'number';
  const corRodape = rodapeAlerta ? 'text-alerta' : invertido ? 'text-papel/80' : 'text-taupe';
  return (
    <Cartao variante={variante} larg={larg}>
      <Overline icone={icone} invertido={invertido}>{rotulo}</Overline>
      <p className="mt-3 font-display text-titulo tabular-nums">
        {temNumero ? formatarNumero(exibido, Number.isInteger(valor) ? 0 : 1) : '—'}
        {temNumero && unidade && <span className="ml-1 font-sans text-base">{unidade}</span>}
      </p>
      {rodape && (
        <p className={`mt-2 flex items-center gap-1 text-sm ${corRodape}`}>
          {rodapeAlerta && <TriangleAlert size={14} strokeWidth={1.75} aria-hidden="true" />}
          {rodape}
        </p>
      )}
    </Cartao>
  );
}
```

- [ ] **Passo 6: `ui/base.jsx`.** Importe `caminhoVinheria` de `'../../lib/rotas.js'` e troque o corpo do `LinkVinheria` por:

```jsx
  return <LinkInterno to={caminhoVinheria(deviceId)}>{children}</LinkInterno>;
```

- [ ] **Passo 7: verificar**

```bash
npm test && npm run build          # 73 passed, build ok
wc -l src/components/ui/*.jsx      # cada um < 250
```
No `npm run dev`, `/dispositivos` continua igual: o `Campo` sem `erro` desenha como antes, e o link da vinheria nos toasts continua funcionando.

- [ ] **Passo 8: commit**

```bash
git add frontend/src
git commit -m "feat: adiciona a leitura com polling, o seletor, os botoes segmentados e o cartao-link"
```

---

## Subtarefa 6.7 — Visão geral (R4)

**Files:** criar `src/components/VinheriaCard.jsx`, `src/pages/Overview.jsx`; modificar `src/App.jsx`, `src/pages/Placeholder.jsx`.

- [ ] **Passo 1: criar `src/components/VinheriaCard.jsx`**

```jsx
/**
 * Cartão de uma vinheria na Visão geral (RF12): faixa de rótulo bordô com o
 * nome e o status (como o rótulo do produto na referência A), cidade, valores
 * atuais, score e tempo desde a última leitura. O cartão inteiro leva ao
 * detalhe. Atributo com alerta aberto aparece em vermelho, com ícone.
 */
import { TriangleAlert } from 'lucide-react';
import { ATRIBUTOS } from '../lib/atributos.js';
import { textoVisto } from '../lib/frota.js';
import { formatarNumero } from '../lib/numero.js';
import { caminhoVinheria } from '../lib/rotas.js';
import { Cartao, SeloStatus } from './ui/index.js';

export default function VinheriaCard({ vinheria }) {
  const emAlerta = new Set(vinheria.active_alerts.map((alerta) => alerta.attr));
  return (
    <Cartao larg={2} para={caminhoVinheria(vinheria.device_id)}>
      <div className="-mx-4 -mt-4 flex items-center justify-between gap-3 bg-bordo px-4 py-3 md:-mx-6 md:-mt-6 md:px-6">
        <span className="min-w-0 truncate font-display text-xl text-papel">{vinheria.name}</span>
        <span className="shrink-0 rounded-full bg-papel">
          <SeloStatus status={vinheria.status} />
        </span>
      </div>
      <p className="mt-3 text-sm text-taupe">{vinheria.city}</p>
      <dl className="mt-4 grid grid-cols-3 gap-2">
        {ATRIBUTOS.map(({ chave, abreviado, unidade }) => {
          const valor = vinheria.current[chave];
          const alerta = emAlerta.has(chave);
          return (
            <div key={chave} className="min-w-0">
              <dt className="text-overline uppercase text-taupe">{abreviado}</dt>
              <dd className={`mt-1 flex items-baseline gap-1 font-display text-2xl tabular-nums ${alerta ? 'text-alerta' : 'text-vinho'}`}>
                {alerta && <TriangleAlert size={16} strokeWidth={1.75} className="self-center" aria-label="fora da faixa" />}
                {valor === null || valor === undefined ? '—' : formatarNumero(valor)}
                {valor !== null && valor !== undefined && <span className="font-sans text-sm">{unidade}</span>}
              </dd>
            </div>
          );
        })}
      </dl>
      <p className="mt-4 flex justify-between gap-3 border-t border-linha pt-3 text-sm text-taupe">
        <span>Score {vinheria.score === null || vinheria.score === undefined ? '—' : formatarNumero(vinheria.score, 0)}</span>
        <span>{textoVisto(vinheria)}</span>
      </p>
    </Cartao>
  );
}
```

- [ ] **Passo 2: criar `src/pages/Overview.jsx`**

```jsx
/**
 * Visão geral da frota (RF12): herói da marca, quatro indicadores (total,
 * ok, em alerta, offline) e um cartão por vinheria, com quem precisa de
 * atenção primeiro. Tudo vem do FleetContext (polling de 5 s), sem chamada
 * nova ao backend.
 */
import { CircleCheck, LayoutGrid, TriangleAlert, WifiOff } from 'lucide-react';
import VinheriaCard from '../components/VinheriaCard.jsx';
import { CartaoKpi, Esqueleto, EstadoVazio, GradeBento, Heroi, LinkInterno } from '../components/ui/index.js';
import { IMAGEM_HEROI } from '../constants.js';
import { useFleet } from '../context/FleetContext.jsx';
import { ordenarFrota, resumoFrota } from '../lib/frota.js';

/** Esqueleto enquanto a primeira leitura da frota não chega. */
function Carregando() {
  return (
    <GradeBento>
      <Esqueleto className="h-32" />
      <Esqueleto className="h-32" />
      <Esqueleto className="h-32" />
      <Esqueleto className="h-32" />
      <Esqueleto className="h-56 md:col-span-2" />
      <Esqueleto className="h-56 md:col-span-2" />
    </GradeBento>
  );
}

/** Indicadores e cartões da frota já carregada. */
function Frota({ frota }) {
  const resumo = resumoFrota(frota);
  return (
    <div className="flex flex-col gap-6">
      <GradeBento>
        <CartaoKpi rotulo="Vinherias" icone={LayoutGrid} valor={resumo.total} />
        <CartaoKpi
          rotulo="OK"
          icone={CircleCheck}
          valor={resumo.ok}
          rodape={resumo.configurando > 0 ? `${resumo.configurando} configurando` : undefined}
        />
        <CartaoKpi
          rotulo="Em alerta"
          icone={TriangleAlert}
          valor={resumo.alerta}
          variante={resumo.alerta > 0 ? 'destaque' : 'padrao'}
        />
        <CartaoKpi rotulo="Offline" icone={WifiOff} valor={resumo.offline} />
      </GradeBento>
      <GradeBento>
        {ordenarFrota(frota.vinherias).map((vinheria) => (
          <VinheriaCard key={vinheria.device_id} vinheria={vinheria} />
        ))}
      </GradeBento>
    </div>
  );
}

export default function Overview() {
  const { fleet } = useFleet();
  let conteudo;
  if (!fleet) {
    conteudo = <Carregando />;
  } else if (fleet.vinherias.length === 0) {
    conteudo = (
      <EstadoVazio
        titulo="Nenhuma vinheria cadastrada"
        texto="Cadastre a primeira para começar o monitoramento."
        acao={<LinkInterno to="/dispositivos">Cadastrar vinheria</LinkInterno>}
      />
    );
  } else {
    conteudo = <Frota frota={fleet} />;
  }
  return (
    <section>
      <Heroi titulo="Smart Solutions" subtitulo="Monitoramento de vinherias" imagem={IMAGEM_HEROI} />
      {conteudo}
    </section>
  );
}
```

- [ ] **Passo 3: `src/App.jsx`.** Importe `Overview` de `./pages/Overview.jsx` e troque a rota `/` por `<Route path="/" element={<Overview />} />`.

- [ ] **Passo 4: `src/pages/Placeholder.jsx`.** Remova o modo `heroi`:
  - o parâmetro `heroi = false`;
  - o import de `IMAGEM_HEROI` e de `Heroi`;
  - o ternário, deixando só `<Titulo overline="Em construção">{titulo}</Titulo>`;
  - no comentário do topo, a frase sobre o herói.

- [ ] **Passo 5: verificar**

Rode `npm test && npm run build`. Esperado: 73 passed e build ok. Com o backend:
- `/` mostra o herói, os 4 KPIs contando e um cartão por vinheria;
- o cartão em alerta vem primeiro, e o KPI "Em alerta" fica bordô;
- clicar num cartão abre `/vinherias/<id>` (ainda placeholder);
- com Tab, o cartão inteiro recebe o anel de foco;
- em 375 px, os cartões empilham e os três valores cabem lado a lado.

- [ ] **Passo 6: commit**

```bash
git add frontend/src
git commit -m "feat: adiciona a visao geral com indicadores da frota e cartoes das vinherias"
```

---

## Subtarefa 6.8 — Gráficos e seletor de janela (R3, R6)

**Files:** criar `src/components/SeletorJanela.jsx`, `src/components/SensorChart.jsx`.

- [ ] **Passo 1: anunciar e ler a skill `dataviz`.** Ela confere as escolhas da spec R3 (área + linhas de faixa + marcador de forma); não muda cor nem token.

- [ ] **Passo 2: criar `src/components/SeletorJanela.jsx`**

```jsx
/**
 * Seletor da janela dos gráficos do detalhe (RF05): últimos 20, 50 ou 100
 * pontos, ou um intervalo de datas. Uma janela só para os três gráficos.
 * A janela só muda com dados válidos (parametrosJanela).
 */
import { useState } from 'react';
import { parametrosJanela } from '../lib/serie.js';
import { Botao, BotoesSegmentados, Campo, MensagemErro } from './ui/index.js';

const OPCOES = [
  { valor: '20', rotulo: '20' },
  { valor: '50', rotulo: '50' },
  { valor: '100', rotulo: '100' },
  { valor: 'datas', rotulo: 'Datas' },
];

export default function SeletorJanela({ janela, aoMudar }) {
  const [modo, setModo] = useState(janela.tipo === 'datas' ? 'datas' : String(janela.n));
  const [datas, setDatas] = useState({ de: '', ate: '' });
  const [erro, setErro] = useState(null);

  function escolher(valor) {
    setModo(valor);
    setErro(null);
    if (valor !== 'datas') {
      aoMudar({ tipo: 'ultimos', n: Number(valor) });
    }
  }

  function aplicar(evento) {
    evento.preventDefault();
    const nova = { tipo: 'datas', ...datas };
    const { erro: invalida } = parametrosJanela(nova);
    if (invalida) {
      setErro(invalida);
      return;
    }
    setErro(null);
    aoMudar(nova);
  }

  return (
    <div className="flex flex-col gap-3">
      <BotoesSegmentados rotulo="Janela dos gráficos" opcoes={OPCOES} valor={modo} aoMudar={escolher} />
      {modo === 'datas' && (
        <form onSubmit={aplicar} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Campo rotulo="De" type="datetime-local" value={datas.de} onChange={(e) => setDatas({ ...datas, de: e.target.value })} />
          <Campo rotulo="Até" type="datetime-local" value={datas.ate} onChange={(e) => setDatas({ ...datas, ate: e.target.value })} />
          <Botao type="submit" variante="secundario">
            Aplicar
          </Botao>
        </form>
      )}
      <MensagemErro erro={erro} />
    </div>
  );
}
```

- [ ] **Passo 3: criar `src/components/SensorChart.jsx`**

```jsx
/**
 * Gráfico do histórico de um atributo (RF05), lido do STH-Comet pelo
 * backend: área em gradiente bordô (referência B), linhas tracejadas no
 * mínimo e no máximo da faixa e um círculo vermelho em cada ponto fora
 * dela (forma, não só cor). Com a janela "últimos N", relê a cada 10 s.
 */
import { useCallback, useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import { api } from '../api/client.js';
import { LEITURA_POLL_MS } from '../constants.js';
import { useLeitura } from '../hooks/useLeitura.js';
import { ATRIBUTO } from '../lib/atributos.js';
import { foraDaFaixa } from '../lib/faixa.js';
import { gradienteVertical } from '../lib/graficos.js';
import { prefereMenosMovimento } from '../lib/movimento.js';
import { formatarNumero } from '../lib/numero.js';
import { paraSerie, parametrosJanela } from '../lib/serie.js';
import { corDoTema } from '../lib/tema.js';
import { Cartao, Esqueleto, EstadoVazio, MensagemErro, Subtitulo } from './ui/index.js';

/** Série tracejada horizontal no valor de um limite da faixa. */
function linhaDeLimite(rotulo, valor, quantidade) {
  return {
    label: rotulo,
    data: Array(quantidade).fill(valor),
    borderColor: corDoTema('taupe'),
    borderWidth: 1.5,
    borderDash: [6, 4],
    pointRadius: 0,
    fill: false,
  };
}

/** Dados do Chart.js: a leitura (com área e marcadores) e, havendo faixa, as linhas de mín e máx. */
function montarDados(pontos, faixa) {
  const { rotulos, valores } = paraSerie(pontos);
  const alerta = corDoTema('alerta');
  const datasets = [
    {
      label: 'leitura',
      data: valores,
      borderColor: corDoTema('bordo'),
      borderWidth: 2,
      tension: 0.3,
      fill: true,
      backgroundColor: gradienteVertical(corDoTema('bordo', 0.35), corDoTema('bordo', 0)),
      pointRadius: valores.map((valor) => (foraDaFaixa(valor, faixa) ? 4 : 0)),
      pointBackgroundColor: alerta,
      pointBorderColor: alerta,
    },
  ];
  if (faixa) {
    datasets.push(linhaDeLimite('mín', faixa.min, valores.length), linhaDeLimite('máx', faixa.max, valores.length));
  }
  return { labels: rotulos, datasets };
}

/** Opções do Chart.js nas cores e na fonte do design system. */
function montarOpcoes(unidade) {
  const taupe = corDoTema('taupe');
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: prefereMenosMovimento() ? false : { duration: 250 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { labels: { color: taupe, boxWidth: 16, filter: (item) => item.datasetIndex > 0 } },
      tooltip: {
        filter: (item) => item.datasetIndex === 0,
        callbacks: { label: (item) => `${formatarNumero(item.parsed.y)} ${unidade}` },
      },
    },
    scales: {
      x: { ticks: { color: taupe, maxTicksLimit: 6, maxRotation: 0 }, grid: { display: false } },
      y: { ticks: { color: taupe }, grid: { color: corDoTema('linha') } },
    },
  };
}

export default function SensorChart({ deviceId, attr, janela, faixa }) {
  const atributo = ATRIBUTO[attr];
  const carregar = useCallback(
    () => api.getHistory(deviceId, { attr, ...parametrosJanela(janela) }),
    [deviceId, attr, janela],
  );
  const { dados, erro, carregando } = useLeitura(carregar, janela.tipo === 'ultimos' ? LEITURA_POLL_MS : null);
  const grafico = useMemo(() => (dados ? montarDados(dados, faixa) : null), [dados, faixa]);
  const opcoes = useMemo(() => montarOpcoes(atributo.unidade), [atributo.unidade]);

  let corpo;
  if (carregando && !dados) {
    corpo = <Esqueleto className="h-full" />;
  } else if (dados && dados.length === 0) {
    corpo = <EstadoVazio titulo="Sem leituras nesta janela" />;
  } else if (grafico) {
    corpo = <Line data={grafico} options={opcoes} role="img" aria-label={`Gráfico de ${atributo.rotulo.toLowerCase()}`} />;
  }

  return (
    <Cartao larg={4}>
      <Subtitulo>{atributo.rotulo}</Subtitulo>
      <MensagemErro erro={erro} />
      <div className="h-56 md:h-72">{corpo}</div>
    </Cartao>
  );
}
```

- [ ] **Passo 4: verificar**

Rode `npm test && npm run build`. Esperado: 73 passed e build ok. A conferência visual fica na 6.12, quando a página do detalhe existir.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/components/SeletorJanela.jsx frontend/src/components/SensorChart.jsx
git commit -m "feat: adiciona os graficos do historico com a faixa e o seletor de janela"
```

---

## Subtarefa 6.9 — Score, faixa e alerta manual (R5.4, R7, R8)

**Files:** criar `src/components/GaugeScore.jsx`, `src/components/TriggerPanel.jsx`, `src/components/PainelComandos.jsx`.

- [ ] **Passo 1: criar `src/components/GaugeScore.jsx`**

```jsx
/**
 * Score de qualidade da vinheria (RF11) em rosca, no cartão bordô de
 * destaque (a rosca de uptime da referência B). O número central conta até
 * o valor; abaixo, a nota de cada atributo. Sem score, mostra "—" e o
 * motivo que o backend explica.
 */
import { Gauge } from 'lucide-react';
import { Doughnut } from 'react-chartjs-2';
import { useContagem } from '../hooks/useContagem.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import '../lib/graficos.js';
import { prefereMenosMovimento } from '../lib/movimento.js';
import { formatarNumero } from '../lib/numero.js';
import { corDoTema } from '../lib/tema.js';
import { Cartao, Esqueleto, Overline } from './ui/index.js';

/** "T 100 · U 85 · L 92" a partir das notas por atributo. */
function notas(attrs) {
  return ATRIBUTOS.map(({ chave, curto }) => {
    const nota = attrs[chave];
    return `${curto} ${nota === null || nota === undefined ? '—' : formatarNumero(nota, 0)}`;
  }).join(' · ');
}

export default function GaugeScore({ relatorio }) {
  const valor = relatorio?.score ?? null;
  const exibido = useContagem(valor);
  const preenchido = valor ?? 0;
  const dados = {
    datasets: [
      {
        data: [preenchido, 100 - preenchido],
        backgroundColor: [corDoTema('papel'), corDoTema('papel', 0.2)],
        borderWidth: 0,
      },
    ],
  };
  const opcoes = {
    cutout: '78%',
    responsive: true,
    maintainAspectRatio: false,
    animation: prefereMenosMovimento() ? false : { duration: 450 },
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
  };

  return (
    <Cartao variante="destaque">
      <Overline icone={Gauge} invertido>
        Score de qualidade
      </Overline>
      {!relatorio ? (
        <Esqueleto className="mx-auto mt-4 size-40 rounded-full" />
      ) : (
        <>
          <div
            className="relative mx-auto mt-4 size-40"
            role="img"
            aria-label={valor === null ? 'Score indisponível' : `Score ${formatarNumero(valor, 0)} de 100`}
          >
            <Doughnut data={dados} options={opcoes} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-titulo tabular-nums">
                {typeof exibido === 'number' ? formatarNumero(exibido, 0) : '—'}
              </span>
              <span className="text-overline uppercase text-papel/80">de 100</span>
            </div>
          </div>
          <p className="mt-3 text-center text-sm text-papel/80">
            {valor === null ? relatorio.message : notas(relatorio.attrs)}
          </p>
        </>
      )}
    </Cartao>
  );
}
```

- [ ] **Passo 2: criar `src/components/TriggerPanel.jsx`**

```jsx
/**
 * Faixa ideal da vinheria (RF06): mínimo e máximo de cada atributo. A mesma
 * faixa é limite dos alertas e referência do score. Valida no navegador
 * (números, mínimo < máximo) e salva pelo backend, que grava no Orion e
 * manda o set_limits ao ESP32; offline, o envio fica pendente.
 */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { useLeitura } from '../hooks/useLeitura.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import { validarFaixa } from '../lib/faixa.js';
import { Botao, Campo, Cartao, Esqueleto, MensagemErro, Subtitulo } from './ui/index.js';

const SUCESSO = {
  enviado: 'Faixa salva e enviada ao ESP32.',
  pendente: 'Faixa salva. O ESP32 recebe quando voltar a ficar online.',
};

const LIMITES = [
  ['min', 'Mín'],
  ['max', 'Máx'],
];

/** Faixa do backend (números) para os campos do formulário (texto). */
function paraCampos(faixa) {
  return Object.fromEntries(
    ATRIBUTOS.map(({ chave }) => [chave, { min: String(faixa[chave].min), max: String(faixa[chave].max) }]),
  );
}

export default function TriggerPanel({ deviceId, onSalvo }) {
  const carregar = useCallback(() => api.getTriggers(deviceId), [deviceId]);
  const { dados, erro: erroLeitura } = useLeitura(carregar);
  const [campos, setCampos] = useState(null);
  const [erros, setErros] = useState({});
  const [aviso, setAviso] = useState(null);
  const salvar = useAcao(api.saveTriggers);

  useEffect(() => {
    if (dados) {
      setCampos(paraCampos(dados));
    }
  }, [dados]);

  function alterar(chave, limite, valor) {
    setCampos((atuais) => ({ ...atuais, [chave]: { ...atuais[chave], [limite]: valor } }));
  }

  async function aoSalvar(evento) {
    evento.preventDefault();
    setAviso(null);
    const { dados: faixa, erros: invalidos } = validarFaixa(campos);
    setErros(invalidos);
    if (!faixa) {
      return;
    }
    const resultado = await salvar.executar(deviceId, faixa);
    if (resultado.ok) {
      setAviso(SUCESSO[resultado.valor.device_sync]);
      onSalvo();
    }
  }

  return (
    <Cartao larg={2}>
      <Subtitulo>Faixa ideal</Subtitulo>
      <MensagemErro erro={erroLeitura} />
      {!campos ? (
        <Esqueleto className="h-64" />
      ) : (
        <form onSubmit={aoSalvar} className="flex flex-col gap-4" noValidate>
          {ATRIBUTOS.map(({ chave, rotulo, unidade }) => (
            <fieldset key={chave}>
              <legend className="mb-2 text-overline uppercase text-taupe">{`${rotulo} (${unidade})`}</legend>
              <div className="grid grid-cols-2 gap-3">
                {LIMITES.map(([limite, nome]) => (
                  <Campo
                    key={limite}
                    rotulo={nome}
                    inputMode="decimal"
                    value={campos[chave][limite]}
                    onChange={(e) => alterar(chave, limite, e.target.value)}
                    erro={erros[`${chave}.${limite}`]}
                  />
                ))}
              </div>
            </fieldset>
          ))}
          <MensagemErro erro={salvar.erro} />
          {aviso && (
            <p role="status" className="text-sm text-ok">
              {aviso}
            </p>
          )}
          <Botao type="submit" className="w-full" carregando={salvar.executando} textoCarregando="Salvando…">
            Salvar faixa
          </Botao>
        </form>
      )}
    </Cartao>
  );
}
```

- [ ] **Passo 3: criar `src/components/PainelComandos.jsx`**

```jsx
/**
 * Alerta manual (RF09): dispara pelo painel o padrão de luz e som de cada
 * anomalia no ESP32, ou desliga o alerta. O backend recusa (409) vinheria
 * offline ou ainda sem faixa; aqui os botões já ficam desabilitados nesses
 * estados, com o motivo escrito.
 */
import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import { Botao, Cartao, MensagemErro, Nota, Subtitulo } from './ui/index.js';

const BLOQUEIO = {
  offline: 'Vinheria offline: os comandos voltam quando ela reconectar.',
  configurando: 'Vinheria aguardando a faixa (configurando).',
};

// Quanto tempo o "Comando enviado." fica na tela
const AVISO_MS = 4000;

export default function PainelComandos({ deviceId, status }) {
  const enviar = useAcao(api.sendCommand);
  const [ativo, setAtivo] = useState(null);
  const [enviado, setEnviado] = useState(false);
  const bloqueio = Object.hasOwn(BLOQUEIO, status) ? BLOQUEIO[status] : null;

  useEffect(() => {
    if (!enviado) {
      return undefined;
    }
    const timer = setTimeout(() => setEnviado(false), AVISO_MS);
    return () => clearTimeout(timer);
  }, [enviado]);

  async function disparar(comando) {
    setAtivo(comando);
    setEnviado(false);
    const resultado = await enviar.executar(deviceId, comando);
    setAtivo(null);
    if (resultado.ok) {
      setEnviado(true);
    }
  }

  const desabilitado = bloqueio !== null || ativo !== null;
  return (
    <Cartao larg={2}>
      <Subtitulo>Alerta manual</Subtitulo>
      {bloqueio && <Nota>{bloqueio}</Nota>}
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {ATRIBUTOS.map(({ comando, botao }) => (
          <Botao
            key={comando}
            variante="secundario"
            disabled={desabilitado}
            carregando={ativo === comando}
            textoCarregando="Enviando…"
            onClick={() => disparar(comando)}
          >
            {botao}
          </Botao>
        ))}
      </div>
      <Botao
        variante="perigo"
        className="mt-3 w-full"
        disabled={desabilitado}
        carregando={ativo === 'alert_off'}
        textoCarregando="Enviando…"
        onClick={() => disparar('alert_off')}
      >
        Desligar alerta
      </Botao>
      <div className="mt-3">
        <MensagemErro erro={enviar.erro} />
      </div>
      {enviado && (
        <p role="status" className="text-sm text-ok">
          Comando enviado.
        </p>
      )}
    </Cartao>
  );
}
```

- [ ] **Passo 4: verificar**

Rode `npm test && npm run build`. Esperado: 73 passed e build ok.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/components/GaugeScore.jsx frontend/src/components/TriggerPanel.jsx frontend/src/components/PainelComandos.jsx
git commit -m "feat: adiciona o score em rosca, a faixa editavel e o alerta manual"
```

---

## Subtarefa 6.10 — Linha do tempo e página de alertas (R9)

**Files:** criar `src/components/AlertTimeline.jsx`, `src/pages/Alerts.jsx`; modificar `src/App.jsx`.

- [ ] **Passo 1: criar `src/components/AlertTimeline.jsx`**

```jsx
/**
 * Linha do tempo de alertas (RF10): ícone do tipo, o que aconteceu, início,
 * fim (ou "em aberto" pulsando) e duração. Mostra a vinheria de cada alerta
 * quando a lista mistura várias. Recebe a leitura pronta (useAlertas).
 */
import { ID_FIWARE } from '../constants.js';
import { ICONE_ATRIBUTO } from '../estilo.js';
import { duracao, formatarDataHora, rotuloAlerta } from '../lib/alertas.js';
import { Esqueleto, LinkVinheria, MensagemErro, Nota } from './ui/index.js';

/** Nome da vinheria com link, ou "EC2" para a queda do FIWARE. */
function Origem({ deviceId, nomes }) {
  if (deviceId === ID_FIWARE) {
    return <span className="text-taupe">EC2</span>;
  }
  return <LinkVinheria deviceId={deviceId}>{nomes[deviceId] ?? deviceId}</LinkVinheria>;
}

/** Selo "em aberto" com o ponto pulsando. */
function EmAberto() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-alerta/10 px-2 text-alerta">
      <span className="size-1.5 animate-pulsar rounded-full bg-alerta" aria-hidden="true" />
      em aberto
    </span>
  );
}

export default function AlertTimeline({ leitura, mostrarVinheria = false, nomes = {} }) {
  const { dados, erro, carregando } = leitura;
  if (carregando && !dados) {
    return <Esqueleto className="h-40" />;
  }
  return (
    <>
      <MensagemErro erro={erro} />
      {dados && dados.length === 0 && <Nota>Nenhum alerta registrado.</Nota>}
      <ol className="flex flex-col">
        {(dados ?? []).map((alerta) => {
          const Icone = ICONE_ATRIBUTO[alerta.device_id === ID_FIWARE ? ID_FIWARE : alerta.attr];
          const aberto = alerta.closed_at === null || alerta.closed_at === undefined;
          return (
            <li
              key={alerta.id}
              className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 border-b border-linha py-3 last:border-b-0 md:grid-cols-[auto_minmax(0,1fr)_auto_6rem] md:items-center md:gap-x-6"
            >
              <Icone
                size={20}
                strokeWidth={1.5}
                aria-hidden="true"
                className={`row-span-3 mt-0.5 md:row-span-1 md:mt-0 ${aberto ? 'text-alerta' : 'text-taupe'}`}
              />
              <div className="min-w-0">
                <p className="font-medium text-vinho">{rotuloAlerta(alerta)}</p>
                {mostrarVinheria && (
                  <p className="text-sm">
                    <Origem deviceId={alerta.device_id} nomes={nomes} />
                  </p>
                )}
              </div>
              <p className="text-sm text-taupe tabular-nums">
                {formatarDataHora(alerta.opened_at)} → {aberto ? <EmAberto /> : formatarDataHora(alerta.closed_at)}
              </p>
              <p className="text-sm text-taupe tabular-nums md:text-right">{aberto ? '' : duracao(alerta.duration_seconds)}</p>
            </li>
          );
        })}
      </ol>
    </>
  );
}
```

- [ ] **Passo 2: criar `src/pages/Alerts.jsx`**

```jsx
/**
 * Histórico de alertas (RF10): linha do tempo geral, filtrável por vinheria
 * ou pela EC2. O filtro mora na URL (?vinheria=), então o link pode ser
 * compartilhado e o Voltar do navegador desfaz a troca.
 */
import { BellRing, CircleDot } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import AlertTimeline from '../components/AlertTimeline.jsx';
import { Cartao, CartaoKpi, GradeBento, Seletor, Titulo } from '../components/ui/index.js';
import { ID_FIWARE } from '../constants.js';
import { useFleet } from '../context/FleetContext.jsx';
import { useAlertas } from '../hooks/useAlertas.js';

const LIMITE = 100;

export default function Alerts() {
  const { fleet } = useFleet();
  const [params, setParams] = useSearchParams();
  const filtro = params.get('vinheria') ?? '';
  const leitura = useAlertas(filtro || null, LIMITE);

  const vinherias = fleet?.vinherias ?? [];
  const nomes = Object.fromEntries(vinherias.map((v) => [v.device_id, v.name]));
  const opcoes = [
    { valor: '', rotulo: 'Todas as vinherias' },
    ...vinherias.map((v) => ({ valor: v.device_id, rotulo: `${v.name} · ${v.city}` })),
    { valor: ID_FIWARE, rotulo: 'EC2 / FIWARE' },
  ];
  const lista = leitura.dados ?? [];
  const abertos = lista.filter((alerta) => alerta.closed_at === null || alerta.closed_at === undefined).length;

  function trocar(evento) {
    const valor = evento.target.value;
    setParams(valor ? { vinheria: valor } : {});
  }

  return (
    <section>
      <Titulo overline="Histórico">Alertas</Titulo>
      <GradeBento>
        <Cartao larg={2}>
          <Seletor rotulo="Vinheria" opcoes={opcoes} value={filtro} onChange={trocar} />
        </Cartao>
        <CartaoKpi
          rotulo="Em aberto"
          icone={CircleDot}
          valor={leitura.dados ? abertos : null}
          variante={abertos > 0 ? 'destaque' : 'padrao'}
        />
        <CartaoKpi
          rotulo="Registrados"
          icone={BellRing}
          valor={leitura.dados ? lista.length : null}
          rodape={`últimos ${LIMITE}`}
        />
        <Cartao larg={4}>
          <AlertTimeline leitura={leitura} mostrarVinheria={!filtro} nomes={nomes} />
        </Cartao>
      </GradeBento>
    </section>
  );
}
```

- [ ] **Passo 3: `src/App.jsx`.** Importe `Alerts` e troque a rota `/alertas` por `<Route path="/alertas" element={<Alerts />} />`.

- [ ] **Passo 4: verificar**

Rode `npm test && npm run build`. Esperado: 73 passed e build ok. Em `/alertas`:
- a lista aparece com ícone, texto, início → fim e duração;
- o alerta offline da `vinheria002` mostra "em aberto" pulsando;
- trocar o filtro muda a URL para `?vinheria=...`, e o Voltar do navegador volta para "Todas";
- "EC2 / FIWARE" filtra as quedas da EC2;
- em 375 px, cada alerta ocupa 3 linhas, com o ícone à esquerda e sem rolagem horizontal.

- [ ] **Passo 5: commit**

```bash
git add frontend/src
git commit -m "feat: adiciona a linha do tempo e a pagina de alertas com filtro por vinheria"
```

---

## Subtarefa 6.11 — Detalhe da vinheria (R5)

**Files:** criar `src/pages/VinheriaDetail.jsx`; modificar `src/App.jsx`.

- [ ] **Passo 1: criar `src/pages/VinheriaDetail.jsx`**

```jsx
/**
 * Detalhe de uma vinheria (RF04, RF05, RF06, RF09, RF10, RF11): cabeçalho
 * com status, score em rosca, valores atuais com a faixa, três gráficos do
 * STH-Comet com uma janela comum, faixa editável, alerta manual e a linha
 * do tempo da vinheria. Nome, status e valores vêm do FleetContext; score,
 * histórico e alertas são lidos aqui a cada 10 s.
 */
import { ArrowLeft } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import AlertTimeline from '../components/AlertTimeline.jsx';
import GaugeScore from '../components/GaugeScore.jsx';
import PainelComandos from '../components/PainelComandos.jsx';
import SeletorJanela from '../components/SeletorJanela.jsx';
import SensorChart from '../components/SensorChart.jsx';
import TriggerPanel from '../components/TriggerPanel.jsx';
import {
  Cartao,
  CartaoKpi,
  Esqueleto,
  EstadoVazio,
  GradeBento,
  LinkInterno,
  Overline,
  SeloStatus,
  Subtitulo,
  Titulo,
} from '../components/ui/index.js';
import { JANELA_PADRAO, LEITURA_POLL_MS } from '../constants.js';
import { useFleet } from '../context/FleetContext.jsx';
import { ICONE_ATRIBUTO } from '../estilo.js';
import { useAlertas } from '../hooks/useAlertas.js';
import { useLeitura } from '../hooks/useLeitura.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import { foraDaFaixa } from '../lib/faixa.js';
import { textoVisto } from '../lib/frota.js';
import { formatarNumero } from '../lib/numero.js';

/** Id fora da frota: recém-cadastrada (aguardando o 1º ciclo) ou inexistente. */
function VinheriaAusente({ id }) {
  const carregar = useCallback(() => api.getDevice(id), [id]);
  const { dados, erro, carregando } = useLeitura(carregar);
  if (carregando) {
    return <Esqueleto className="h-64" />;
  }
  if (dados) {
    return (
      <EstadoVazio
        titulo={dados.name}
        texto="Aguardando o primeiro ciclo do monitoramento. Os dados aparecem em alguns segundos."
      />
    );
  }
  return (
    <EstadoVazio
      titulo="Vinheria não encontrada"
      texto={erro}
      acao={<LinkInterno to="/">Voltar para a Visão geral</LinkInterno>}
    />
  );
}

/** Valor atual de um atributo com a faixa no rodapé (vermelho quando fora). */
function KpiAtributo({ atributo, valor, faixa }) {
  const fora = foraDaFaixa(valor, faixa);
  const rodape = faixa
    ? `${fora ? 'Fora da faixa' : 'Faixa'} ${formatarNumero(faixa.min)}–${formatarNumero(faixa.max)} ${atributo.unidade}`
    : undefined;
  return (
    <CartaoKpi
      rotulo={atributo.rotulo}
      icone={ICONE_ATRIBUTO[atributo.chave]}
      valor={valor ?? null}
      unidade={atributo.unidade}
      rodape={rodape}
      rodapeAlerta={fora}
    />
  );
}

export default function VinheriaDetail() {
  const { id } = useParams();
  const { fleet } = useFleet();
  const vinheria = fleet?.vinherias.find((v) => v.device_id === id) ?? null;
  const carregarScore = useCallback(() => api.getScore(id), [id]);
  const score = useLeitura(vinheria ? carregarScore : null, LEITURA_POLL_MS);
  const alertas = useAlertas(id, 20);
  const [janela, setJanela] = useState(JANELA_PADRAO);

  if (!fleet) {
    return <Esqueleto className="h-64" />;
  }
  if (!vinheria) {
    return <VinheriaAusente id={id} />;
  }
  const limites = score.dados?.limits ?? null;

  return (
    <section className="flex flex-col gap-6">
      <div>
        <LinkInterno to="/">
          <span className="inline-flex min-h-11 items-center gap-1">
            <ArrowLeft size={16} aria-hidden="true" />
            Visão geral
          </span>
        </LinkInterno>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <Titulo overline={vinheria.city}>{vinheria.name}</Titulo>
          <div className="flex flex-col items-start gap-1 md:items-end">
            <SeloStatus status={vinheria.status} />
            <span className="text-sm text-taupe">{textoVisto(vinheria)}</span>
          </div>
        </div>
      </div>

      <GradeBento>
        <GaugeScore relatorio={score.dados} />
        {ATRIBUTOS.map((atributo) => (
          <KpiAtributo
            key={atributo.chave}
            atributo={atributo}
            valor={vinheria.current[atributo.chave]}
            faixa={limites?.[atributo.chave] ?? null}
          />
        ))}
      </GradeBento>

      <div className="flex flex-col gap-2">
        <Overline>Janela dos gráficos</Overline>
        <SeletorJanela janela={janela} aoMudar={setJanela} />
      </div>

      <GradeBento>
        {ATRIBUTOS.map(({ chave }) => (
          <SensorChart key={chave} deviceId={id} attr={chave} janela={janela} faixa={limites?.[chave] ?? null} />
        ))}
        <TriggerPanel deviceId={id} onSalvo={score.recarregar} />
        <PainelComandos deviceId={id} status={vinheria.status} />
        <Cartao larg={4}>
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <Subtitulo>Linha do tempo</Subtitulo>
            <LinkInterno to={`/alertas?vinheria=${encodeURIComponent(id)}`}>Ver todos os alertas</LinkInterno>
          </div>
          <AlertTimeline leitura={alertas} />
        </Cartao>
      </GradeBento>
    </section>
  );
}
```

- [ ] **Passo 2: `src/App.jsx`.** Importe `VinheriaDetail` e troque a rota `/vinherias/:id` por `<Route path="/vinherias/:id" element={<VinheriaDetail />} />`. Atualize o comentário do topo: só `/chat` continua `Placeholder`.

- [ ] **Passo 3: verificar**

```bash
npm test && npm run build                              # 73 passed, build ok
wc -l src/pages/VinheriaDetail.jsx src/components/*.jsx   # nenhum acima de ~250
```
Com o backend, a EC2 e o Wokwi, em `/vinherias/vinheria001`:
- a rosca mostra o score e as notas;
- os 3 KPIs mostram o valor e a faixa;
- os 3 gráficos desenham a área bordô com as linhas tracejadas de mín e máx, e se atualizam a cada 10 s;
- "Datas" com início depois do fim mostra o erro;
- salvar a faixa mostra "Faixa salva e enviada ao ESP32" e move as linhas;
- "Piscar luz" mostra "Comando enviado.";
- `/vinherias/vinheria999` mostra "Vinheria não encontrada".

- [ ] **Passo 4: commit**

```bash
git add frontend/src
git commit -m "feat: adiciona o detalhe da vinheria com score, graficos, faixa, comandos e alertas"
```

---

## Subtarefa 6.12 — Auditoria visual (`impeccable-design-polish`)

- [ ] **Passo 1: anunciar e rodar a skill `impeccable-design-polish`** sobre `/`, `/vinherias/vinheria001` e `/alertas`. Use capturas do Edge headless, como na 5B.12, uma de cada vez e com perfil isolado:

```bash
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
timeout 60 "$EDGE" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="<scratchpad>/prof-x" --window-size=1280,1600 --virtual-time-budget=8000 --screenshot="<scratchpad>/detalhe-d.png" http://localhost:5173/vinherias/vinheria001
```
Capture em 500 e 1280 px de largura.

- [ ] **Passo 2: registrar os achados** no fim deste plano (`# | tela | achado | ação`), classificando cada um como **corrigir agora** (cabe nos tokens e componentes), **Task 7A/7B** ou **devolver ao planejamento** (exige decisão nova; nesse caso, pare e reporte).

- [ ] **Passo 3: corrigir os "corrigir agora"**, um commit `fix:` por achado, com `npm test && npm run build` depois de cada um.

- [ ] **Passo 4: commit do registro**

```bash
git add docs/specs/task-6-visao-geral-graficos/plan.md
git commit -m "docs: registra os achados da auditoria de design da task 6"
```

---

## Subtarefa 6.13 — Verificação final e fechamento

- [ ] **Passo 1: suíte e build**

```bash
cd frontend
npm test        # 73 passed
npm run build   # sem erro
cd ../backend && .venv/Scripts/python -m pytest tests -q   # 285 passed (nada mudou)
```

- [ ] **Passo 2: conferências estáticas**

```bash
cd ../frontend
grep -rnE "#[0-9a-fA-F]{3,8}\b|rgb\(" src --include=*.jsx            # esperado: nada
grep -rnE "#[0-9a-fA-F]{6}\b" src --include=*.js | grep -v test       # esperado: nada (cores só no styles.css)
grep -rn "style={" src                                                # esperado: nada
grep -rln "fetch(" src                                                # esperado: só src/api/client.js e client.test.js
grep -rn "<h1\|<h2\|<input\|<select\|<button" src --include=*.jsx | grep -v "components/ui/"   # esperado: nada
grep -rn "/vinherias/\${" src | grep -v "lib/rotas.js"                # esperado: nada
find src -name "*.js*" | xargs wc -l | sort -n | tail -5              # nenhum acima de ~250
```

- [ ] **Passo 3: ensaio manual** (backend, EC2 e 2 Wokwi ligados). Os itens da spec §7.5:
  1. esquentar o DHT da `vinheria002`: só ela reage (cartão no topo, KPI "Em alerta" bordô, gráfico com círculo vermelho, linha do tempo "em aberto", ESP32 apitando);
  2. baixar o máximo de temperatura abaixo do valor atual e salvar: as linhas descem, o alerta dispara e o LCD mostra a faixa;
  3. "Piscar luz" e "Desligar alerta" no ESP32;
  4. parar um Wokwi: o cartão fica offline, os comandos ficam desabilitados e a linha do tempo mostra "Offline em aberto";
  5. filtro em `/alertas` e o Voltar;
  6. janela "Datas" inválida e válida.

  Anote o que divergir. Se o ensaio não puder ser feito (EC2 desligada), registre como pendente.

- [ ] **Passo 4: documentar**
  - Em `PLANO-CP5-VINHERIA.md`, sob o título da Task 6, acrescente `> **6 FEITA em <data>** — commits <primeiro>..<último>; 73 testes do front; desvios: …; ensaio manual: …`.
  - No topo deste plano, acrescente `> **Estado em <data>:** …`.

- [ ] **Passo 5: commit**

```bash
git add PLANO-CP5-VINHERIA.md docs/specs/task-6-visao-geral-graficos/plan.md
git commit -m "docs: fecha a task 6 com a visao geral, o detalhe e os alertas"
```

---

## Achados da auditoria 6 (subtarefa 6.12, 20/10/2026)

Auditoria feita sobre capturas do Edge headless de `/` (500 e 1280 px), `/vinherias/vinheria001` (1280 px) e `/alertas` (1280 px). A EC2 estava desligada, então as telas foram vistas com **dados sintéticos**: um backend de mentira só no scratchpad (porta 8001, fora do repositório) e um segundo Vite apontando para ele; ambos foram encerrados ao fim. O detalhe em 500 px e as telas com dados reais ficam para o ensaio manual da 6.13.

| # | tela | achado | ação |
|---|---|---|---|
| 1 | detalhe, gráficos | A legenda "mín/máx" desenhava caixas quebradas no lugar de traços. | corrigido: `usePointStyle` com `pointStyle: 'line'` (commit `fix: troca as caixas da legenda…`) |
| 2 | detalhe, topo | Os três cartões de valor esticam até a altura da rosca e ficam com espaço vazio embaixo. | aceito: ritmo do bento; vira ajuste se a Task 7 trouxer mais conteúdo nesses cartões |
| 3 | `/alertas` | O número de "Registrados" aparece no meio da contagem na captura (3 de 4). | sem ação: é o `useContagem` em andamento, a lista tem os 4 itens |
| 4 | `/` e detalhe | Rosca, cartão bordô de alerta, faixa de resumo no celular, selo do menu inferior e cartões ordenados por urgência conferidos. | sem ação |
