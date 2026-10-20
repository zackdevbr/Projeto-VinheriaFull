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
