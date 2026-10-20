/**
 * Caminhos das rotas do painel montados num lugar só (react-router-dom).
 */

/** Rota do detalhe de uma vinheria. */
export function caminhoVinheria(deviceId) {
  return `/vinherias/${encodeURIComponent(deviceId)}`;
}
