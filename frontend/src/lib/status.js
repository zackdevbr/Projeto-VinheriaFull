/**
 * Normalização do status de uma vinheria para a interface. O backend pode
 * ganhar status novos; o painel desenha só os que conhece (STATUS_ROTULO)
 * e trata qualquer outro como "aguardando", em vez de quebrar a tela.
 */
import { STATUS_ROTULO } from '../constants.js';

export function statusConhecido(status) {
  return Object.hasOwn(STATUS_ROTULO, status) ? status : 'aguardando';
}
