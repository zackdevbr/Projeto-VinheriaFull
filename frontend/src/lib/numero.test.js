/** Testes da formatação de números em pt-BR usada no painel. */
import { describe, expect, it } from 'vitest';
import { formatarNumero } from './numero.js';

describe('formatarNumero', () => {
  it('sem casas fixas usa vírgula e até uma casa', () => {
    expect(formatarNumero(21.44)).toBe('21,4');
    expect(formatarNumero(75)).toBe('75');
  });

  it('com casas fixas mantém o número de casas', () => {
    expect(formatarNumero(16.9, 1)).toBe('16,9');
    expect(formatarNumero(17, 1)).toBe('17,0');
    expect(formatarNumero(91.6, 0)).toBe('92');
  });
});
