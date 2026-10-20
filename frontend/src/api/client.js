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
