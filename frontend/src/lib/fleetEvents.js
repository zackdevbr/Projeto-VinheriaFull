/**
 * Eventos da frota: compara dois retratos de GET /api/fleet e diz o que
 * mudou, para o painel avisar (RF14). Funções puras, sem React, testadas
 * em fleetEvents.test.js.
 *
 * Regras (spec R4): avisa quando uma vinheria entra em alerta, fica offline
 * ou volta ao normal. A queda da EC2 deixa todas offline de uma vez; nesse
 * caso sai um único aviso da EC2, não um por vinheria.
 */
import { LIMITE_TOASTS } from '../constants.js';

/** Lista os eventos entre o retrato anterior e o atual ([] na primeira leitura). */
export function diffFleet(anterior, atual) {
  if (!anterior || !atual) {
    return [];
  }
  const quando = atual.updated_at ?? new Date().toISOString();
  const eventos = [];
  if (anterior.fiware_online && !atual.fiware_online) {
    eventos.push(criarEvento('fiware_offline', null, quando));
  }
  if (!anterior.fiware_online && atual.fiware_online) {
    eventos.push(criarEvento('fiware_online', null, quando));
  }
  const antes = new Map(anterior.vinherias.map((v) => [v.device_id, v]));
  for (const depois of atual.vinherias) {
    const previa = antes.get(depois.device_id);
    // Vinheria nova (ou mesmo status) não gera aviso
    if (!previa || previa.status === depois.status) {
      continue;
    }
    const tipo = tipoDaTransicao(previa, depois);
    if (tipo) {
      eventos.push(criarEvento(tipo, depois, quando));
    }
  }
  return eventos;
}

/** Tipo do evento de uma vinheria que mudou de status, ou null se não avisa. */
function tipoDaTransicao(previa, depois) {
  if (depois.status === 'alerta') {
    return 'alerta';
  }
  if (depois.status === 'offline') {
    // Offline por causa da EC2 já é avisado pelo evento único fiware_offline
    return depois.offline_reason === 'fiware' ? null : 'offline';
  }
  if (previa.status === 'offline') {
    // Volta da EC2 já é avisada pelo evento único fiware_online
    return previa.offline_reason === 'fiware' ? null : 'normal';
  }
  if (previa.status === 'alerta' && depois.status === 'ok') {
    return 'normal';
  }
  return null;
}

/** Monta o evento; o id é único por tipo, vinheria e retrato (serve de key do toast). */
function criarEvento(tipo, vinheria, quando) {
  return {
    id: `${tipo}:${vinheria?.device_id ?? 'fiware'}:${quando}`,
    tipo,
    device_id: vinheria?.device_id ?? null,
    name: vinheria?.name ?? null,
    city: vinheria?.city ?? null,
    at: quando,
  };
}

/** Frase em português mostrada no toast. */
export function textoDoEvento(evento) {
  const quem = `${evento.name} (${evento.city})`;
  switch (evento.tipo) {
    case 'alerta':
      return `${quem} entrou em alerta`;
    case 'offline':
      return `${quem} ficou offline`;
    case 'normal':
      return `${quem} voltou ao normal`;
    case 'fiware_offline':
      return 'EC2/FIWARE fora do ar: todas as vinherias offline';
    case 'fiware_online':
      return 'EC2/FIWARE de volta';
    default:
      return quem;
  }
}

/** Empilha os eventos novos em cima dos toasts atuais, sem repetir id e até o limite. */
export function empilharToasts(atuais, novos, limite = LIMITE_TOASTS) {
  const existentes = new Set(atuais.map((toast) => toast.id));
  const ineditos = [...novos].reverse().filter((evento) => !existentes.has(evento.id));
  return [...ineditos, ...atuais].slice(0, limite);
}

/**
 * Resumo para a faixa fixa: EC2 fora, vinherias em alerta e offline (sem
 * contar as offline por causa da EC2). null enquanto não há retrato.
 */
export function bannerSummary(frota) {
  if (!frota) {
    return null;
  }
  const fiwareOffline = !frota.fiware_online;
  const emAlerta = frota.vinherias.filter((v) => v.status === 'alerta');
  const offline = frota.vinherias.filter((v) => v.status === 'offline' && v.offline_reason !== 'fiware');
  return {
    fiwareOffline,
    emAlerta,
    offline,
    visivel: fiwareOffline || emAlerta.length > 0 || offline.length > 0,
  };
}

/**
 * Quantas vinherias pedem atenção (em alerta ou offline por falta de
 * leitura), para o selo do item Alertas no menu. Usa as mesmas regras da
 * faixa (bannerSummary): a queda da EC2 aparece na faixa, não no selo.
 */
export function contarAtencao(frota) {
  const resumo = bannerSummary(frota);
  return resumo ? resumo.emAlerta.length + resumo.offline.length : 0;
}
