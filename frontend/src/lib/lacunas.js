/**
 * Desenho do "registro pausado" no gráfico: os períodos em que o sensor
 * ficou sem enviar leituras (desligado ou offline). É um plugin do Chart.js
 * em duas camadas:
 *  - por baixo da linha, uma faixa rosé suave com hachura diagonal fina (o
 *    traço de gravura dos rótulos de vinho) e bordas finas;
 *  - por cima, uma etiqueta em pílula creme com o símbolo de pausa e o
 *    tamanho da pausa; etiquetas que se tocariam sobem para outra linha.
 * Nada depende só de cor: a hachura e o símbolo de pausa dizem "sem dados".
 *
 * Recebe tudo pelas opções do gráfico (options.plugins.lacunas): { lacunas,
 * corFundo, corHachura, corBorda, corPilula, corPilulaBorda, corTexto }, em
 * que `lacunas` vem de paraSerie (lib/serie.js) e as cores dos tokens do tema.
 */
import { duracao } from './alertas.js';

// Gráfico mais estreito que isto (celular) usa etiquetas menores, para cobrir menos a linha
const LARGURA_COMPACTA = 520;
const FOLGA = 4;
const PASSO_HACHURA = 7;

/**
 * Distribui etiquetas (intervalos horizontais { inicio, fim }, em ordem) em
 * linhas, para que nenhuma cubra outra: cada uma vai para a primeira linha
 * cujo último intervalo termina com pelo menos `folga` de distância.
 * Devolve o índice da linha de cada etiqueta.
 */
export function linhasSemSobreposicao(intervalos, folga) {
  const fimDaLinha = [];
  return intervalos.map(({ inicio, fim }) => {
    let linha = fimDaLinha.findIndex((fimAnterior) => inicio - fimAnterior >= folga);
    if (linha === -1) {
      linha = fimDaLinha.length;
    }
    fimDaLinha[linha] = fim;
    return linha;
  });
}

/** Retângulo com cantos arredondados (a API roundRect nem sempre existe). */
function caminhoArredondado(ctx, x, y, largura, altura, raio) {
  ctx.beginPath();
  ctx.moveTo(x + raio, y);
  ctx.arcTo(x + largura, y, x + largura, y + altura, raio);
  ctx.arcTo(x + largura, y + altura, x, y + altura, raio);
  ctx.arcTo(x, y + altura, x, y, raio);
  ctx.arcTo(x, y, x + largura, y, raio);
  ctx.closePath();
}

/** Símbolo de pausa (duas barras) com o canto superior esquerdo em (x, y). */
function desenharPausa(ctx, x, y, tamanho) {
  const barra = tamanho * 0.32;
  ctx.fillRect(x, y, barra, tamanho);
  ctx.fillRect(x + tamanho - barra, y, barra, tamanho);
}

/** Limites horizontais de cada vão: entre a última leitura antes e a primeira depois. */
function limitesDosVaos(grafico, lacunas) {
  const pontos = grafico.getDatasetMeta(0).data;
  return lacunas
    .map(({ indice, segundos }) => ({ antes: pontos[indice - 1], depois: pontos[indice + 1], segundos }))
    .filter(({ antes, depois }) => antes && depois)
    .map(({ antes, depois, segundos }) => ({ inicio: antes.x, fim: depois.x, segundos }));
}

export const pluginLacunas = {
  id: 'lacunas',

  // Por baixo da linha: faixa suave, hachura e bordas
  beforeDatasetsDraw(grafico, _args, opcoes) {
    const vaos = limitesDosVaos(grafico, opcoes?.lacunas ?? []);
    if (vaos.length === 0) {
      return;
    }
    const { ctx, chartArea } = grafico;
    const altura = chartArea.bottom - chartArea.top;
    ctx.save();
    for (const { inicio, fim } of vaos) {
      ctx.fillStyle = opcoes.corFundo;
      ctx.fillRect(inicio, chartArea.top, fim - inicio, altura);

      // Hachura diagonal a 45°, recortada na faixa
      ctx.save();
      ctx.beginPath();
      ctx.rect(inicio, chartArea.top, fim - inicio, altura);
      ctx.clip();
      ctx.strokeStyle = opcoes.corHachura;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = inicio - altura; x < fim; x += PASSO_HACHURA) {
        ctx.moveTo(x, chartArea.bottom);
        ctx.lineTo(x + altura, chartArea.top);
      }
      ctx.stroke();
      ctx.restore();

      // Bordas finas nas duas pontas do vão
      ctx.strokeStyle = opcoes.corBorda;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (const x of [inicio, fim]) {
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
      }
      ctx.stroke();
    }
    ctx.restore();
  },

  // Por cima da linha: etiqueta em pílula com o símbolo de pausa e o tempo parado
  afterDatasetsDraw(grafico, _args, opcoes) {
    const vaos = limitesDosVaos(grafico, opcoes?.lacunas ?? []);
    if (vaos.length === 0) {
      return;
    }
    const { ctx, chartArea } = grafico;
    const compacto = chartArea.right - chartArea.left < LARGURA_COMPACTA;
    const alturaPilula = compacto ? 20 : 24;
    const margem = compacto ? 8 : 12;
    const tamanhoIcone = compacto ? 8 : 10;
    ctx.save();
    ctx.font = `600 ${compacto ? 10 : 11}px ${grafico.options.font?.family ?? 'sans-serif'}`;
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left';

    const etiquetas = vaos.map(({ inicio, fim, segundos }) => {
      const texto = duracao(segundos);
      const largura = margem + tamanhoIcone + 5 + ctx.measureText(texto).width + margem;
      // Centrada no vão, sem sair da área do gráfico
      const centro = Math.min(
        Math.max((inicio + fim) / 2, chartArea.left + largura / 2),
        chartArea.right - largura / 2,
      );
      return { texto, largura, inicio: centro - largura / 2, fim: centro + largura / 2 };
    });
    const linhas = linhasSemSobreposicao(etiquetas, FOLGA);

    etiquetas.forEach((etiqueta, i) => {
      const y = chartArea.top + 6 + linhas[i] * (alturaPilula + FOLGA);
      caminhoArredondado(ctx, etiqueta.inicio, y, etiqueta.largura, alturaPilula, alturaPilula / 2);
      ctx.fillStyle = opcoes.corPilula;
      ctx.fill();
      ctx.strokeStyle = opcoes.corPilulaBorda;
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = opcoes.corTexto;
      desenharPausa(ctx, etiqueta.inicio + margem, y + (alturaPilula - tamanhoIcone) / 2, tamanhoIcone);
      ctx.fillText(etiqueta.texto, etiqueta.inicio + margem + tamanhoIcone + 5, y + alturaPilula / 2 + 0.5);
    });
    ctx.restore();
  },
};
