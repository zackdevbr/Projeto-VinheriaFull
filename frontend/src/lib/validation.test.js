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

/** Testes da validação do cadastro de vinheria no navegador (spec R6.1). */
import { describe, expect, it } from 'vitest';
import { validarCadastro } from './validation.js';

describe('validarCadastro', () => {
  it('aceita, limpa espaços e passa o id para minúsculas', () => {
    expect(validarCadastro({ device_id: ' Vinheria003 ', name: ' Vinheria Recife ', city: 'Recife ' }))
      .toEqual({ dados: { device_id: 'vinheria003', name: 'Vinheria Recife', city: 'Recife' }, erro: null });
  });

  it('recusa id fora do formato', () => {
    expect(validarCadastro({ device_id: 'vinheria3', name: 'A', city: 'B' }).erro).toMatch(/vinheria00N/);
  });

  it('recusa nome ou cidade vazios', () => {
    expect(validarCadastro({ device_id: 'vinheria003', name: '  ', city: 'B' }).erro).toMatch(/nome e cidade/);
  });

  it('recusa nome com mais de 60 caracteres', () => {
    expect(validarCadastro({ device_id: 'vinheria003', name: 'x'.repeat(61), city: 'B' }).erro).toMatch(/60/);
  });
});
