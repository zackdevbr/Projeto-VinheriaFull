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
