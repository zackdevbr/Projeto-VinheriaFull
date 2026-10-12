# Task 5A — Front-end React: base, configuração do FIWARE, aviso global e cadastro — Plano de execução

> **Estado em 12/10/2026:** feitas as subtarefas 5A.1 a 5A.9 (verificações manuais com EC2 e Wokwi pendentes, ver nota na Task 5 do PLANO).

> **Para quem executa (Sonnet):** use `superpowers:executing-plans`. Os passos usam checkbox (`- [ ]`). Execute **uma subtarefa por vez**, informe o resultado de cada passo e **pare para revisão do usuário ao fim de cada subtarefa** (`CLAUDE.md` §2 e §4). Se algo não bater com a spec, pare e devolva para planejamento; não improvise. **Não tome nenhuma decisão visual**: o CSS deste plano é provisório e é o único permitido até a Task 5B.

**Objetivo:** painel React rodando em `http://localhost:5173` com barra Smart Solutions e saúde do FIWARE (IP trocável no painel Avançado), aviso global de alerta/offline com toasts, rotas reservadas para as Tasks 6 e 7A e a tela `/dispositivos` cadastrando e removendo vinherias.

**Arquitetura:** `src/api/client.js` é a única porta para o backend (via proxy do Vite). `src/lib/` guarda a lógica pura e testada (`fleetEvents.js`, `validation.js`). `src/hooks/usePolling.js` faz o polling sem sobrepor requisições. Dois contexts: `ConfigContext` (config + saúde, 30 s) e `FleetContext` (frota + eventos + toasts, 5 s). Componentes só leem os contexts e chamam `api.*`.

**Stack:** React + react-router-dom + Vite + Tailwind CSS v4 (plugin `@tailwindcss/vite`), JavaScript puro; Vitest (só lógica pura, ambiente `node`). Nenhuma mudança no backend.

**Spec:** [`spec.md`](spec.md) — requisitos R1 a R7, fatos F1 a F5, decisões D1 a D13. Leia antes de começar.

## Global Constraints

- Todos os comandos do front rodam de dentro de `frontend/`.
- JavaScript puro: arquivos `.js` e `.jsx`. Nada de TypeScript, nem `jsconfig`/`tsconfig`.
- Componentes e contexts **nunca** chamam `fetch`; usam `api.*` de `src/api/client.js`.
- Nada de URL, IP ou porta em módulo de lógica: o cliente usa caminhos relativos `/api/...`; o destino do proxy vem de `BACKEND_URL`.
- Comentários em português: um bloco no topo de cada arquivo dizendo o propósito, e comentário em cada função não óbvia.
- Nenhum arquivo passa de ~250 linhas.
- **Reaproveitar antes de escrever (sem código redundante):** antes de criar um elemento, função ou trecho de lógica, procure se já existe em `components/ui.jsx`, `hooks/` (`useAcao`, `usePolling`), `context/criarContexto.js`, `lib/` ou `api/client.js` e use. Se o mesmo padrão aparecer pela **segunda** vez, extraia para um desses lugares em vez de copiar. Em especial: ação assíncrona com "carregando/erro" → `useAcao` (nada de `try/catch/finally` em componente ou página); título, campo, botão, erro, texto secundário e link de vinheria → `ui.jsx` (nada de `<h1>`, `<input>`, `<button>` soltos nas telas, salvo o × do toast); contexto novo → `criarContexto`. Se uma peça daqui não servir, **pare e reporte** em vez de criar uma variação paralela.
- **Troca de página só pelo `react-router-dom`:** `NavLink` no menu, `Link` nos links internos e `useNavigate` para navegar por código. Nunca `<a href>` nem `window.location` para páginas do próprio painel (recarregaria a página e perderia os toasts e o estado da frota).
- **Estilo só com Tailwind:** classes utilitárias no `className`. O único arquivo `.css` é `src/styles.css` (importa o Tailwind e define o fundo do `body`); nada de `.css` por componente, nem `style={...}` inline. Classes montadas em tempo de execução precisam aparecer **inteiras** no código (mapas como `{ ok: 'text-green-700' }`), nunca concatenadas (`'text-' + cor`), senão o Tailwind não as gera.
- Nenhuma decisão visual: só os utilitários neutros deste plano (cinzas, bordas, espaçamento) e as cores semânticas de status (verde, vermelho, âmbar, cinza). Cores da marca, fontes e `@theme` são da Task 5B.
- Testes não acessam a rede (o `fetch` é sempre substituído por `vi.stubGlobal`).
- Commits: mensagem em português, imperativo, uma linha, prefixo `feat:`/`test:`/`chore:`/`docs:`, **sem linha de co-author** (`CLAUDE.md` §8 prevalece sobre qualquer lembrete de atribuição).
- Contagem de testes esperada ao fim de cada subtarefa está no passo de verificação; se der diferente, reporte antes de seguir.

## Review Focus

1. **EC2 cai com o painel aberto:** um único toast "EC2/FIWARE fora do ar", não um por vinheria; na volta, um único "EC2/FIWARE de volta". Testes `EC2 cai: um único evento` e `EC2 volta: um único evento` (5A.4).
2. **Backend parado com o painel aberto:** a barra mostra "Backend indisponível" e volta sozinha. Teste `sem corpo JSON e status 5xx` (5A.2) + checagem manual (5A.9).
3. **Cadastro lento (provisionamento):** botão desabilitado com "Provisionando no FIWARE…" e sem duplo envio (5A.8, manual).
4. **Vinheria recém-cadastrada** ainda fora da frota: status "Aguardando 1º ciclo", sem toast falso. Teste `vinheria nova ou removida não gera evento` (5A.4).

---

## Subtarefa 5A.1 — Scaffold Vite + React + Tailwind (R1)

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.js`, `frontend/index.html`, `frontend/src/styles.css`, `frontend/src/main.jsx`, `frontend/.env.example`

- [ ] **Passo 1: criar `frontend/package.json`**

```json
{
  "name": "smart-solutions-painel",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run"
  }
}
```

- [ ] **Passo 2: instalar as dependências**

```bash
cd frontend
npm install react react-dom react-router-dom
npm install -D vite @vitejs/plugin-react vitest tailwindcss @tailwindcss/vite
```

Esperado: `package.json` ganha `dependencies` e `devDependencies`, e aparece `package-lock.json`. O `tailwindcss` instalado deve ser **4.x** (a configuração abaixo é a do v4: plugin do Vite e `@import "tailwindcss"`, sem `tailwind.config.js` nem PostCSS). Se vier 3.x, ou se o npm der `ERESOLVE` (conflito de versões entre `vite`, `vitest` e `@tailwindcss/vite`), **pare e reporte** a mensagem; não use `--force` nem `--legacy-peer-deps`. Informe as versões instaladas.

- [ ] **Passo 3: criar `frontend/vite.config.js`**

```js
/**
 * Configuração do Vite (servidor de desenvolvimento e build) e do Vitest.
 *
 * O painel chama sempre caminhos relativos (/api/...). Aqui o Vite encaminha
 * esses caminhos para o backend FastAPI (proxy), então não há CORS nem
 * endereço do backend dentro do código. O destino vem de BACKEND_URL no
 * frontend/.env; sem ela, usa o backend local na porta 8000.
 * O Tailwind CSS v4 entra pelo plugin oficial do Vite.
 */
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxy = { '/api': env.BACKEND_URL || 'http://localhost:8000' };
  return {
    plugins: [react(), tailwindcss()],
    server: { port: 5173, strictPort: true, proxy },
    preview: { proxy },
    test: { environment: 'node', include: ['src/**/*.test.js'] },
  };
});
```

- [ ] **Passo 4: criar `frontend/index.html`**

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Smart Solutions — Monitoramento de Vinherias</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Passo 5: criar `frontend/src/styles.css`** (o único arquivo CSS do painel)

```css
/*
 * Estilo do painel: Tailwind CSS v4, usado por classes utilitárias no JSX.
 * Na Task 5A o visual é provisório (cinzas e cores de status). A Task 5B
 * acrescenta aqui o @theme com as cores e fontes da marca Smart Solutions.
 */
@import "tailwindcss";

