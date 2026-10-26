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
