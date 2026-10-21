/**
 * Gráfico do histórico de um atributo (RF05), lido do STH-Comet pelo
 * backend: área em gradiente bordô (referência B), linhas tracejadas no
 * mínimo e no máximo da faixa e um círculo vermelho em cada ponto fora
 * dela (forma, não só cor). A legenda, embaixo, explica cada elemento
 * com o valor dos limites. Com a janela "últimos N", relê a cada 10 s.
 * Com o FIWARE fora do ar, o cartão avisa "FIWARE desligado" em vez do erro
 * técnico. Quando o sensor ficou sem enviar leituras (registro pausado), a
 * linha quebra e uma faixa hachurada marca o vão, com o tempo parado. Um
 * resumo em texto (só para leitor de tela) acompanha o canvas.
 */
import { Chart } from 'chart.js';
import { Pause } from 'lucide-react';
import { useCallback, useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import { api } from '../api/client.js';
import { JUNTAR_PAUSAS_SEGUNDOS, LACUNA_SEGUNDOS, LEITURA_POLL_MS } from '../constants.js';
import { useLeitura } from '../hooks/useLeitura.js';
import { ATRIBUTO } from '../lib/atributos.js';
import { foraDaFaixa } from '../lib/faixa.js';
import { gradienteVertical } from '../lib/graficos.js';
import { pluginLacunas } from '../lib/lacunas.js';
import { prefereMenosMovimento } from '../lib/movimento.js';
import { formatarNumero } from '../lib/numero.js';
import {
  fiwareForaDoAr,
  paraSerie,
  parametrosJanela,
  resumoLacunas,
  rotuloDoEixo,
  semLeituras,
  tituloDoBalao,
} from '../lib/serie.js';
import { corDoTema } from '../lib/tema.js';
import { Cartao, Esqueleto, EstadoVazio, MensagemErro, Subtitulo } from './ui/index.js';

// Texto da legenda dos pontos fora da faixa (também identifica o item ao escolher o desenho dele)
const ROTULO_FORA = 'Fora da faixa';
// Texto da legenda do período em que o sensor ficou sem enviar leituras
const ROTULO_PAUSA = 'Registro pausado';

// Desenho de cada item da legenda: círculo para os pontos fora da faixa, selo arredondado para o registro pausado; traço para as linhas
const PONTO_DA_LEGENDA = { [ROTULO_FORA]: 'circle', [ROTULO_PAUSA]: 'rectRounded' };

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

/** Série vazia que só existe para a legenda explicar a faixa hachurada dos vãos (registro pausado). */
function legendaRegistroPausado() {
  const rose = corDoTema('rose');
  return {
    label: ROTULO_PAUSA,
    data: [],
    showLine: false,
    pointStyle: 'rectRounded',
    pointRadius: 6,
    pointBackgroundColor: corDoTema('rose', 0.25),
    pointBorderColor: rose,
    borderColor: rose,
  };
}

/**
 * Dados do Chart.js: a leitura (com área e marcadores) e, havendo faixa, as
 * linhas dos limites com o valor na legenda e a explicação dos pontos fora.
 */
function montarDados(serie, faixa, unidade) {
  const { rotulos, valores } = serie;
  const alerta = corDoTema('alerta');
  const datasets = [
    {
      label: 'Leitura',
      data: valores,
      borderColor: corDoTema('bordo'),
      borderWidth: 2,
      tension: 0.3,
      fill: true,
      spanGaps: false,
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
  if (serie.lacunas.length > 0) {
    datasets.push(legendaRegistroPausado());
  }
  return { labels: rotulos, datasets };
}

/** Opções do Chart.js nas cores e na fonte do design system. */
function montarOpcoes(unidade, lacunas) {
  const taupe = corDoTema('taupe');
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: prefereMenosMovimento() ? false : { duration: 250 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      lacunas: {
        lacunas,
        corFundo: corDoTema('rose', 0.12),
        corHachura: corDoTema('rose', 0.35),
        corBorda: corDoTema('rose', 0.6),
        corPilula: corDoTema('papel'),
        corPilulaBorda: corDoTema('rose'),
        corTexto: corDoTema('bordo'),
      },
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
              pointStyle: PONTO_DA_LEGENDA[item.text] ?? 'line',
            })),
        },
      },
      tooltip: {
        filter: (item) => item.datasetIndex === 0 && item.parsed.y !== null,
        callbacks: {
          title: tituloDoBalao,
          label: (item) => `${formatarNumero(item.parsed.y)} ${unidade}`,
        },
      },
    },
    scales: {
      x: {
        // Só o dia (dd/mm) em cada marca do eixo; a hora aparece no balão ao passar o mouse sobre o ponto
        ticks: {
          color: taupe,
          maxTicksLimit: 6,
          maxRotation: 0,
          callback(valor) {
            return rotuloDoEixo(this.getLabelForValue(valor));
          },
        },
        grid: { display: false },
      },
      y: { ticks: { color: taupe }, grid: { color: corDoTema('linha') } },
    },
  };
}

