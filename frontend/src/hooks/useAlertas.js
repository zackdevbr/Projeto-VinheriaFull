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

/**
 * Alertas de uma vinheria (ou de todas, com deviceId null), relidos a cada
 * 10 s, para a linha do tempo do detalhe e a página de alertas.
 */
import { useCallback } from 'react';
import { api } from '../api/client.js';
import { LEITURA_POLL_MS } from '../constants.js';
import { useLeitura } from './useLeitura.js';

export function useAlertas(deviceId, limite) {
  const carregar = useCallback(() => api.getAlerts({ deviceId, limit: limite }), [deviceId, limite]);
  return useLeitura(carregar, LEITURA_POLL_MS);
}
