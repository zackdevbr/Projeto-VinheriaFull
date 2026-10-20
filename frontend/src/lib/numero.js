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
