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
 * Normalização do status de uma vinheria para a interface. O backend pode
 * ganhar status novos; o painel desenha só os que conhece (STATUS_ROTULO)
 * e trata qualquer outro como "aguardando", em vez de quebrar a tela.
 */
import { STATUS_ROTULO } from '../constants.js';

export function statusConhecido(status) {
  return Object.hasOwn(STATUS_ROTULO, status) ? status : 'aguardando';
}