@layer base {
  body {
    @apply bg-white text-gray-900 antialiased;
  }
}
```

- [ ] **Passo 6: criar `frontend/src/main.jsx` provisório**

```jsx
/**
 * Ponto de entrada do painel. Versão provisória da 5A.1: só confirma que o
 * Vite, o React e o Tailwind estão de pé. A 5A.5 liga o roteador e o App.
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <h1 className="p-4 text-2xl font-semibold text-green-700">Smart Solutions</h1>
  </StrictMode>,
);
```

- [ ] **Passo 7: criar `frontend/.env.example`**

```
# Endereço do backend FastAPI usado pelo proxy do Vite.
# Vazio = http://localhost:8000. Copie para frontend/.env se precisar mudar.
BACKEND_URL=
```

- [ ] **Passo 8: verificar**

```bash
npm run build
```
Esperado: `dist/` gerado sem erro, com um `.css` em `dist/assets/` contendo `text-green-700` (prova de que o Tailwind gerou a classe usada). Depois `npm run dev`, abrir `http://localhost:5173`: aba com o título "Smart Solutions — Monitoramento de Vinherias" e o texto "Smart Solutions" **grande, em negrito e verde, com espaçamento** (sem Tailwind ele sairia como um `h1` sem margem). Parar o servidor. `git status` não deve listar `node_modules/` nem `dist/`.

- [ ] **Passo 9: commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/index.html frontend/src/styles.css frontend/src/main.jsx frontend/.env.example
git commit -m "chore: cria o projeto do painel com Vite, React, Tailwind e proxy para o backend"
```

---

## Subtarefa 5A.2 — Cliente HTTP (R2)

**Files:**
- Create: `frontend/src/api/client.test.js`, `frontend/src/api/client.js`

- [ ] **Passo 1: escrever os testes que falham** — `frontend/src/api/client.test.js`

```js
/** Testes do cliente HTTP do painel (spec R2). O fetch é sempre falso: nada vai à rede. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, errorFromResponse, request } from './client.js';

function respostaJson(status, corpo) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('errorFromResponse', () => {
  it('usa o detail em texto e o service do backend', () => {
    const erro = errorFromResponse(409, { detail: 'vinheria001 já cadastrada', service: 'registry' });
    expect(erro).toBeInstanceOf(ApiError);
    expect(erro.status).toBe(409);
    expect(erro.message).toBe('vinheria001 já cadastrada');
    expect(erro.service).toBe('registry');
  });

  it('junta os erros de validação 422 com o nome do campo', () => {
    const erro = errorFromResponse(422, {
      detail: [
        { loc: ['body', 'device_id'], msg: 'String should match pattern' },
        { loc: ['body', 'city'], msg: 'Field required' },
      ],
    });
    expect(erro.message).toBe('device_id: String should match pattern; city: Field required');
  });

  it('sem corpo JSON e status 4xx, devolve mensagem genérica', () => {
    expect(errorFromResponse(404, null).message).toBe('Erro HTTP 404');
  });

  it('sem corpo JSON e status 5xx, avisa que o backend não respondeu', () => {
    expect(errorFromResponse(500, null).message).toMatch(/Backend sem resposta/);
  });
});

describe('request', () => {
  it('GET devolve o JSON da resposta', async () => {
    const fetchFalso = vi.fn(async () => respostaJson(200, { ec2_ip: '1.2.3.4' }));
    vi.stubGlobal('fetch', fetchFalso);
    await expect(request('/api/config')).resolves.toEqual({ ec2_ip: '1.2.3.4' });
    expect(fetchFalso).toHaveBeenCalledWith('/api/config', expect.objectContaining({ method: 'GET' }));
  });

  it('POST envia o corpo em JSON com o cabeçalho certo', async () => {
    const fetchFalso = vi.fn(async () => respostaJson(201, { device_id: 'vinheria003' }));
    vi.stubGlobal('fetch', fetchFalso);
    await api.createDevice({ device_id: 'vinheria003', name: 'A', city: 'B' });
    const [url, opcoes] = fetchFalso.mock.calls[0];
    expect(url).toBe('/api/devices');
    expect(opcoes.method).toBe('POST');
    expect(opcoes.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(JSON.parse(opcoes.body)).toEqual({ device_id: 'vinheria003', name: 'A', city: 'B' });
  });

  it('204 devolve null', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })));
    await expect(api.deleteDevice('vinheria003')).resolves.toBeNull();
  });

  it('status de erro vira ApiError com o detail', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respostaJson(409, { detail: 'Vinheria offline', service: 'registry' })));
    await expect(request('/api/x')).rejects.toMatchObject({ name: 'ApiError', status: 409, message: 'Vinheria offline' });
  });

  it('falha de rede vira ApiError com status 0', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('fetch failed'); }));
    await expect(request('/api/config')).rejects.toMatchObject({ name: 'ApiError', status: 0 });
  });
});
```

- [ ] **Passo 2: rodar e ver falhar**

```bash
npm test
```
Esperado: falha por `client.js` não existir.

- [ ] **Passo 3: implementar `frontend/src/api/client.js`**

```js
/**
 * Cliente HTTP do painel: a única porta de entrada para o backend FastAPI.
 *
 * Componentes e contexts nunca chamam fetch; usam as funções de `api`. Os
 * caminhos são relativos (/api/...) porque o Vite encaminha para o backend
 * (proxy em vite.config.js). Toda falha vira ApiError com uma mensagem em
 * português pronta para mostrar na tela.
 */

/** Erro de uma chamada ao backend. status 0 = nem chegou ao servidor. */
export class ApiError extends Error {
  constructor(status, message, service = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.service = service;
  }
}

/**
 * Monta o ApiError a partir da resposta de erro do backend.
 *
 * O backend responde { detail: "texto", service } nos erros de negócio e do
 * FIWARE, e { detail: [{ loc, msg }] } na validação do Pydantic (422). Sem
 * corpo JSON e com status 5xx, o caso típico é o proxy do Vite sem backend.
 */
export function errorFromResponse(status, body) {
  const detail = body?.detail;
  if (typeof detail === 'string') {
    return new ApiError(status, detail, body.service ?? null);
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const partes = detail.map((item) => {
      const campo = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
      return campo ? `${campo}: ${item.msg}` : item.msg;
    });
    return new ApiError(status, partes.join('; '));
  }
  if (status >= 500) {
    return new ApiError(status, `Backend sem resposta (HTTP ${status}). Confira se o uvicorn está rodando.`);
  }
  return new ApiError(status, `Erro HTTP ${status}`);
}

