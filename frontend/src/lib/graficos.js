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
 * Registro único do Chart.js: só os módulos que o painel usa (linha com
 * área e rosca), para o bundle não levar a biblioteca inteira. Quem desenha
 * <Line> ou <Doughnut> importa este arquivo. A fonte padrão vem do token
 * --font-sans (Inter).
 */
import {
  ArcElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { lerToken } from './tema.js';

Chart.register(
  ArcElement,
  CategoryScale,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
);
Chart.defaults.font.family = lerToken('--font-sans') || 'sans-serif';
Chart.defaults.font.size = 11;

/** Preenchimento em gradiente vertical (cor no topo, outra na base), calculado na área do gráfico. */
export function gradienteVertical(corTopo, corBase) {
  return ({ chart }) => {
    const { ctx, chartArea } = chart;
    if (!chartArea) {
      return corBase;
    }
    const gradiente = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    gradiente.addColorStop(0, corTopo);
    gradiente.addColorStop(1, corBase);
    return gradiente;
  };
}