/** Resumo em texto da janela (último, mínimo e máximo), alternativa ao canvas para leitor de tela. */
function resumoEmTexto(atributo, pontos, lacunas) {
  const valores = pontos.map((ponto) => ponto.value);
  const fmt = (valor) => `${formatarNumero(valor)} ${atributo.unidade}`;
  return `${atributo.rotulo}: ${pontos.length} leituras, última ${fmt(valores[valores.length - 1])}, mínima ${fmt(Math.min(...valores))}, máxima ${fmt(Math.max(...valores))}.${lacunas.length > 0 ? ` ${resumoLacunas(lacunas)}` : ''}`;
}

export default function SensorChart({ deviceId, attr, janela, faixa }) {
  const atributo = ATRIBUTO[attr];
  const carregar = useCallback(() => {
    const parametros = parametrosJanela(janela);
    if (parametros.erro) {
      throw new Error(parametros.erro);
    }
    return api.getHistory(deviceId, { attr, ...parametros });
  }, [deviceId, attr, janela]);
  const { dados, erro, falha, carregando } = useLeitura(carregar, janela.tipo === 'ultimos' ? LEITURA_POLL_MS : null);
  const desligado = fiwareForaDoAr(falha);
  const vazio = semLeituras(falha) || (dados !== null && dados.length === 0);
  const serie = useMemo(() => (dados ? paraSerie(dados, LACUNA_SEGUNDOS, JUNTAR_PAUSAS_SEGUNDOS) : null), [dados]);
  const grafico = useMemo(() => (serie ? montarDados(serie, faixa, atributo.unidade) : null), [serie, faixa, atributo.unidade]);
  const opcoes = useMemo(() => montarOpcoes(atributo.unidade, serie?.lacunas ?? []), [atributo.unidade, serie]);
  const textoLacunas = serie ? resumoLacunas(serie.lacunas) : null;

  let corpo;
  if (carregando && !dados) {
    corpo = <Esqueleto className="h-full" />;
  } else if (desligado) {
    corpo = <EstadoVazio titulo="FIWARE desligado" texto="Os gráficos voltam assim que ele estiver no ar." />;
  } else if (vazio) {
    corpo = (
      <EstadoVazio
        titulo="Sem leituras neste período"
        texto="O sensor não estava ativo nesse intervalo. Ele pode ter ficado desligado ou offline."
      />
    );
  } else if (grafico) {
    corpo = <Line data={grafico} options={opcoes} plugins={[pluginLacunas]} role="img" aria-label={`Gráfico de ${atributo.rotulo.toLowerCase()}`} />;
  }

  return (
    <Cartao larg={4}>
      <Subtitulo>{atributo.rotulo}</Subtitulo>
      <MensagemErro erro={semLeituras(falha) || desligado ? null : erro} />
      <div className="h-64 md:h-72">{corpo}</div>
      {textoLacunas && (
        <div className="mt-4 flex items-start gap-3 rounded-xl border border-rose/40 bg-rose/10 px-4 py-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-full border border-rose/60 bg-papel text-bordo">
            <Pause size={16} strokeWidth={1.75} aria-hidden="true" />
          </span>
          <div className="min-w-0 text-sm">
            <p className="font-display text-lg leading-tight text-bordo">Registro pausado</p>
            <p className="mt-0.5 text-vinho">
              {textoLacunas} A faixa hachurada no gráfico marca esse período, sem dados.
            </p>
          </div>
        </div>
      )}
      {dados && dados.length > 0 && <p className="sr-only">{resumoEmTexto(atributo, dados, serie.lacunas)}</p>}
    </Cartao>
  );
}
