/** Testes da janela dos gráficos e da conversão do histórico (spec R2.5, R2.6). */
import { describe, expect, it } from 'vitest';
import { ApiError } from '../api/client.js';
import {
  descricaoJanela,
  fiwareForaDoAr,
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
    expect(serie.lacunas).toEqual([{ indice: 3, ultimoIndice: 3, segundos: 596, pausas: 1 }]);
  });

  it('pausa igual ao limite não conta como vão; só acima dele', () => {
    const quase = [
      { ts: '2026-10-19T10:00:00.000Z', value: 1 },
      { ts: '2026-10-19T10:00:30.000Z', value: 2 },
      { ts: '2026-10-19T10:01:01.000Z', value: 3 },
    ];
    const serie = paraSerie(quase, 30);
    expect(serie.valores).toEqual([1, 2, null, 3]);
    expect(serie.lacunas).toEqual([{ indice: 2, ultimoIndice: 2, segundos: 31, pausas: 1 }]);
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
  const pausa = (segundos, pausas = 1) => ({ indice: 1, ultimoIndice: 1, segundos, pausas });

  it('sem vãos não há o que dizer', () => {
    expect(resumoLacunas([])).toBeNull();
  });

  it('um vão diz quanto tempo o sensor ficou sem enviar', () => {
    expect(resumoLacunas([pausa(843)])).toBe('O sensor ficou 14 min 3 s sem enviar leituras.');
  });

  it('vários vãos dizem quantas vezes, o total parado e a maior pausa', () => {
    expect(resumoLacunas([pausa(600), pausa(7200)])).toBe(
      'O sensor ficou sem enviar leituras 2 vezes, somando 2 h 10 min; a maior pausa foi de 2 h 0 min.',
    );
  });

  it('uma pausa que juntou várias avisa que foram pausas seguidas', () => {
    expect(resumoLacunas([pausa(480, 3)])).toBe('O sensor ficou 8 min 0 s sem enviar leituras, em 3 pausas seguidas.');
  });

  it('tempos acima de 24 horas aparecem em dias', () => {
    expect(resumoLacunas([pausa(120900)])).toBe('O sensor ficou 1 dia 9 h sem enviar leituras.');
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

describe('paraSerie junta pausas contínuas', () => {
  // A, B, [pausa de 5 min], C, D, [pausa de 3 min], E, F: só 2 s de leituras entre as pausas
  const comPausasColadas = [
    { ts: '2026-10-19T10:00:00.000Z', value: 1 },
    { ts: '2026-10-19T10:00:02.000Z', value: 2 },
    { ts: '2026-10-19T10:05:02.000Z', value: 3 },
    { ts: '2026-10-19T10:05:04.000Z', value: 4 },
    { ts: '2026-10-19T10:08:04.000Z', value: 5 },
    { ts: '2026-10-19T10:08:06.000Z', value: 6 },
  ];

  it('pausas separadas por poucas leituras viram uma só, com o total parado', () => {
    const serie = paraSerie(comPausasColadas, 30, 60);
    expect(serie.valores).toEqual([1, 2, null, 3, 4, null, 5, 6]);
    expect(serie.lacunas).toEqual([{ indice: 2, ultimoIndice: 5, segundos: 480, pausas: 2 }]);
  });

  it('se as leituras entre as pausas duram mais que o limite, continuam duas pausas', () => {
    // 2 min de leituras a cada 20 s entre duas pausas de 5 min
    const separadas = [
      { ts: '2026-10-19T10:00:00.000Z', value: 1 },
      { ts: '2026-10-19T10:00:02.000Z', value: 2 },
      ...[2, 22, 42].flatMap((s) => [5, 6].map((m, i) => ({ ts: `2026-10-19T10:0${m}:${String(s).padStart(2, '0')}.000Z`, value: 10 + i }))),
      { ts: '2026-10-19T10:07:02.000Z', value: 3 },
      { ts: '2026-10-19T10:12:02.000Z', value: 4 },
    ].sort((x, y) => x.ts.localeCompare(y.ts));
    expect(paraSerie(separadas, 30, 60).lacunas.map((l) => l.pausas)).toEqual([1, 1]);
  });

  it('uma única leitura entre duas pausas também as une', () => {
    const umaLeitura = [
      { ts: '2026-10-19T10:00:00.000Z', value: 1 },
      { ts: '2026-10-19T10:05:00.000Z', value: 2 },
      { ts: '2026-10-19T10:10:00.000Z', value: 3 },
    ];
    expect(paraSerie(umaLeitura, 30, 60).lacunas).toEqual([{ indice: 1, ultimoIndice: 3, segundos: 600, pausas: 2 }]);
  });

  it('sem limite para juntar, cada pausa fica separada', () => {
    expect(paraSerie(comPausasColadas, 30).lacunas).toHaveLength(2);
  });

  it('três pausas coladas viram uma e somam tudo', () => {
    const tres = [
      { ts: '2026-10-19T10:00:00.000Z', value: 1 },
      { ts: '2026-10-19T10:02:00.000Z', value: 2 },
      { ts: '2026-10-19T10:04:00.000Z', value: 3 },
      { ts: '2026-10-19T10:06:00.000Z', value: 4 },
    ];
    expect(paraSerie(tres, 30, 60).lacunas).toEqual([{ indice: 1, ultimoIndice: 5, segundos: 360, pausas: 3 }]);
  });
});

describe('fiwareForaDoAr', () => {
  it('503 do backend quer dizer que o FIWARE não respondeu (EC2 desligada, IP errado ou timeout)', () => {
    expect(fiwareForaDoAr(new ApiError(503, 'tempo esgotado em http://1.2.3.4:8666/STH', 'sth'))).toBe(true);
    expect(fiwareForaDoAr(new ApiError(503, 'sem conexão', 'orion'))).toBe(true);
  });

  it('outros erros não são "FIWARE desligado"', () => {
    expect(fiwareForaDoAr(new ApiError(0, 'Backend indisponível'))).toBe(false);
    expect(fiwareForaDoAr(new ApiError(404, 'sem dados', 'sth'))).toBe(false);
    expect(fiwareForaDoAr(new ApiError(502, 'resposta inválida', 'sth'))).toBe(false);
    expect(fiwareForaDoAr(null)).toBe(false);
  });
});
