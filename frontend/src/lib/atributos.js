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
 * Os três atributos monitorados, com os nomes canônicos do FIWARE (chave),
 * o rótulo e a unidade da tela e o comando de alerta manual de cada um.
 * Fonte única para cartões, gráficos, faixa, comandos e linha do tempo.
 */
export const ATRIBUTOS = [
  { chave: 'temperature', rotulo: 'Temperatura', abreviado: 'Temp', curto: 'T', unidade: '°C', comando: 'blink_temp', botao: 'Piscar temperatura' },
  { chave: 'humidity', rotulo: 'Umidade', abreviado: 'Umid', curto: 'U', unidade: '%', comando: 'blink_hum', botao: 'Piscar umidade' },
  { chave: 'luminosity', rotulo: 'Luminosidade', abreviado: 'Luz', curto: 'L', unidade: '%', comando: 'blink_lux', botao: 'Piscar luz' },
];

// Mesmo conteúdo indexado pela chave (ex.: ATRIBUTO.temperature.unidade)
export const ATRIBUTO = Object.fromEntries(ATRIBUTOS.map((atributo) => [atributo.chave, atributo]));
