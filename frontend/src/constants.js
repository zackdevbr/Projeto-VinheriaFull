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

// Imagens enviadas pelo usuário depois (Task 5B, spec R8): caminho do
// arquivo em frontend/public (ex.: '/logo.svg') ou null enquanto não chegam
export const LOGO_SRC = null;
export const IMAGEM_HEROI = '/heroi-adega.jpg';

// Leituras do detalhe e da página de alertas (histórico, score, alertas)
export const LEITURA_POLL_MS = 10000;

// device_id dos alertas que registram a EC2/FIWARE fora do ar
export const ID_FIWARE = 'fiware';

// Janela inicial dos gráficos do detalhe: os últimos 50 pontos
export const JANELA_PADRAO = { tipo: 'ultimos', n: 50 };

// Faixa ideal inicial de uma vinheria nova (PRD, RF11): é a mesma que o
// backend grava no cadastro e a que o formulário de cadastro já mostra
export const FAIXA_PADRAO = {
  temperature: { min: 12, max: 18 },
  humidity: { min: 50, max: 70 },
  luminosity: { min: 0, max: 30 },
};

// Cada leitura do sensor chega a cada ~2 s (PRD, RF03); usado para explicar
// quanto tempo cobrem as "últimas N leituras" dos gráficos
export const INTERVALO_LEITURA_S = 2;

// Pausa entre duas leituras acima da qual o gráfico mostra um vão (sensor
// desligado ou offline): é o mesmo padrão de 30 s do backend para offline
export const LACUNA_SEGUNDOS = 30;

// Pausas separadas por menos que isto de leituras seguidas (sensor que falha e
// volta por instantes) contam como uma pausa só no gráfico
export const JUNTAR_PAUSAS_SEGUNDOS = 60;
