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
