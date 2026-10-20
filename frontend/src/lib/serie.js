/**
 * Janela dos gráficos (últimos N pontos ou intervalo de datas) e conversão
 * do histórico do STH-Comet ([{ ts, value }]) para o formato do Chart.js.
 */

/**
 * Parâmetros do GET de histórico para a janela escolhida. Datas vêm do
 * campo datetime-local (hora local) e saem em ISO. Janela inválida
 * devolve { erro } em vez dos parâmetros.
 */
export function parametrosJanela(janela) {
  if (janela.tipo === 'ultimos') {
    return { lastN: janela.n };
  }
  if (!janela.de || !janela.ate) {
    return { erro: 'Informe o início e o fim.' };
  }
  const de = new Date(janela.de);
  const ate = new Date(janela.ate);
  if (Number.isNaN(de.getTime()) || Number.isNaN(ate.getTime())) {
    return { erro: 'Data inválida.' };
  }
  if (de >= ate) {
    return { erro: 'O início precisa ser antes do fim.' };
  }
  return { dateFrom: de.toISOString(), dateTo: ate.toISOString() };
}

/** Rótulos HH:mm:ss (hora local) e valores, na ordem recebida. */
export function paraSerie(pontos) {
  return {
    rotulos: pontos.map((ponto) =>
      new Date(ponto.ts).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    ),
    valores: pontos.map((ponto) => ponto.value),
  };
}
