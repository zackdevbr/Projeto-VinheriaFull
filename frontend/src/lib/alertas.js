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
 * Textos da linha do tempo de alertas (RF10): o que aconteceu, quando e
 * por quanto tempo. A queda da EC2 é registrada com device_id 'fiware'.
 */
import { ID_FIWARE } from '../constants.js';
import { ATRIBUTO } from './atributos.js';
import { formatarNumero } from './numero.js';

/** Duração em texto curto (s, min, h e, de 24 h em diante, dias); null quer dizer que o alerta ainda está aberto. */
export function duracao(segundos) {
  if (segundos === null || segundos === undefined) {
    return 'em aberto';
  }
  if (segundos < 60) {
    return `${segundos} s`;
  }
  if (segundos < 3600) {
    return `${Math.floor(segundos / 60)} min ${segundos % 60} s`;
  }
  if (segundos < 86400) {
    return `${Math.floor(segundos / 3600)} h ${Math.floor((segundos % 3600) / 60)} min`;
  }
  // A partir de 24 horas conta em dias, com as horas que sobram
  const dias = Math.floor(segundos / 86400);
  return `${dias} ${dias === 1 ? 'dia' : 'dias'} ${Math.floor((segundos % 86400) / 3600)} h`;
}

/** O que aconteceu: "Temperatura 21,4 °C", "Offline" ou "EC2 / FIWARE fora do ar". */
export function rotuloAlerta(alerta) {
  if (alerta.device_id === ID_FIWARE) {
    return 'EC2 / FIWARE fora do ar';
  }
  if (alerta.attr === 'offline') {
    return 'Offline';
  }
  const atributo = ATRIBUTO[alerta.attr];
  if (!atributo) {
    return alerta.attr;
  }
  if (alerta.value === null || alerta.value === undefined) {
    return atributo.rotulo;
  }
  return `${atributo.rotulo} ${formatarNumero(alerta.value)} ${atributo.unidade}`;
}

/** Data e hora curtas (dd/mm HH:mm) no fuso local. */
export function formatarDataHora(iso) {
  return new Date(iso)
    .toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    .replace(', ', ' ');
}