/** Faz uma chamada ao backend e devolve o JSON (ou null em 204). */
export async function request(path, { method = 'GET', body } = {}) {
  const comCorpo = body !== undefined;
  let resposta;
  try {
    resposta = await fetch(path, {
      method,
      headers: comCorpo ? { 'Content-Type': 'application/json' } : undefined,
      body: comCorpo ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Backend indisponível. Confira se o uvicorn está rodando.');
  }
  if (resposta.status === 204) {
    return null;
  }
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    throw errorFromResponse(resposta.status, dados);
  }
  return dados;
}

/** Endpoints usados pelo painel (contratos em PLANO-CP5-VINHERIA.md). */
export const api = {
  getConfig: () => request('/api/config'),
  saveConfig: (changes) => request('/api/config', { method: 'PUT', body: changes }),
  getHealth: () => request('/api/config/health'),
  getFleet: () => request('/api/fleet'),
  listDevices: () => request('/api/devices'),
  createDevice: (device) => request('/api/devices', { method: 'POST', body: device }),
  deleteDevice: (deviceId) =>
    request(`/api/devices/${encodeURIComponent(deviceId)}`, { method: 'DELETE' }),
};
```

- [ ] **Passo 4: rodar e ver passar**

```bash
npm test
```
Esperado: **9 passed**.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/api/client.js frontend/src/api/client.test.js
git commit -m "feat: adiciona o cliente HTTP do painel com erros traduzidos"
```

---

## Subtarefa 5A.3 — Validação do cadastro (R6.1)

**Files:**
- Create: `frontend/src/lib/validation.test.js`, `frontend/src/lib/validation.js`

- [ ] **Passo 1: escrever os testes que falham** — `frontend/src/lib/validation.test.js`

```js
/** Testes da validação do cadastro de vinheria no navegador (spec R6.1). */
import { describe, expect, it } from 'vitest';
import { validarCadastro } from './validation.js';

describe('validarCadastro', () => {
  it('aceita, limpa espaços e passa o id para minúsculas', () => {
    expect(validarCadastro({ device_id: ' Vinheria003 ', name: ' Vinheria Recife ', city: 'Recife ' }))
      .toEqual({ dados: { device_id: 'vinheria003', name: 'Vinheria Recife', city: 'Recife' }, erro: null });
  });

  it('recusa id fora do formato', () => {
    expect(validarCadastro({ device_id: 'vinheria3', name: 'A', city: 'B' }).erro).toMatch(/vinheria00N/);
  });

  it('recusa nome ou cidade vazios', () => {
    expect(validarCadastro({ device_id: 'vinheria003', name: '  ', city: 'B' }).erro).toMatch(/nome e cidade/);
  });

  it('recusa nome com mais de 60 caracteres', () => {
    expect(validarCadastro({ device_id: 'vinheria003', name: 'x'.repeat(61), city: 'B' }).erro).toMatch(/60/);
  });
});
```

- [ ] **Passo 2: rodar e ver falhar** — `npm test` → falha por `validation.js` não existir.

- [ ] **Passo 3: implementar `frontend/src/lib/validation.js`**

```js
/**
 * Validação do cadastro de vinheria feita no navegador, antes de chamar o
 * backend. Repete as regras do DeviceCreate (backend/app/models/schemas.py)
 * para o usuário ver o erro na hora; o backend continua validando.
 */

const ID_VALIDO = /^vinheria\d{3}$/;
const LIMITE_TEXTO = 60;

/**
 * Limpa e confere os campos do formulário.
 * Devolve { dados, erro: null } quando está tudo certo, ou { dados: null, erro }.
 */
export function validarCadastro(campos) {
  const dados = {
    device_id: campos.device_id.trim().toLowerCase(),
    name: campos.name.trim(),
    city: campos.city.trim(),
  };
  if (!ID_VALIDO.test(dados.device_id)) {
    return { dados: null, erro: 'O id deve seguir o formato vinheria00N (ex.: vinheria003).' };
  }
  if (!dados.name || !dados.city) {
    return { dados: null, erro: 'Informe nome e cidade.' };
  }
  if (dados.name.length > LIMITE_TEXTO || dados.city.length > LIMITE_TEXTO) {
    return { dados: null, erro: `Nome e cidade têm no máximo ${LIMITE_TEXTO} caracteres.` };
  }
  return { dados, erro: null };
}
```

- [ ] **Passo 4: rodar e ver passar** — `npm test` → **13 passed**.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/lib/validation.js frontend/src/lib/validation.test.js
git commit -m "feat: valida o cadastro de vinheria no navegador"
```

---

## Subtarefa 5A.4 — Eventos da frota (R4)

**Files:**
- Create: `frontend/src/constants.js`, `frontend/src/lib/fleetEvents.test.js`, `frontend/src/lib/fleetEvents.js`

- [ ] **Passo 1: criar `frontend/src/constants.js`**

```js
/**
 * Constantes do painel: intervalos de atualização, limite de toasts e os
 * rótulos em português de cada status de vinheria.
 */

// Polling da frota (RF14) e da saúde do FIWARE
export const FLEET_POLL_MS = 5000;
export const HEALTH_POLL_MS = 30000;

// Quantos avisos (toasts) ficam empilhados na tela ao mesmo tempo
export const LIMITE_TOASTS = 5;

// "aguardando" = cadastrada, mas o poller ainda não a incluiu na frota
export const STATUS_ROTULO = {
  ok: 'OK',
  alerta: 'Em alerta',
  offline: 'Offline',
  configurando: 'Configurando',
  aguardando: 'Aguardando 1º ciclo',
};
```

- [ ] **Passo 2: escrever os testes que falham** — `frontend/src/lib/fleetEvents.test.js`

```js
/** Testes dos eventos da frota que alimentam a faixa e os toasts (spec R4). */
import { describe, expect, it } from 'vitest';
import { bannerSummary, diffFleet, empilharToasts, textoDoEvento } from './fleetEvents.js';

function vinheria(deviceId, status, extra = {}) {
  return {
    device_id: deviceId,
    name: `Vinheria ${deviceId.slice(-3)}`,
    city: 'Cidade',
    status,
    offline_reason: null,
    current: {},
    active_alerts: [],
    ...extra,
  };
}

function frota(vinherias, extra = {}) {
  return {
    fiware_online: true,
    fiware_offline_since: null,
    updated_at: '2026-10-20T14:00:00+00:00',
    vinherias,
    ...extra,
  };
}

const offlineSemLeitura = { offline_reason: 'sem_leitura' };
const offlineFiware = { offline_reason: 'fiware' };

describe('diffFleet', () => {
  it('primeira leitura não gera eventos', () => {
    expect(diffFleet(null, frota([vinheria('vinheria001', 'alerta')]))).toEqual([]);
  });

  it('ok para alerta gera evento alerta', () => {
    const eventos = diffFleet(frota([vinheria('vinheria001', 'ok')]), frota([vinheria('vinheria001', 'alerta')]));
    expect(eventos).toHaveLength(1);
    expect(eventos[0]).toMatchObject({ tipo: 'alerta', device_id: 'vinheria001', name: 'Vinheria 001', city: 'Cidade' });
  });

  it('status igual não gera evento', () => {
    expect(diffFleet(frota([vinheria('vinheria001', 'alerta')]), frota([vinheria('vinheria001', 'alerta')]))).toEqual([]);
  });

  it('ok para offline sem leitura gera evento offline', () => {
    const eventos = diffFleet(
      frota([vinheria('vinheria001', 'ok')]),
      frota([vinheria('vinheria001', 'offline', offlineSemLeitura)]),
    );
    expect(eventos.map((e) => e.tipo)).toEqual(['offline']);
  });

  it('offline sem leitura para ok ou configurando gera evento normal', () => {
    const antes = frota([vinheria('vinheria001', 'offline', offlineSemLeitura)]);
    expect(diffFleet(antes, frota([vinheria('vinheria001', 'ok')])).map((e) => e.tipo)).toEqual(['normal']);
    expect(diffFleet(antes, frota([vinheria('vinheria001', 'configurando')])).map((e) => e.tipo)).toEqual(['normal']);
  });

  it('alerta para ok gera evento normal', () => {
    const eventos = diffFleet(frota([vinheria('vinheria001', 'alerta')]), frota([vinheria('vinheria001', 'ok')]));
    expect(eventos.map((e) => e.tipo)).toEqual(['normal']);
  });

  it('configurando para ok não gera evento', () => {
    expect(diffFleet(frota([vinheria('vinheria001', 'configurando')]), frota([vinheria('vinheria001', 'ok')]))).toEqual([]);
  });

  it('EC2 cai: um único evento, sem eventos por vinheria', () => {
    const antes = frota([vinheria('vinheria001', 'ok'), vinheria('vinheria002', 'alerta')]);
    const depois = frota(
      [vinheria('vinheria001', 'offline', offlineFiware), vinheria('vinheria002', 'offline', offlineFiware)],
      { fiware_online: false, fiware_offline_since: '2026-10-20T14:00:00+00:00' },
    );
    const eventos = diffFleet(antes, depois);
    expect(eventos).toHaveLength(1);
    expect(eventos[0]).toMatchObject({ tipo: 'fiware_offline', device_id: null });
  });

  it('EC2 volta: um único evento, sem normal por vinheria', () => {
    const antes = frota(
      [vinheria('vinheria001', 'offline', offlineFiware), vinheria('vinheria002', 'offline', offlineFiware)],
      { fiware_online: false },
    );
    const depois = frota([vinheria('vinheria001', 'ok'), vinheria('vinheria002', 'configurando')]);
    expect(diffFleet(antes, depois).map((e) => e.tipo)).toEqual(['fiware_online']);
  });

  it('vinheria nova ou removida não gera evento', () => {
    const antes = frota([vinheria('vinheria001', 'ok')]);
    const depois = frota([vinheria('vinheria002', 'offline', offlineSemLeitura)]);
    expect(diffFleet(antes, depois)).toEqual([]);
  });

  it('só a vinheria que mudou gera evento', () => {
    const antes = frota([vinheria('vinheria001', 'ok'), vinheria('vinheria002', 'ok')]);
    const depois = frota([vinheria('vinheria001', 'alerta'), vinheria('vinheria002', 'ok')]);
    expect(diffFleet(antes, depois).map((e) => e.device_id)).toEqual(['vinheria001']);
  });

  it('id junta tipo, vinheria e o horário do retrato', () => {
    const depois = frota([vinheria('vinheria001', 'alerta')], { updated_at: '2026-10-20T14:00:05+00:00' });
    const [evento] = diffFleet(frota([vinheria('vinheria001', 'ok')]), depois);
    expect(evento.id).toBe('alerta:vinheria001:2026-10-20T14:00:05+00:00');
    expect(evento.at).toBe('2026-10-20T14:00:05+00:00');
  });
});

describe('textoDoEvento', () => {
  it('gera a frase de cada tipo', () => {
    const base = { device_id: 'vinheria001', name: 'Vinheria Paulista', city: 'São Paulo' };
    expect(textoDoEvento({ ...base, tipo: 'alerta' })).toBe('Vinheria Paulista (São Paulo) entrou em alerta');
    expect(textoDoEvento({ ...base, tipo: 'offline' })).toBe('Vinheria Paulista (São Paulo) ficou offline');
    expect(textoDoEvento({ ...base, tipo: 'normal' })).toBe('Vinheria Paulista (São Paulo) voltou ao normal');
    expect(textoDoEvento({ tipo: 'fiware_offline' })).toBe('EC2/FIWARE fora do ar: todas as vinherias offline');
    expect(textoDoEvento({ tipo: 'fiware_online' })).toBe('EC2/FIWARE de volta');
  });
});

describe('empilharToasts', () => {
  it('põe os novos primeiro, não repete id e respeita o limite', () => {
    expect(empilharToasts([{ id: 'a' }], [{ id: 'b' }, { id: 'c' }, { id: 'a' }]).map((t) => t.id))
      .toEqual(['c', 'b', 'a']);
    const atuais = [{ id: 'a1' }, { id: 'a2' }, { id: 'a3' }, { id: 'a4' }];
    expect(empilharToasts(atuais, [{ id: 'b' }, { id: 'c' }]).map((t) => t.id))
      .toEqual(['c', 'b', 'a1', 'a2', 'a3']);
  });
});

describe('bannerSummary', () => {
  it('sem frota devolve null', () => {
    expect(bannerSummary(null)).toBeNull();
  });

  it('separa alerta e offline e ignora offline causado pela EC2', () => {
    const resumo = bannerSummary(frota([
      vinheria('vinheria001', 'alerta'),
      vinheria('vinheria002', 'offline', offlineSemLeitura),
      vinheria('vinheria003', 'ok'),
    ]));
    expect(resumo.fiwareOffline).toBe(false);
    expect(resumo.emAlerta.map((v) => v.device_id)).toEqual(['vinheria001']);
    expect(resumo.offline.map((v) => v.device_id)).toEqual(['vinheria002']);
    expect(resumo.visivel).toBe(true);

    const ec2Fora = bannerSummary(frota([vinheria('vinheria001', 'offline', offlineFiware)], { fiware_online: false }));
    expect(ec2Fora.fiwareOffline).toBe(true);
    expect(ec2Fora.offline).toEqual([]);
    expect(ec2Fora.visivel).toBe(true);
  });

  it('frota toda ok não mostra a faixa', () => {
    expect(bannerSummary(frota([vinheria('vinheria001', 'ok'), vinheria('vinheria002', 'configurando')])).visivel).toBe(false);
  });
});
```

- [ ] **Passo 3: rodar e ver falhar** — `npm test` → falha por `fleetEvents.js` não existir.

- [ ] **Passo 4: implementar `frontend/src/lib/fleetEvents.js`**

```js
/**
 * Eventos da frota: compara dois retratos de GET /api/fleet e diz o que
 * mudou, para o painel avisar (RF14). Funções puras, sem React, testadas
 * em fleetEvents.test.js.
 *
 * Regras (spec R4): avisa quando uma vinheria entra em alerta, fica offline
 * ou volta ao normal. A queda da EC2 deixa todas offline de uma vez; nesse
 * caso sai um único aviso da EC2, não um por vinheria.
 */
import { LIMITE_TOASTS } from '../constants.js';

/** Lista os eventos entre o retrato anterior e o atual ([] na primeira leitura). */
export function diffFleet(anterior, atual) {
  if (!anterior || !atual) {
    return [];
  }
  const quando = atual.updated_at ?? new Date().toISOString();
  const eventos = [];
  if (anterior.fiware_online && !atual.fiware_online) {
    eventos.push(criarEvento('fiware_offline', null, quando));
  }
  if (!anterior.fiware_online && atual.fiware_online) {
    eventos.push(criarEvento('fiware_online', null, quando));
  }
  const antes = new Map(anterior.vinherias.map((v) => [v.device_id, v]));
  for (const depois of atual.vinherias) {
    const previa = antes.get(depois.device_id);
    // Vinheria nova (ou mesmo status) não gera aviso
    if (!previa || previa.status === depois.status) {
      continue;
    }
    const tipo = tipoDaTransicao(previa, depois);
    if (tipo) {
      eventos.push(criarEvento(tipo, depois, quando));
    }
  }
  return eventos;
}

/** Tipo do evento de uma vinheria que mudou de status, ou null se não avisa. */
function tipoDaTransicao(previa, depois) {
  if (depois.status === 'alerta') {
    return 'alerta';
  }
  if (depois.status === 'offline') {
    // Offline por causa da EC2 já é avisado pelo evento único fiware_offline
    return depois.offline_reason === 'fiware' ? null : 'offline';
  }
  if (previa.status === 'offline') {
    // Volta da EC2 já é avisada pelo evento único fiware_online
    return previa.offline_reason === 'fiware' ? null : 'normal';
  }
  if (previa.status === 'alerta' && depois.status === 'ok') {
    return 'normal';
  }
  return null;
}

/** Monta o evento; o id é único por tipo, vinheria e retrato (serve de key do toast). */
function criarEvento(tipo, vinheria, quando) {
  return {
    id: `${tipo}:${vinheria?.device_id ?? 'fiware'}:${quando}`,
    tipo,
    device_id: vinheria?.device_id ?? null,
    name: vinheria?.name ?? null,
    city: vinheria?.city ?? null,
    at: quando,
  };
}

/** Frase em português mostrada no toast. */
export function textoDoEvento(evento) {
  const quem = `${evento.name} (${evento.city})`;
  switch (evento.tipo) {
    case 'alerta':
      return `${quem} entrou em alerta`;
    case 'offline':
      return `${quem} ficou offline`;
    case 'normal':
      return `${quem} voltou ao normal`;
    case 'fiware_offline':
      return 'EC2/FIWARE fora do ar: todas as vinherias offline';
    case 'fiware_online':
      return 'EC2/FIWARE de volta';
    default:
      return quem;
  }
}

/** Empilha os eventos novos em cima dos toasts atuais, sem repetir id e até o limite. */
export function empilharToasts(atuais, novos, limite = LIMITE_TOASTS) {
  const existentes = new Set(atuais.map((toast) => toast.id));
  const ineditos = [...novos].reverse().filter((evento) => !existentes.has(evento.id));
  return [...ineditos, ...atuais].slice(0, limite);
}

/**
 * Resumo para a faixa fixa: EC2 fora, vinherias em alerta e offline (sem
 * contar as offline por causa da EC2). null enquanto não há retrato.
 */
export function bannerSummary(frota) {
  if (!frota) {
    return null;
  }
  const fiwareOffline = !frota.fiware_online;
  const emAlerta = frota.vinherias.filter((v) => v.status === 'alerta');
  const offline = frota.vinherias.filter((v) => v.status === 'offline' && v.offline_reason !== 'fiware');
  return {
    fiwareOffline,
    emAlerta,
    offline,
    visivel: fiwareOffline || emAlerta.length > 0 || offline.length > 0,
  };
}
```

- [ ] **Passo 5: rodar e ver passar** — `npm test` → **30 passed**.

- [ ] **Passo 6: commit**

```bash
git add frontend/src/constants.js frontend/src/lib/fleetEvents.js frontend/src/lib/fleetEvents.test.js
git commit -m "feat: calcula os eventos de alerta, offline e volta da frota"
```

---

## Subtarefa 5A.5 — Casca: rotas, navegação, polling e peças reutilizáveis (R7)

**Files:**
- Create: `frontend/src/estilo.js`, `frontend/src/components/ui.jsx`, `frontend/src/hooks/usePolling.js`, `frontend/src/hooks/useAcao.js`, `frontend/src/context/criarContexto.js`, `frontend/src/pages/Placeholder.jsx`, `frontend/src/App.jsx`
- Modify: `frontend/src/main.jsx`

> **Por que esta subtarefa cria peças antes das telas:** as telas das 5A.6 a 5A.8 repetiriam o mesmo `try/catch/finally` com "carregando" e "erro" (4 vezes), o mesmo boilerplate de contexto (2 vezes) e os mesmos rótulo+campo, botão, mensagem de erro, título, texto secundário e link de vinheria. Tudo isso nasce aqui, uma vez, e as telas só usam. A Task 6 reaproveita as mesmas peças.

- [ ] **Passo 1: criar `frontend/src/estilo.js`** (provisório; não acrescente cores além destas)

```js
/**
 * Cores semânticas de cada status, como mapas de classes Tailwind.
 * Visual PROVISÓRIO da Task 5A: a Task 5B troca pelas cores do design
 * system. As classes ficam escritas por inteiro de propósito, para o
 * Tailwind encontrá-las ao gerar o CSS. As classes de título, campo,
 * botão etc. não ficam aqui: moram nos componentes de components/ui.jsx.
 */

// Cor do texto do status de uma vinheria (tabela de dispositivos)
export const COR_STATUS = {
  ok: 'text-green-700',
  alerta: 'text-red-700',
  configurando: 'text-amber-700',
  offline: 'text-gray-500',
  aguardando: 'text-gray-500',
};

// Cor da bolinha do indicador de saúde do FIWARE
export const COR_SAUDE = {
  verificando: 'bg-gray-400',
  online: 'bg-green-600',
  offline: 'bg-red-600',
  sem_backend: 'bg-red-600',
};

// Cor da borda esquerda de cada toast
export const BORDA_TOAST = {
  alerta: 'border-l-red-600',
  fiware_offline: 'border-l-red-600',
  offline: 'border-l-gray-500',
  normal: 'border-l-green-600',
  fiware_online: 'border-l-green-600',
};
```

- [ ] **Passo 2: criar `frontend/src/components/ui.jsx`**

```jsx
/**
 * Componentes básicos reaproveitados em todas as telas: título, campo com
 * rótulo, botão, mensagem de erro, texto secundário e link para o detalhe
 * de uma vinheria. Eles concentram as classes Tailwind repetidas, então a
 * Task 5B troca o visual aqui, num lugar só. Antes de escrever um destes
 * elementos à mão numa tela, use o daqui (ou acrescente uma variação aqui).
 */
import { Link } from 'react-router-dom';

/** Título de página. */
export function Titulo({ children }) {
  return <h1 className="mb-4 text-xl font-semibold">{children}</h1>;
}

/** Campo de texto com o rótulo em cima; as demais props vão para o <input>. */
export function Campo({ rotulo, ...props }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {rotulo}
      <input className="rounded border border-gray-300 px-2 py-1" {...props} />
    </label>
  );
}

