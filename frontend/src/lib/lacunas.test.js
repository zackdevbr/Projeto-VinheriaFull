/*
 * Smart Solutions — Monitoramento de Vinherias
 * CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
 * Integrantes:
 *   Eduarda Soares Moraes — RM569369
 *   Isac Nilton Fernandes de Oliveira — RM573282
 *   João Benedito de Oliveira Simplício — RM570206
 *   Julia Souza Matarazzo — RM571340
 *   Mariana Malagutti Gomes Peixoto — RM570290
 */

/** Testes do posicionamento das etiquetas dos vãos do gráfico, para uma não cobrir a outra. */
import { describe, expect, it } from 'vitest';
import { linhasSemSobreposicao } from './lacunas.js';

describe('linhasSemSobreposicao', () => {
  it('etiquetas que não se tocam ficam todas na primeira linha', () => {
    expect(linhasSemSobreposicao([{ inicio: 0, fim: 40 }, { inicio: 100, fim: 140 }], 4)).toEqual([0, 0]);
  });

  it('etiqueta que invade a anterior sobe para a linha de baixo', () => {
    expect(linhasSemSobreposicao([{ inicio: 0, fim: 60 }, { inicio: 50, fim: 110 }], 4)).toEqual([0, 1]);
  });

  it('a folga mínima entre etiquetas também conta como sobreposição', () => {
    expect(linhasSemSobreposicao([{ inicio: 0, fim: 40 }, { inicio: 42, fim: 80 }], 4)).toEqual([0, 1]);
    expect(linhasSemSobreposicao([{ inicio: 0, fim: 40 }, { inicio: 44, fim: 80 }], 4)).toEqual([0, 0]);
  });

  it('reaproveita a primeira linha que já esteja livre', () => {
    const intervalos = [{ inicio: 0, fim: 60 }, { inicio: 50, fim: 110 }, { inicio: 120, fim: 160 }];
    expect(linhasSemSobreposicao(intervalos, 4)).toEqual([0, 1, 0]);
  });

  it('três etiquetas coladas usam três linhas', () => {
    const intervalos = [{ inicio: 0, fim: 80 }, { inicio: 10, fim: 90 }, { inicio: 20, fim: 100 }];
    expect(linhasSemSobreposicao(intervalos, 4)).toEqual([0, 1, 2]);
  });

  it('sem etiquetas não há o que posicionar', () => {
    expect(linhasSemSobreposicao([], 4)).toEqual([]);
  });
});
