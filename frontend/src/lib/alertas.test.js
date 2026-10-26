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

/** Testes dos textos da linha do tempo de alertas (spec R2.7, R2.8). */
import { describe, expect, it } from 'vitest';
import { duracao, formatarDataHora, rotuloAlerta } from './alertas.js';

describe('duracao', () => {
  it('descreve a duração em texto curto', () => {
    expect(duracao(null)).toBe('em aberto');
    expect(duracao(0)).toBe('0 s');
    expect(duracao(45)).toBe('45 s');
    expect(duracao(60)).toBe('1 min 0 s');
    expect(duracao(252)).toBe('4 min 12 s');
    expect(duracao(3600)).toBe('1 h 0 min');
    expect(duracao(7380)).toBe('2 h 3 min');
  });

  it('a partir de 24 horas conta em dias (com as horas que sobram)', () => {
    expect(duracao(86399)).toBe('23 h 59 min');
    expect(duracao(86400)).toBe('1 dia 0 h');
    expect(duracao(120900)).toBe('1 dia 9 h');
    expect(duracao(3 * 86400 + 5 * 3600 + 20 * 60)).toBe('3 dias 5 h');
  });
});

describe('rotuloAlerta', () => {
  it('sensor mostra nome, valor em pt-BR e unidade', () => {
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'temperature', value: 21.44 })).toBe('Temperatura 21,4 °C');
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'humidity', value: 75 })).toBe('Umidade 75 %');
  });

  it('offline da vinheria e queda da EC2 têm texto próprio', () => {
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'offline', value: null })).toBe('Offline');
    expect(rotuloAlerta({ device_id: 'fiware', attr: 'offline', value: null })).toBe('EC2 / FIWARE fora do ar');
  });

  it('sem valor mostra só o nome do atributo', () => {
    expect(rotuloAlerta({ device_id: 'vinheria001', attr: 'luminosity', value: null })).toBe('Luminosidade');
  });
});

describe('formatarDataHora', () => {
  it('mostra dia/mês e hora:minuto', () => {
    expect(formatarDataHora('2026-10-19T14:32:00Z')).toMatch(/^\d{2}\/\d{2} \d{2}:\d{2}$/);
  });
});