/** Botão padrão. Com `carregando`, fica desabilitado e mostra `textoCarregando`. */
export function Botao({ carregando = false, textoCarregando, disabled, type = 'button', children, ...props }) {
  return (
    <button
      type={type}
      disabled={disabled || carregando}
      className="rounded border border-gray-400 px-3 py-1 text-sm hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
      {...props}
    >
      {carregando && textoCarregando ? textoCarregando : children}
    </button>
  );
}

/** Mensagem de erro; não desenha nada quando `erro` está vazio. */
export function MensagemErro({ erro }) {
  if (!erro) {
    return null;
  }
  return (
    <p className="mb-2 basis-full text-sm text-red-700" role="alert">
      {erro}
    </p>
  );
}

/** Texto secundário: avisos, "Carregando…", lista vazia. */
export function Nota({ children }) {
  return <p className="text-gray-600">{children}</p>;
}

/** Link (React Router, sem recarregar) para o detalhe de uma vinheria. */
export function LinkVinheria({ deviceId, children }) {
  return (
    <Link to={`/vinherias/${deviceId}`} className="underline hover:text-gray-600">
      {children}
    </Link>
  );
}
```

- [ ] **Passo 3: criar `frontend/src/hooks/useAcao.js`**

```js
/**
 * Hook para ações assíncronas disparadas pelo usuário (salvar, cadastrar,
 * remover, carregar). Controla o "executando" e guarda a mensagem do
 * ApiError, para nenhuma tela repetir o mesmo try/catch/finally.
 *
 * executar(...args) nunca lança: devolve { ok: true, valor } ou { ok: false }.
 * setErro permite mostrar um erro de validação feito antes da chamada.
 */
