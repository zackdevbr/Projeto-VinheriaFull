/** Testes de statusConhecido: status novo do backend não pode quebrar a tela (Task 5B). */
import { describe, expect, it } from 'vitest';
import { statusConhecido } from './status.js';

describe('statusConhecido', () => {
  it('mantém os status que o painel sabe desenhar', () => {
    for (const status of ['ok', 'alerta', 'offline', 'configurando', 'aguardando']) {
      expect(statusConhecido(status)).toBe(status);
    }
  });

  it('troca status desconhecido ou ausente por aguardando', () => {
    expect(statusConhecido('manutencao')).toBe('aguardando');
    expect(statusConhecido(undefined)).toBe('aguardando');
  });

  it('não aceita nomes herdados de Object', () => {
    expect(statusConhecido('toString')).toBe('aguardando');
    expect(statusConhecido('__proto__')).toBe('aguardando');
  });
});
