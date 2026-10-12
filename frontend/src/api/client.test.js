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
