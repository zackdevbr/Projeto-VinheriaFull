/**
 * Leitura dos tokens do design system (styles.css) em runtime, para o
 * Chart.js, que desenha em canvas e não entende classes Tailwind. Assim a
 * paleta continua com fonte única no @theme e nenhum hex se repete aqui.
 */

/** Cor hex (#rrggbb) com transparência, no formato rgb moderno. */
export function comAlfa(hex, alfa) {
  const limpo = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((inicio) => parseInt(limpo.slice(inicio, inicio + 2), 16));
  return `rgb(${r} ${g} ${b} / ${alfa})`;
}

/** Valor de uma variável CSS do :root (ex.: '--font-sans'). */
export function lerToken(nome) {
  return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
}

/** Cor de um token (ex.: 'bordo'), opcionalmente com transparência. */
export function corDoTema(nome, alfa = 1) {
  const hex = lerToken(`--color-${nome}`);
  return alfa === 1 ? hex : comAlfa(hex, alfa);
}
