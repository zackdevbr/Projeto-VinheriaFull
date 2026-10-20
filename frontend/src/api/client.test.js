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
