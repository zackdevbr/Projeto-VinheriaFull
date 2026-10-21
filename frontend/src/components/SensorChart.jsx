/**
 * Gráfico do histórico de um atributo (RF05), lido do STH-Comet pelo
 * backend: área em gradiente bordô (referência B), linhas tracejadas no
 * mínimo e no máximo da faixa e um círculo vermelho em cada ponto fora
 * dela (forma, não só cor). A legenda, embaixo, explica cada elemento
 * com o valor dos limites. Com a janela "últimos N", relê a cada 10 s.
 * Um resumo em texto (só para leitor de tela) acompanha o canvas.
 */
import { Chart } from 'chart.js';
import { useCallback, useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import { api } from '../api/client.js';
import { LEITURA_POLL_MS } from '../constants.js';
import { useLeitura } from '../hooks/useLeitura.js';
import { ATRIBUTO } from '../lib/atributos.js';
import { foraDaFaixa } from '../lib/faixa.js';
import { gradienteVertical } from '../lib/graficos.js';
import { prefereMenosMovimento } from '../lib/movimento.js';
import { formatarNumero } from '../lib/numero.js';
import { paraSerie, parametrosJanela, semLeituras } from '../lib/serie.js';
import { corDoTema } from '../lib/tema.js';
import { Cartao, Esqueleto, EstadoVazio, MensagemErro, Subtitulo } from './ui/index.js';

// Texto da legenda dos pontos fora da faixa (também identifica o item ao escolher o desenho dele)
const ROTULO_FORA = 'Fora da faixa';

/** Série tracejada horizontal no valor de um limite da faixa. */
function linhaDeLimite(rotulo, valor, quantidade) {
  return {
    label: rotulo,
    data: Array(quantidade).fill(valor),
    borderColor: corDoTema('taupe'),
    borderWidth: 1.5,
    borderDash: [6, 4],
    pointRadius: 0,
    fill: false,
  };
}

/** Série vazia que só existe para a legenda explicar o círculo vermelho dos pontos fora da faixa. */
function legendaForaDaFaixa() {
  const alerta = corDoTema('alerta');
  return {
    label: ROTULO_FORA,
    data: [],
    showLine: false,
    pointRadius: 4,
    pointBackgroundColor: alerta,
    pointBorderColor: alerta,
    borderColor: alerta,
  };
}

/**
 * Dados do Chart.js: a leitura (com área e marcadores) e, havendo faixa, as
 * linhas dos limites com o valor na legenda e a explicação dos pontos fora.
 */
function montarDados(pontos, faixa, unidade) {
  const { rotulos, valores } = paraSerie(pontos);
  const alerta = corDoTema('alerta');
  const datasets = [
    {
      label: 'Leitura',
      data: valores,
      borderColor: corDoTema('bordo'),
      borderWidth: 2,
      tension: 0.3,
      fill: true,
      backgroundColor: gradienteVertical(corDoTema('bordo', 0.35), corDoTema('bordo', 0)),
      pointRadius: valores.map((valor) => (foraDaFaixa(valor, faixa) ? 4 : 0)),
      pointBackgroundColor: alerta,
      pointBorderColor: alerta,
    },
  ];
  if (faixa) {
    datasets.push(
      linhaDeLimite(`Limite mínimo da faixa (${formatarNumero(faixa.min)} ${unidade})`, faixa.min, valores.length),
      linhaDeLimite(`Limite máximo da faixa (${formatarNumero(faixa.max)} ${unidade})`, faixa.max, valores.length),
      legendaForaDaFaixa(),
    );
  }
  return { labels: rotulos, datasets };
}

/** Opções do Chart.js nas cores e na fonte do design system. */
function montarOpcoes(unidade) {
  const taupe = corDoTema('taupe');
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: prefereMenosMovimento() ? false : { duration: 250 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: taupe,
          usePointStyle: true,
          boxWidth: 24,
          padding: 16,
          // Traço para as linhas (leitura e limites); círculo para "Fora da faixa"
          generateLabels: (grafico) =>
            Chart.defaults.plugins.legend.labels.generateLabels(grafico).map((item) => ({
              ...item,
              pointStyle: item.text === ROTULO_FORA ? 'circle' : 'line',
            })),
        },
      },
      tooltip: {
        filter: (item) => item.datasetIndex === 0,
        callbacks: { label: (item) => `${formatarNumero(item.parsed.y)} ${unidade}` },
      },
    },
    scales: {
      x: { ticks: { color: taupe, maxTicksLimit: 6, maxRotation: 0 }, grid: { display: false } },
      y: { ticks: { color: taupe }, grid: { color: corDoTema('linha') } },
    },
  };
}

/** Resumo em texto da janela (último, mínimo e máximo), alternativa ao canvas para leitor de tela. */
function resumoEmTexto(atributo, pontos) {
  const valores = pontos.map((ponto) => ponto.value);
  const fmt = (valor) => `${formatarNumero(valor)} ${atributo.unidade}`;
  return `${atributo.rotulo}: ${pontos.length} leituras, última ${fmt(valores[valores.length - 1])}, mínima ${fmt(Math.min(...valores))}, máxima ${fmt(Math.max(...valores))}.`;
}

export default function SensorChart({ deviceId, attr, janela, faixa }) {
  const atributo = ATRIBUTO[attr];
  const carregar = useCallback(
    () => api.getHistory(deviceId, { attr, ...parametrosJanela(janela) }),
    [deviceId, attr, janela],
  );
  const { dados, erro, falha, carregando } = useLeitura(carregar, janela.tipo === 'ultimos' ? LEITURA_POLL_MS : null);
  const vazio = semLeituras(falha) || (dados !== null && dados.length === 0);
  const grafico = useMemo(() => (dados ? montarDados(dados, faixa, atributo.unidade) : null), [dados, faixa, atributo.unidade]);
  const opcoes = useMemo(() => montarOpcoes(atributo.unidade), [atributo.unidade]);

  let corpo;
  if (carregando && !dados) {
    corpo = <Esqueleto className="h-full" />;
  } else if (vazio) {
    corpo = (
      <EstadoVazio
        titulo="Sem leituras neste período"
        texto="O sensor não estava ativo nesse intervalo. Ele pode ter ficado desligado ou offline."
      />
    );
  } else if (grafico) {
    corpo = <Line data={grafico} options={opcoes} role="img" aria-label={`Gráfico de ${atributo.rotulo.toLowerCase()}`} />;
  }

  return (
    <Cartao larg={4}>
      <Subtitulo>{atributo.rotulo}</Subtitulo>
      <MensagemErro erro={semLeituras(falha) ? null : erro} />
      <div className="h-56 md:h-72">{corpo}</div>
      {dados && dados.length > 0 && <p className="sr-only">{resumoEmTexto(atributo, dados)}</p>}
    </Cartao>
  );
}
