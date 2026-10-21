/** Testes da janela dos gráficos e da conversão do histórico (spec R2.5, R2.6). */
import { describe, expect, it } from 'vitest';
import { ApiError } from '../api/client.js';
import {
  descricaoJanela,
  paraSerie,
  parametrosJanela,
  resumoLacunas,
  rotuloDoEixo,
  semLeituras,
  tituloDoBalao,
  tituloDoPonto,
} from './serie.js';

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
  it('separa rótulos de data e hora e valores', () => {
    const serie = paraSerie([
      { ts: '2026-10-19T14:32:05.000Z', value: 21.4 },
      { ts: '2026-10-19T14:32:07.000Z', value: 21.5 },
    ]);
    expect(serie.valores).toEqual([21.4, 21.5]);
    expect(serie.rotulos).toHaveLength(2);
    for (const rotulo of serie.rotulos) {
      expect(rotulo).toMatch(/^\d{2}\/\d{2} \d{2}:\d{2}:\d{2}$/);
    }
  });

  it('lista vazia dá listas vazias', () => {
    expect(paraSerie([])).toEqual({ rotulos: [], valores: [], lacunas: [] });
  });
});

describe('semLeituras', () => {
  it('404 do STH-Comet quer dizer que o intervalo não tem leituras', () => {
    expect(semLeituras(new ApiError(404, 'No context element found', 'sth'))).toBe(true);
  });

  it('outros erros não são "sem leituras"', () => {
    expect(semLeituras(new ApiError(404, 'vinheria099 não encontrada', 'registry'))).toBe(false);
    expect(semLeituras(new ApiError(503, 'sem conexão', 'sth'))).toBe(false);
    expect(semLeituras(null)).toBe(false);
  });
});

describe('paraSerie com vãos', () => {
  // Leituras a cada 2 s, uma pausa de ~10 min e a volta
  const pontos = [
    { ts: '2026-10-19T10:00:00.000Z', value: 1 },
    { ts: '2026-10-19T10:00:02.000Z', value: 2 },
    { ts: '2026-10-19T10:00:04.000Z', value: 3 },
    { ts: '2026-10-19T10:10:00.000Z', value: 4 },
    { ts: '2026-10-19T10:10:02.000Z', value: 5 },
  ];

  it('insere um ponto vazio onde o sensor ficou sem enviar e guarda o tamanho da pausa', () => {
    const serie = paraSerie(pontos, 30);
    expect(serie.valores).toEqual([1, 2, 3, null, 4, 5]);
    expect(serie.rotulos).toHaveLength(6);
    expect(serie.lacunas).toEqual([{ indice: 3, segundos: 596 }]);
  });

  it('pausa igual ao limite não conta como vão; só acima dele', () => {
    const quase = [
      { ts: '2026-10-19T10:00:00.000Z', value: 1 },
      { ts: '2026-10-19T10:00:30.000Z', value: 2 },
      { ts: '2026-10-19T10:01:01.000Z', value: 3 },
    ];
    const serie = paraSerie(quase, 30);
    expect(serie.valores).toEqual([1, 2, null, 3]);
    expect(serie.lacunas).toEqual([{ indice: 2, segundos: 31 }]);
  });

  it('sem limite informado nunca cria vão', () => {
    expect(paraSerie(pontos).valores).toEqual([1, 2, 3, 4, 5]);
  });

  it('dois vãos têm índices que já contam o ponto vazio inserido antes', () => {
    const dois = [
      { ts: '2026-10-19T10:00:00.000Z', value: 1 },
      { ts: '2026-10-19T10:05:00.000Z', value: 2 },
      { ts: '2026-10-19T10:10:00.000Z', value: 3 },
    ];
    const serie = paraSerie(dois, 30);
    expect(serie.valores).toEqual([1, null, 2, null, 3]);
    expect(serie.lacunas.map((l) => l.indice)).toEqual([1, 3]);
  });
});

describe('resumoLacunas', () => {
  it('sem vãos não há o que dizer', () => {
    expect(resumoLacunas([])).toBeNull();
  });

  it('um vão diz quanto tempo o sensor ficou sem enviar', () => {
    expect(resumoLacunas([{ indice: 3, segundos: 843 }])).toBe('O sensor ficou 14 min 3 s sem enviar leituras.');
  });

  it('vários vãos dizem quantas vezes e a maior pausa', () => {
    expect(resumoLacunas([{ indice: 1, segundos: 40 }, { indice: 3, segundos: 7380 }])).toBe(
      'O sensor ficou sem enviar leituras 2 vezes; a maior pausa foi de 2 h 3 min.',
    );
  });
});

describe('descricaoJanela', () => {
  it('últimas N leituras explicam o que é uma leitura e quanto tempo cobrem', () => {
    expect(descricaoJanela({ tipo: 'ultimos', n: 50 })).toBe(
      'Mostra as últimas 50 leituras do sensor (uma a cada ~2 s, cerca de 1 min 40 s).',
    );
    expect(descricaoJanela({ tipo: 'ultimos', n: 20 })).toBe(
      'Mostra as últimas 20 leituras do sensor (uma a cada ~2 s, cerca de 40 s).',
    );
  });

  it('por período explica o que escolher', () => {
    expect(descricaoJanela({ tipo: 'datas', de: '', ate: '' })).toBe(
      'Escolha o início e o fim para ver as leituras desse intervalo.',
    );
  });
});

describe('rotuloDoEixo', () => {
  // O Chart.js só desenha algumas marcas (por amostragem); por isso cada marca mostra o
  // próprio dia, sem depender de outra marca ter sido desenhada antes
  it('cada marca mostra só o dia (dd/mm) do ponto dela, sem a hora', () => {
    expect(rotuloDoEixo('20/10 21:14:25')).toBe('20/10');
    expect(rotuloDoEixo('21/10 00:00:03')).toBe('21/10');
  });

  it('o dia aparece mesmo que a marca anterior seja do mesmo dia', () => {
    expect(rotuloDoEixo('20/10 21:14:27', ['20/10 21:14:25'])).toBe('20/10');
  });

  it('ponto vazio de um vão não ganha marca', () => {
    expect(rotuloDoEixo('')).toBe('');
  });
});

describe('tituloDoPonto', () => {
  it('no balão, a hora aparece junto do dia', () => {
    expect(tituloDoPonto('20/10 21:14:25')).toBe('20/10 às 21:14:25');
  });

  it('ponto vazio de um vão não tem título', () => {
    expect(tituloDoPonto('')).toBe('');
  });
});

describe('tituloDoBalao', () => {
  // O Chart.js chama o título do balão com os itens que sobraram depois do filtro;
  // sobre um vão do gráfico (ponto vazio) não sobra nenhum, e isso não pode quebrar o gráfico
  it('com a lista vazia (mouse sobre um vão) devolve texto vazio, sem lançar erro', () => {
    expect(() => tituloDoBalao([])).not.toThrow();
    expect(tituloDoBalao([])).toBe('');
  });

  it('com itens, usa o rótulo do primeiro: dia e hora', () => {
    expect(tituloDoBalao([{ label: '20/10 21:14:25' }])).toBe('20/10 às 21:14:25');
  });
});
