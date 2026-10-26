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
 * Caminhos das rotas do painel montados num lugar só (react-router-dom).
 */

/** Rota do detalhe de uma vinheria. */
export function caminhoVinheria(deviceId) {
  return `/vinherias/${encodeURIComponent(deviceId)}`;
}
