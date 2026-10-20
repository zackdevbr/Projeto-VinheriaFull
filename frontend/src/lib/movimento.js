/**
 * Preferência do sistema por menos movimento (prefers-reduced-motion).
 * Usada pela contagem dos números e pelas animações do Chart.js. Fora do
 * navegador (testes), responde false.
 */
export function prefereMenosMovimento() {
  return globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}
