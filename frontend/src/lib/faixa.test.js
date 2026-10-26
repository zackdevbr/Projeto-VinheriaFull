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

/** Testes da validação da faixa ideal e do "fora da faixa" (spec R2.4, R2.9). */
import { describe, expect, it } from 'vitest';
import { FAIXA_PADRAO } from '../constants.js';
import { camposDaFaixa, foraDaFaixa, validarFaixa } from './faixa.js';

const valida = {
  temperature: { min: '12,5', max: '18' },
  humidity: { min: 50, max: 70 },
  luminosity: { min: '0', max: '30' },
};

describe('validarFaixa', () => {
  it('aceita vírgula ou ponto e devolve números', () => {
    expect(validarFaixa(valida)).toEqual({
      dados: {
        temperature: { min: 12.5, max: 18 },
        humidity: { min: 50, max: 70 },
        luminosity: { min: 0, max: 30 },
      },
      erros: {},
    });
  });

  it('recusa campo vazio ou não numérico', () => {
    const resultado = validarFaixa({ ...valida, temperature: { min: '', max: '18' }, humidity: { min: 50, max: 'abc' } });
    expect(resultado.dados).toBeNull();
    expect(resultado.erros['temperature.min']).toBe('Informe um número');
    expect(resultado.erros['humidity.max']).toBe('Informe um número');
  });

  it('recusa mínimo maior ou igual ao máximo, com o erro no campo máximo', () => {
    const resultado = validarFaixa({ ...valida, luminosity: { min: '30', max: '30' } });
    expect(resultado.dados).toBeNull();
    expect(resultado.erros['luminosity.max']).toMatch(/menor que o máximo/);
  });

  it('recusa hexadecimal, notação científica e lixo que Number() aceitaria', () => {
    for (const texto of ['0x10', '1e3', 'Infinity', '1,5,5', '--3', '1.']) {
      const resultado = validarFaixa({ ...valida, temperature: { min: texto, max: '18' } });
      expect(resultado.dados).toBeNull();
      expect(resultado.erros['temperature.min']).toBe('Informe um número');
    }
  });

  it('aceita negativo, decimal com vírgula ou ponto e espaços nas pontas', () => {
    const resultado = validarFaixa({ ...valida, temperature: { min: ' -5,5 ', max: '18.25' } });
    expect(resultado.dados.temperature).toEqual({ min: -5.5, max: 18.25 });
  });

  it('atributo ausente dá erro nos dois campos', () => {
    const { luminosity, ...semLuz } = valida;
    const resultado = validarFaixa(semLuz);
    expect(resultado.erros['luminosity.min']).toBe('Informe um número');
    expect(resultado.erros['luminosity.max']).toBe('Informe um número');
  });
});

describe('foraDaFaixa', () => {
  const faixa = { min: 12, max: 18 };

  it('só fora quando passa do limite (limite exato está dentro)', () => {
    expect(foraDaFaixa(11.9, faixa)).toBe(true);
    expect(foraDaFaixa(18.1, faixa)).toBe(true);
    expect(foraDaFaixa(12, faixa)).toBe(false);
    expect(foraDaFaixa(18, faixa)).toBe(false);
  });

  it('valor ou faixa ausentes não contam como fora', () => {
    expect(foraDaFaixa(null, faixa)).toBe(false);
    expect(foraDaFaixa(15, null)).toBe(false);
  });
});

describe('camposDaFaixa', () => {
  it('converte a faixa em números para os campos de texto do formulário', () => {
    expect(camposDaFaixa({ temperature: { min: 12.5, max: 18 }, humidity: { min: 50, max: 70 }, luminosity: { min: 0, max: 30 } })).toEqual({
      temperature: { min: '12.5', max: '18' },
      humidity: { min: '50', max: '70' },
      luminosity: { min: '0', max: '30' },
    });
  });
});

describe('FAIXA_PADRAO', () => {
  it('segue o PRD (RF11): 12–18 °C, 50–70 % de umidade, luz de 0 a 30 %', () => {
    expect(FAIXA_PADRAO).toEqual({
      temperature: { min: 12, max: 18 },
      humidity: { min: 50, max: 70 },
      luminosity: { min: 0, max: 30 },
    });
  });

  it('passa pela validação do formulário sem mudar de valor', () => {
    expect(validarFaixa(camposDaFaixa(FAIXA_PADRAO)).dados).toEqual(FAIXA_PADRAO);
  });
});
