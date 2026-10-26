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
 * Formatação de números para a tela, no padrão brasileiro (vírgula decimal).
 */

/** Sem `casas`, usa até uma casa decimal; com `casas`, fixa a quantidade (evita "pular" durante a contagem). */
export function formatarNumero(numero, casas) {
  const opcoes = casas === undefined
    ? { maximumFractionDigits: 1 }
    : { minimumFractionDigits: casas, maximumFractionDigits: casas };
  return numero.toLocaleString('pt-BR', opcoes);
}