import { useCallback, useState } from 'react';

export function useAcao(acao) {
  const [executando, setExecutando] = useState(false);
  const [erro, setErro] = useState(null);

  const executar = useCallback(async (...args) => {
    setExecutando(true);
    setErro(null);
    try {
      return { ok: true, valor: await acao(...args) };
    } catch (falha) {
      setErro(falha.message);
      return { ok: false };
    } finally {
      setExecutando(false);
    }
  }, [acao]);

  return { executar, executando, erro, setErro };
}
```

> `acao` deve ser estável entre renderizações (função de `api.*` ou criada com `useCallback`); senão `executar` muda a cada render.

- [ ] **Passo 4: criar `frontend/src/context/criarContexto.js`**

```js
/**
 * Fábrica de contexto React: devolve o Provider e um hook de acesso que
 * falha cedo quando usado fora dele. Evita repetir createContext +
 * useContext + checagem em cada contexto do painel (Config, Fleet e os das
 * próximas tasks).
 */
import { createContext, useContext } from 'react';

export function criarContexto(nome) {
  const Contexto = createContext(null);
  function useContexto() {
    const valor = useContext(Contexto);
    if (!valor) {
      throw new Error(`use${nome} precisa estar dentro de <${nome}Provider>`);
    }
    return valor;
  }
  return [Contexto.Provider, useContexto];
}
```

- [ ] **Passo 5: criar `frontend/src/hooks/usePolling.js`**

```js
/**
 * Hook de polling: roda uma tarefa assíncrona agora e de novo `intervaloMs`
 * depois que ela TERMINA (cadeia de setTimeout). Assim as requisições nunca
 * se acumulam, mesmo quando o FIWARE demora até o timeout para responder.
 */
import { useEffect, useRef } from 'react';

