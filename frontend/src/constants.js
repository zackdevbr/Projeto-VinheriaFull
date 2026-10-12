/**
 * Constantes do painel: intervalos de atualização, limite de toasts e os
 * rótulos em português de cada status de vinheria.
 */

// Polling da frota (RF14) e da saúde do FIWARE
export const FLEET_POLL_MS = 5000;
export const HEALTH_POLL_MS = 30000;

// Quantos avisos (toasts) ficam empilhados na tela ao mesmo tempo
export const LIMITE_TOASTS = 5;

// "aguardando" = cadastrada, mas o poller ainda não a incluiu na frota
export const STATUS_ROTULO = {
  ok: 'OK',
  alerta: 'Em alerta',
  offline: 'Offline',
  configurando: 'Configurando',
  aguardando: 'Aguardando 1º ciclo',
};
