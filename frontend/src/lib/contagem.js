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