export function usePolling(tarefa, intervaloMs) {
  // Guarda a versão mais recente da tarefa sem reiniciar o ciclo
  const tarefaAtual = useRef(tarefa);
  useEffect(() => {
    tarefaAtual.current = tarefa;
  }, [tarefa]);

  useEffect(() => {
    let ativo = true;
    let timer = null;
    async function ciclo() {
      try {
        await tarefaAtual.current();
      } catch (erro) {
        // A tarefa deveria tratar os próprios erros; isto só evita parar o ciclo
        console.error('usePolling: tarefa falhou', erro);
      } finally {
        if (ativo) {
          timer = setTimeout(ciclo, intervaloMs);
        }
      }
    }
    ciclo();
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [intervaloMs]);
}
```

- [ ] **Passo 6: criar `frontend/src/pages/Placeholder.jsx`**

```jsx
/**
 * Tela provisória das rotas que outras tasks ainda vão preencher
 * (Visão geral, Detalhe e Alertas na Task 6; Chat na Task 7A).
 * Sem `task`, serve de página "não encontrada".
 */
import { Nota, Titulo } from '../components/ui.jsx';

export default function Placeholder({ titulo, task }) {
  return (
    <section>
      <Titulo>{titulo}</Titulo>
      <Nota>{task ? `Esta tela chega na ${task}.` : 'Confira o endereço ou use o menu acima.'}</Nota>
    </section>
  );
}
```

- [ ] **Passo 7: criar `frontend/src/App.jsx`**

```jsx
/**
 * Layout e rotas do painel Smart Solutions.
 *
 * Rotas: / Visão geral · /vinherias/:id Detalhe · /alertas · /dispositivos
 * · /chat. As telas das Tasks 6 e 7A ainda são Placeholder.
 * A troca de página é sempre pelo react-router-dom (NavLink/Link/useNavigate),
 * sem recarregar: os toasts e o polling da frota continuam vivos.
 */
import { NavLink, Route, Routes } from 'react-router-dom';
import Placeholder from './pages/Placeholder.jsx';

const MENU = [
  { to: '/', rotulo: 'Visão geral' },
  { to: '/dispositivos', rotulo: 'Dispositivos' },
  { to: '/alertas', rotulo: 'Alertas' },
  { to: '/chat', rotulo: 'Chat' },
];

/** Classes do item do menu; o NavLink informa se a rota está ativa. */
function classeDoMenu({ isActive }) {
  return isActive ? 'font-semibold underline' : 'text-gray-700 hover:underline';
}

export default function App() {
  return (
    <>
      <nav className="flex gap-4 border-b border-gray-200 px-4 py-2 text-sm">
        {MENU.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'} className={classeDoMenu}>
            {item.rotulo}
          </NavLink>
        ))}
      </nav>
      <main className="p-4">
        <Routes>
          <Route path="/" element={<Placeholder titulo="Visão geral" task="Task 6" />} />
          <Route path="/vinherias/:id" element={<Placeholder titulo="Detalhe da vinheria" task="Task 6" />} />
          <Route path="/alertas" element={<Placeholder titulo="Alertas" task="Task 6" />} />
          <Route path="/dispositivos" element={<Placeholder titulo="Dispositivos" task="subtarefa 5A.8" />} />
          <Route path="/chat" element={<Placeholder titulo="Chat" task="Task 7A" />} />
          <Route path="*" element={<Placeholder titulo="Página não encontrada" />} />
        </Routes>
      </main>
    </>
  );
}
```

- [ ] **Passo 8: substituir `frontend/src/main.jsx`**

```jsx
/** Ponto de entrada do painel: liga o roteador (BrowserRouter) e o Tailwind e monta o App. */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
```

- [ ] **Passo 9: verificar** — `npm test` → **30 passed**; `npm run build` sem erro (ui.jsx, useAcao e criarContexto ainda sem uso nas telas além do Placeholder; tudo bem); `npm run dev`: os 4 links trocam de página **sem recarregar** (na aba Network, nenhuma requisição de documento `localhost:5173/...` ao clicar; só navegação do React Router), o ativo fica em negrito e sublinhado, `/vinherias/vinheria001` mostra "Detalhe da vinheria", `/xyz` mostra "Página não encontrada", recarregar a página em `/alertas` não dá 404, e os botões Voltar/Avançar do navegador funcionam. Console do navegador sem erros.

- [ ] **Passo 10: commit**

```bash
git add frontend/src/estilo.js frontend/src/components/ui.jsx frontend/src/hooks/usePolling.js frontend/src/hooks/useAcao.js frontend/src/context/criarContexto.js frontend/src/pages/Placeholder.jsx frontend/src/App.jsx frontend/src/main.jsx
git commit -m "feat: adiciona as rotas do painel com react-router e as pecas reutilizaveis de tela, contexto e acao"
```

---

## Subtarefa 5A.6 — Configuração e saúde do FIWARE (R3)

**Files:**
- Create: `frontend/src/context/ConfigContext.jsx`, `frontend/src/components/FiwareBar.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Passo 1: criar `frontend/src/context/ConfigContext.jsx`**

```jsx
/**
 * Contexto da configuração do backend e da saúde do FIWARE.
 *
 * A cada 30 s lê GET /api/config e GET /api/config/health. Expõe o IP em
 * uso, o resultado do health e salvarIp(), que troca o IP do FIWARE em
 * runtime (PUT /api/config) e revalida a saúde na hora.
 */
import { useCallback, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { HEALTH_POLL_MS } from '../constants.js';
import { usePolling } from '../hooks/usePolling.js';
import { criarContexto } from './criarContexto.js';

const [Provedor, useConfig] = criarContexto('Config');
export { useConfig };

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [health, setHealth] = useState(null);
  // verificando | online | offline | sem_backend
  const [healthState, setHealthState] = useState('verificando');

  /** Recarrega config e saúde; o config também, para aparecer se o backend voltou. */
  const verificarSaude = useCallback(async () => {
    try {
      const [novoConfig, novoHealth] = await Promise.all([api.getConfig(), api.getHealth()]);
      setConfig(novoConfig);
      setHealth(novoHealth);
      setHealthState(novoHealth.ok ? 'online' : 'offline');
    } catch {
      setHealth(null);
      setHealthState('sem_backend');
    }
  }, []);

  usePolling(verificarSaude, HEALTH_POLL_MS);

  /** Grava o novo IP do FIWARE; erros sobem para o formulário mostrar. */
  const salvarIp = useCallback(async (ip) => {
    const novo = await api.saveConfig({ ec2_ip: ip });
    setConfig(novo);
    setHealthState('verificando');
    await verificarSaude();
    return novo;
  }, [verificarSaude]);

  const valor = useMemo(
    () => ({ config, health, healthState, salvarIp, verificarSaude }),
    [config, health, healthState, salvarIp, verificarSaude],
  );
  return <Provedor value={valor}>{children}</Provedor>;
}
```

- [ ] **Passo 2: criar `frontend/src/components/FiwareBar.jsx`**

```jsx
/**
 * Barra fixa do topo: marca Smart Solutions, indicador de saúde do FIWARE
 * com o IP em uso e o painel "Avançado" (recolhido) para trocar o IP da EC2
 * em runtime. O IP padrão vem do .env do backend (IP elástico).
 */
import { useState } from 'react';
import { useConfig } from '../context/ConfigContext.jsx';
import { COR_SAUDE } from '../estilo.js';
import { useAcao } from '../hooks/useAcao.js';
import { Botao, Campo, MensagemErro } from './ui.jsx';

const ROTULO = {
  verificando: 'Verificando FIWARE…',
  online: 'FIWARE online',
  offline: 'FIWARE fora do ar',
  sem_backend: 'Backend indisponível',
};

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

export default function FiwareBar() {
  const { config, health, healthState, salvarIp } = useConfig();
  const [ip, setIp] = useState('');
  const [salvo, setSalvo] = useState(null);
  const salvar = useAcao(salvarIp);

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
    <header className="sticky top-0 z-10 flex flex-wrap items-center gap-4 border-b border-gray-300 bg-white px-4 py-2">
      <strong className="text-lg font-semibold">Smart Solutions</strong>
      <span className="flex items-center gap-2 text-sm">
        <span className={`h-2.5 w-2.5 rounded-full ${COR_SAUDE[healthState]}`} aria-hidden="true" />
        {ROTULO[healthState]}
        {config ? ` · ${config.ec2_ip}` : ''}
      </span>
      <details className="ml-auto text-sm">
        <summary className="cursor-pointer select-none">Avançado</summary>
        <form onSubmit={aoSalvar} className="mt-2 flex items-end gap-2">
          <Campo
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
        <MensagemErro erro={salvar.erro} />
        {salvo && <p role="status" className="mt-1">{salvo}</p>}
        {health && (
          <ul className="mt-2 space-y-0.5 text-gray-700">
            {SERVICOS.map(([chave, nome]) => (
              <li key={chave}>
                {nome}: {descreverServico(health[chave])}
              </li>
            ))}
          </ul>
        )}
      </details>
    </header>
  );
}
```

- [ ] **Passo 3: ligar no `App.jsx`** — acrescentar os imports e envolver o layout:

```jsx
import FiwareBar from './components/FiwareBar.jsx';
import { ConfigProvider } from './context/ConfigContext.jsx';
```

e trocar o `return` por:

```jsx
  return (
    <ConfigProvider>
      <FiwareBar />
      <nav className="flex gap-4 border-b border-gray-200 px-4 py-2 text-sm">
        {/* ...menu igual ao da 5A.5... */}
      </nav>
      <main className="p-4">
        {/* ...Routes iguais às da 5A.5... */}
      </main>
    </ConfigProvider>
  );
```

(o conteúdo de `nav` e `main` não muda; o comentário acima só indica onde fica.)

- [ ] **Passo 4: verificar no navegador** (backend rodando em `backend/` com `uvicorn app.main:app --reload`, EC2 ligada). **Anote o IP em uso antes de mexer.**
  1. A barra mostra "Smart Solutions", "FIWARE online · <IP>". Abrir "Avançado": Orion, IoT Agent e STH-Comet "ok (N ms)".
  2. Salvar `10.255.255.1` → "IP salvo: 10.255.255.1" e, em até ~10 s, "FIWARE fora do ar", com os três serviços "falhou".
  3. Salvar `http://<IP anotado>:1026/` → o backend normaliza para o IP; indicador volta a "FIWARE online".
  4. Parar o uvicorn → em até 30 s "Backend indisponível". Subir de novo → volta sozinho, sem recarregar.
  5. `npm test` → **30 passed**. Console sem erros (o 500 do proxy enquanto o backend está parado é esperado no terminal do Vite).

- [ ] **Passo 5: commit**

```bash
git add frontend/src/context/ConfigContext.jsx frontend/src/components/FiwareBar.jsx frontend/src/App.jsx
git commit -m "feat: mostra a saude do FIWARE e permite trocar o IP no painel avancado"
```

