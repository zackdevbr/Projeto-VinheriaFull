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

/** Testes do resumo, da ordem e do "visto há" da frota (spec R2.1–R2.3). */
import { describe, expect, it } from 'vitest';
import { ordenarFrota, resumoFrota, textoVisto, vistoHa } from './frota.js';

const v = (device_id, status) => ({ device_id, status });

describe('resumoFrota', () => {
  it('sem frota devolve tudo zero', () => {
    expect(resumoFrota(null)).toEqual({ total: 0, ok: 0, alerta: 0, offline: 0, configurando: 0 });
  });

  it('conta cada status e o total', () => {
    const frota = { vinherias: [v('a', 'ok'), v('b', 'ok'), v('c', 'alerta'), v('d', 'offline'), v('e', 'configurando')] };
    expect(resumoFrota(frota)).toEqual({ total: 5, ok: 2, alerta: 1, offline: 1, configurando: 1 });
  });
});

describe('ordenarFrota', () => {
  const lista = [
    v('vinheria005', 'ok'),
    v('vinheria003', 'alerta'),
    v('vinheria002', 'configurando'),
    v('vinheria004', 'offline'),
    v('vinheria001', 'alerta'),
    v('vinheria006', 'manutencao'),
  ];

  it('põe alerta, offline, configurando e ok nessa ordem, desconhecido no fim', () => {
    expect(ordenarFrota(lista).map((x) => x.device_id)).toEqual([
      'vinheria001', 'vinheria003', 'vinheria004', 'vinheria002', 'vinheria005', 'vinheria006',
    ]);
  });

  it('não altera a lista recebida', () => {
    ordenarFrota(lista);
    expect(lista[0].device_id).toBe('vinheria005');
  });
});

describe('vistoHa', () => {
  it('descreve o tempo desde a última leitura', () => {
    expect(vistoHa(null)).toBe('sem leitura');
    expect(vistoHa(0)).toBe('agora');
    expect(vistoHa(4)).toBe('agora');
    expect(vistoHa(12)).toBe('há 12 s');
    expect(vistoHa(59)).toBe('há 59 s');
    expect(vistoHa(60)).toBe('há 1 min');
    expect(vistoHa(3599)).toBe('há 59 min');
    expect(vistoHa(7200)).toBe('há 2 h');
    expect(vistoHa(86399)).toBe('há 23 h');
    expect(vistoHa(86400)).toBe('há 1 dia');
    expect(vistoHa(86400 * 29)).toBe('há 29 dias');
    expect(vistoHa(86400 * 30)).toBe('há 1 mês');
    expect(vistoHa(86400 * 65)).toBe('há 2 meses');
    expect(vistoHa(86400 * 360)).toBe('há 1 ano');
    expect(vistoHa(86400 * 800)).toBe('há 2 anos');
  });
});

describe('textoVisto', () => {
  it('com a EC2 fora diz isso; senão o tempo desde a leitura', () => {
    expect(textoVisto({ offline_reason: 'fiware', seconds_since: 400 })).toBe('EC2 fora');
    expect(textoVisto({ offline_reason: null, seconds_since: 12 })).toBe('há 12 s');
  });
});
