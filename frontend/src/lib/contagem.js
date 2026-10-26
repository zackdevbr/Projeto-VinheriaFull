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
 * Interpolação dos números que "contam" até o valor novo (valor de sensor,
 * score). Função pura, testada; o hook useContagem cuida do tempo.
 */

/** Valor entre `de` e `para` com easing ease-out cúbico; `progresso` vai de 0 a 1. */
export function interpolar(de, para, progresso) {
  if (de === para || progresso >= 1) {
    return para;
  }
  if (progresso <= 0) {
    return de;
  }
  const curva = 1 - (1 - progresso) ** 3;
  return de + (para - de) * curva;
}