---

## Subtarefa 5A.7 — Polling da frota e aviso global (R5)

**Files:**
- Create: `frontend/src/context/FleetContext.jsx`, `frontend/src/components/AlertBanner.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Passo 1: criar `frontend/src/context/FleetContext.jsx`**

```jsx
/**
 * Contexto da frota: lê GET /api/fleet a cada 5 s, guarda o retrato
 * anterior e transforma as mudanças de status em toasts (RF14).
 *
 * Expõe o retrato atual (`fleet`), o erro da última leitura, a pilha de
 * toasts, fecharToast(id) e atualizar() para pedir uma leitura na hora.
 */
import { useCallback, useMemo, useRef, useState } from 'react';
import { api } from '../api/client.js';
import { FLEET_POLL_MS } from '../constants.js';
import { usePolling } from '../hooks/usePolling.js';
import { diffFleet, empilharToasts } from '../lib/fleetEvents.js';
import { criarContexto } from './criarContexto.js';

const [Provedor, useFleet] = criarContexto('Fleet');
export { useFleet };

export function FleetProvider({ children }) {
  const [fleet, setFleet] = useState(null);
  const [error, setError] = useState(null);
  const [toasts, setToasts] = useState([]);
  // Retrato anterior para comparar; ref porque não precisa redesenhar a tela
  const anterior = useRef(null);

  /** Uma leitura da frota: atualiza o retrato e empilha os eventos novos. */
  const atualizar = useCallback(async () => {
    try {
      const atual = await api.getFleet();
      const eventos = diffFleet(anterior.current, atual);
      anterior.current = atual;
      setFleet(atual);
      setError(null);
      if (eventos.length > 0) {
        setToasts((atuais) => empilharToasts(atuais, eventos));
      }
    } catch (erro) {
      setError(erro.message);
    }
  }, []);

  usePolling(atualizar, FLEET_POLL_MS);

  const fecharToast = useCallback((id) => {
    setToasts((atuais) => atuais.filter((toast) => toast.id !== id));
  }, []);

  const valor = useMemo(
    () => ({ fleet, error, toasts, fecharToast, atualizar }),
    [fleet, error, toasts, fecharToast, atualizar],
  );
  return <Provedor value={valor}>{children}</Provedor>;
}
```

- [ ] **Passo 2: criar `frontend/src/components/AlertBanner.jsx`**

```jsx
/**
 * Aviso global (RF14): faixa fixa enquanto houver vinheria em alerta ou
 * offline (ou a EC2 fora do ar) e toasts empilhados, um por evento, com
 * link para o detalhe da vinheria. Os toasts só somem quando fechados.
 */
import { Fragment } from 'react';
import { useFleet } from '../context/FleetContext.jsx';
import { BORDA_TOAST } from '../estilo.js';
import { bannerSummary, textoDoEvento } from '../lib/fleetEvents.js';
import { LinkVinheria } from './ui.jsx';

/** Nomes das vinherias separados por vírgula, cada um com link para o detalhe. */
function listaDeLinks(vinherias) {
  return vinherias.map((v, indice) => (
    <Fragment key={v.device_id}>
      {indice > 0 && ', '}
      <LinkVinheria deviceId={v.device_id}>{v.name}</LinkVinheria>
    </Fragment>
  ));
}

