/**
 * Textos da linha do tempo de alertas (RF10): o que aconteceu, quando e
 * por quanto tempo. A queda da EC2 é registrada com device_id 'fiware'.
 */
import { ID_FIWARE } from '../constants.js';
import { ATRIBUTO } from './atributos.js';
import { formatarNumero } from './numero.js';

/** Duração em texto curto; null quer dizer que o alerta ainda está aberto. */
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
  return `${Math.floor(segundos / 3600)} h ${Math.floor((segundos % 3600) / 60)} min`;
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
