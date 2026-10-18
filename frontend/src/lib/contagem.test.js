/** Testes da interpolação usada na contagem animada dos números (spec R6.1). */
import { describe, expect, it } from 'vitest';
import { interpolar } from './contagem.js';

describe('interpolar', () => {
  it('devolve o valor inicial no começo e o final no fim', () => {
    expect(interpolar(0, 10, 0)).toBe(0);
    expect(interpolar(0, 10, 1)).toBe(10);
  });

  it('prende o progresso fora de 0..1', () => {
    expect(interpolar(0, 10, -1)).toBe(0);
    expect(interpolar(0, 10, 1.5)).toBe(10);
  });

  it('é ease-out: no meio do tempo já passou da metade', () => {
    expect(interpolar(0, 10, 0.5)).toBeCloseTo(8.75);
  });

  it('funciona com valores negativos (temperatura)', () => {
    expect(interpolar(-5, 5, 0.5)).toBeCloseTo(3.75);
  });

  it('com início igual ao fim devolve o fim', () => {
    expect(interpolar(7, 7, 0.3)).toBe(7);
  });
});