export default function AlertBanner() {
  const { fleet, toasts, fecharToast } = useFleet();
  const resumo = bannerSummary(fleet);

  return (
    <>
      {resumo?.visivel && (
        <div className="flex flex-wrap gap-4 border-b border-red-600 bg-red-50 px-4 py-2 text-sm" role="alert">
          {resumo.fiwareOffline && <span>EC2/FIWARE fora do ar: todas as vinherias offline.</span>}
          {resumo.emAlerta.length > 0 && <span>Em alerta: {listaDeLinks(resumo.emAlerta)}</span>}
          {resumo.offline.length > 0 && <span>Offline: {listaDeLinks(resumo.offline)}</span>}
        </div>
      )}
      <div className="fixed bottom-4 right-4 z-20 flex max-w-sm flex-col gap-2" aria-live="polite">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center gap-2 border border-l-4 border-gray-300 bg-white px-3 py-2 text-sm shadow ${BORDA_TOAST[toast.tipo]}`}
          >
            <span>{textoDoEvento(toast)}</span>
            {toast.device_id && <LinkVinheria deviceId={toast.device_id}>Ver detalhe</LinkVinheria>}
            <button
              type="button"
              onClick={() => fecharToast(toast.id)}
              aria-label="Fechar aviso"
              className="ml-auto px-1 text-gray-500 hover:text-gray-900"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
```

- [ ] **Passo 3: ligar no `App.jsx`** — acrescentar os imports:

```jsx
import AlertBanner from './components/AlertBanner.jsx';
import { FleetProvider } from './context/FleetContext.jsx';
```

e envolver tudo dentro do `ConfigProvider` com o `FleetProvider`, com o `AlertBanner` logo abaixo da `FiwareBar`:

```jsx
    <ConfigProvider>
      <FleetProvider>
        <FiwareBar />
        <AlertBanner />
        {/* nav e main iguais */}
      </FleetProvider>
    </ConfigProvider>
```

- [ ] **Passo 4: verificar no navegador** (backend + EC2 ligados, Wokwi da `vinheria001` rodando; a `vinheria002` sem Wokwi aparece offline).
  1. Ao abrir: faixa fixa "Offline: Vinheria Mineira" (002) e **nenhum toast** (primeira leitura).
  2. Na aba Network, `/api/fleet` a cada ~5 s, nunca duas ao mesmo tempo.
  3. Parar o Wokwi da 001 → em até ~40 s toast "Vinheria Paulista (São Paulo) ficou offline" com "Ver detalhe" (abre `/vinherias/vinheria001`) e a 001 na faixa. Fechar o toast no ×.
  4. Religar o Wokwi → toast "… voltou ao normal" e a 001 sai da faixa.
  5. EC2: no Avançado, salvar `10.255.255.1` → em até ~40 s **um único** toast "EC2/FIWARE fora do ar…" e a faixa com a mensagem da EC2. Voltar o IP real → **um único** "EC2/FIWARE de volta" (a volta pode levar ~1 min, achado da Task 4).
  6. `npm test` → **30 passed**. Console sem erros.

- [ ] **Passo 5: commit**

```bash
git add frontend/src/context/FleetContext.jsx frontend/src/components/AlertBanner.jsx frontend/src/App.jsx
git commit -m "feat: avisa no painel quando uma vinheria entra em alerta, fica offline ou volta"
```

---

## Subtarefa 5A.8 — Cadastro e remoção de vinherias (R6)

**Files:**
- Create: `frontend/src/components/DeviceForm.jsx`, `frontend/src/components/DeviceList.jsx`, `frontend/src/pages/Devices.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Passo 1: criar `frontend/src/components/DeviceForm.jsx`**

```jsx
/**
 * Formulário de cadastro de vinheria (RF01): device_id (vinheria00N, igual
 * ao ID_DEVICE do firmware), nome e cidade. Valida no navegador e chama
 * POST /api/devices, que provisiona no FIWARE e pode levar alguns segundos.
 */
import { useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { validarCadastro } from '../lib/validation.js';
import { Botao, Campo, MensagemErro } from './ui.jsx';

const VAZIO = { device_id: '', name: '', city: '' };

// Os três campos do cadastro: [name do input, rótulo, exemplo, tamanho máximo]
const CAMPOS = [
  ['device_id', 'Id do dispositivo', 'vinheria003', 11],
  ['name', 'Nome', 'Vinheria Recife', 60],
  ['city', 'Cidade', 'Recife', 60],
];

export default function DeviceForm({ onCreated }) {
  const [campos, setCampos] = useState(VAZIO);
  const cadastrar = useAcao(api.createDevice);

  function alterar(evento) {
    const { name, value } = evento.target;
    setCampos((atuais) => ({ ...atuais, [name]: value }));
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    const { dados, erro: invalido } = validarCadastro(campos);
    if (invalido) {
      cadastrar.setErro(invalido);
      return;
    }
    const resultado = await cadastrar.executar(dados);
    if (resultado.ok) {
      setCampos(VAZIO);
      await onCreated(resultado.valor);
    }
  }

  return (
    <form className="mb-6 flex flex-wrap items-end gap-3" onSubmit={aoEnviar}>
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
      <Botao type="submit" carregando={cadastrar.executando} textoCarregando="Provisionando no FIWARE…">
        Cadastrar
      </Botao>
      <MensagemErro erro={cadastrar.erro} />
    </form>
  );
}
```

- [ ] **Passo 2: criar `frontend/src/components/DeviceList.jsx`**

```jsx
/**
 * Lista das vinherias cadastradas (RF02) com o status vindo da frota e o
 * botão de remover. A remoção apaga o cadastro local, o device no IoT Agent
 * e a entidade no Orion; o histórico do STH-Comet é mantido.
 */
import { useState } from 'react';
import { api } from '../api/client.js';
import { STATUS_ROTULO } from '../constants.js';
import { COR_STATUS } from '../estilo.js';
import { useAcao } from '../hooks/useAcao.js';
import { Botao, MensagemErro, Nota } from './ui.jsx';

// Classes das células da tabela (provisório 5A; vira componente de tabela
// em ui.jsx quando a Task 6 precisar de uma segunda tabela)
const CELULA = 'border-b border-gray-200 px-3 py-1.5 text-left';

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
    return <Nota>Nenhuma vinheria cadastrada.</Nota>;
  }

  return (
    <>
      <MensagemErro erro={excluir.erro} />
      <table className="border-collapse text-sm">
        <thead>
          <tr className="font-semibold">
            <th className={CELULA}>Id</th>
            <th className={CELULA}>Nome</th>
            <th className={CELULA}>Cidade</th>
            <th className={CELULA}>Status</th>
            <th className={CELULA} aria-label="Ações" />
          </tr>
        </thead>
        <tbody>
          {devices.map((device) => {
            // Recém-cadastrada só entra na frota no próximo ciclo do poller
            const status = statusPorId[device.device_id] ?? 'aguardando';
            return (
              <tr key={device.device_id}>
                <td className={CELULA}>{device.device_id}</td>
                <td className={CELULA}>{device.name}</td>
                <td className={CELULA}>{device.city}</td>
                <td className={`${CELULA} ${COR_STATUS[status]}`}>{STATUS_ROTULO[status]}</td>
                <td className={CELULA}>
                  <Botao
                    onClick={() => remover(device)}
                    disabled={removendo !== null}
                    carregando={removendo === device.device_id}
                    textoCarregando="Removendo…"
                  >
                    Excluir
                  </Botao>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
```

- [ ] **Passo 3: criar `frontend/src/pages/Devices.jsx`**

```jsx
/**
 * Página /dispositivos: cadastro e lista das vinherias. Depois de cadastrar
 * ou remover, recarrega a lista e pede uma leitura imediata da frota para
 * o status aparecer sem esperar o próximo ciclo do polling.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import DeviceForm from '../components/DeviceForm.jsx';
import DeviceList from '../components/DeviceList.jsx';
import { MensagemErro, Nota, Titulo } from '../components/ui.jsx';
import { useFleet } from '../context/FleetContext.jsx';
import { useAcao } from '../hooks/useAcao.js';

export default function Devices() {
  const { fleet, atualizar } = useFleet();
  // null = lista ainda não carregada (mostra "Carregando…")
  const [devices, setDevices] = useState(null);
  const listar = useAcao(api.listDevices);
  const executarListar = listar.executar;

  const carregar = useCallback(async () => {
    const resultado = await executarListar();
    if (resultado.ok) {
      setDevices(resultado.valor);
    }
  }, [executarListar]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // device_id -> status, a partir do último retrato da frota
  const statusPorId = useMemo(
    () => Object.fromEntries((fleet?.vinherias ?? []).map((v) => [v.device_id, v.status])),
    [fleet],
  );

  const aposMudanca = useCallback(async () => {
    await carregar();
    atualizar();
  }, [carregar, atualizar]);

  return (
    <section>
      <Titulo>Dispositivos</Titulo>
      <DeviceForm onCreated={aposMudanca} />
      <MensagemErro erro={listar.erro} />
      {devices === null ? (
        <Nota>{listar.erro ? 'Não foi possível carregar a lista.' : 'Carregando…'}</Nota>
      ) : (
        <DeviceList devices={devices} statusPorId={statusPorId} onDeleted={aposMudanca} />
      )}
    </section>
  );
}
```

- [ ] **Passo 4: ligar no `App.jsx`** — importar `import Devices from './pages/Devices.jsx';` e trocar a rota:

```jsx
          <Route path="/dispositivos" element={<Devices />} />
```

- [ ] **Passo 5: verificar no navegador** (backend + EC2 ligados).
  1. `/dispositivos` lista `vinheria001` e `vinheria002` com o status da frota.
  2. Id `vinheria3` → "O id deve seguir o formato vinheria00N…", **sem** requisição na aba Network.
  3. Cadastrar `vinheria099` / "Vinheria Teste" / "Recife" → botão "Provisionando no FIWARE…" desabilitado; depois a linha aparece com "Aguardando 1º ciclo" e, em seguida, o status da frota (sem Wokwi: "Offline" após `offline_seconds`, ou "Configurando"). Nenhum toast para ela até lá (R4.4).
  4. Cadastrar `vinheria099` de novo → mensagem 409 do backend no formulário.
  5. Excluir a `vinheria099` → confirmação com o texto do STH; "Removendo…"; a linha some. Cancelar a confirmação não faz requisição.
  6. `npm test` → **30 passed**. Console sem erros.

- [ ] **Passo 6: commit**

```bash
git add frontend/src/components/DeviceForm.jsx frontend/src/components/DeviceList.jsx frontend/src/pages/Devices.jsx frontend/src/App.jsx
git commit -m "feat: adiciona a tela de cadastro e remocao de vinherias"
```

---

## Subtarefa 5A.9 — Verificação final e documentação

**Files:**
- Modify: `PLANO-CP5-VINHERIA.md` (nota de fechamento da Task 5A), `docs/specs/task-5a-front-base-devices/plan.md` (estado)

- [ ] **Passo 1: suíte e build**

```bash
cd frontend
npm test
npm run build
```
Esperado: **30 passed**; build sem erro. Conferir também que o backend segue verde: `cd ../backend && .venv/Scripts/python -m pytest tests -q` → **281 passed** (nada no backend mudou).

- [ ] **Passo 2: conferências estáticas**

```bash
grep -rn "fetch(" frontend/src --include=*.jsx      # esperado: nada
grep -rln "fetch(" frontend/src                     # esperado: só src/api/client.js e src/api/client.test.js
grep -rn "localhost\|:8000\|:1026" frontend/src      # esperado: nada
find frontend/src -name "*.ts" -o -name "*.tsx"      # esperado: nada
grep -rn "<a \|href=\|window.location" frontend/src  # esperado: nada (navegação só pelo react-router-dom)
find frontend/src -name "*.css"                      # esperado: só src/styles.css
grep -rn "style={" frontend/src                      # esperado: nada
ls frontend/tailwind.config.* frontend/postcss.config.* 2>/dev/null   # esperado: nada (Tailwind v4 pelo plugin do Vite)
grep -rn "<h1\|<input\|<button" frontend/src --include=*.jsx | grep -v "components/ui.jsx"   # esperado: só o botão × do toast em AlertBanner.jsx
grep -rn "try {" frontend/src/components frontend/src/pages   # esperado: nada (ações passam por useAcao)
grep -rn "createContext" frontend/src | grep -v criarContexto.js   # esperado: nada
grep -rn "/vinherias/\${" frontend/src | grep -v "components/ui.jsx"   # esperado: nada (links passam por LinkVinheria)
wc -l frontend/src/**/*.js* frontend/src/*.js*       # nenhum acima de ~250
```

- [ ] **Passo 3: ensaio completo no navegador** — repetir em sequência os passos de verificação de 5A.6, 5A.7 e 5A.8 numa sessão só, com `npm run dev`. Anotar o que divergir.

- [ ] **Passo 4: documentar** — em `PLANO-CP5-VINHERIA.md`, na seção da Task 5, acrescentar no topo uma nota `> **5A FEITA em <data>** — commits <primeiro>..<último>; 30 testes do front; desvios: …` (ou "nenhum"). No topo deste `plan.md`, uma linha `> **Estado em <data>:** feitas as subtarefas 5A.1 a 5A.9.`

- [ ] **Passo 5: commit**

```bash
git add PLANO-CP5-VINHERIA.md docs/specs/task-5a-front-base-devices/plan.md
git commit -m "docs: fecha a task 5a com a base do painel e o cadastro de vinherias"
```
