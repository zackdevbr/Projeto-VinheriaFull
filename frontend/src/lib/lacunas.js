/**
 * Plugin do Chart.js que desenha os vãos do gráfico: quando o sensor ficou
 * sem enviar leituras (desligado ou offline), pinta uma faixa cinza entre a
 * última leitura antes da pausa e a primeira depois, com tracejado nas
 * bordas e o tamanho da pausa escrito na vertical. Recebe os vãos pelas
 * opções do gráfico (options.plugins.lacunas): { lacunas, cor, corBorda,
 * corTexto }, em que `lacunas` vem de paraSerie (lib/serie.js).
 */
import { duracao } from './alertas.js';

export const pluginLacunas = {
  id: 'lacunas',
  beforeDatasetsDraw(grafico, _args, opcoes) {
    const lacunas = opcoes?.lacunas ?? [];
    if (lacunas.length === 0) {
      return;
    }
    const { ctx, chartArea } = grafico;
    const pontos = grafico.getDatasetMeta(0).data;
    const altura = chartArea.bottom - chartArea.top;
    ctx.save();
    for (const { indice, segundos } of lacunas) {
      const antes = pontos[indice - 1];
      const depois = pontos[indice + 1];
      if (!antes || !depois) {
        continue;
      }
      ctx.fillStyle = opcoes.cor;
      ctx.fillRect(antes.x, chartArea.top, depois.x - antes.x, altura);

      ctx.strokeStyle = opcoes.corBorda;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      for (const x of [antes.x, depois.x]) {
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
      }
      ctx.stroke();

      // Texto na vertical, para caber mesmo numa faixa estreita; o curto se o longo não couber
      ctx.setLineDash([]);
      ctx.fillStyle = opcoes.corTexto;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = `600 11px ${grafico.options.font?.family ?? 'sans-serif'}`;
      const completo = `sensor sem leituras · ${duracao(segundos)}`;
      const texto = ctx.measureText(completo).width <= altura - 16 ? completo : duracao(segundos);
      ctx.translate((antes.x + depois.x) / 2, chartArea.top + altura / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(texto, 0, 0);
      ctx.rotate(Math.PI / 2);
      ctx.translate(-((antes.x + depois.x) / 2), -(chartArea.top + altura / 2));
    }
    ctx.restore();
  },
};
