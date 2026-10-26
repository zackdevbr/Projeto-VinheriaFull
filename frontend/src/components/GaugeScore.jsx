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
 * Score de qualidade da vinheria (RF11) em rosca, no cartão bordô de
 * destaque (a rosca de uptime da referência B). O número central conta até
 * o valor; abaixo, a nota de cada atributo. Sem score, mostra "—" e o
 * motivo que o backend explica.
 */
import { Gauge } from 'lucide-react';
import { Doughnut } from 'react-chartjs-2';
import { useContagem } from '../hooks/useContagem.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import '../lib/graficos.js';
import { prefereMenosMovimento } from '../lib/movimento.js';
import { formatarNumero } from '../lib/numero.js';
import { corDoTema } from '../lib/tema.js';
import { Cartao, Esqueleto, Overline } from './ui/index.js';

/** "T 100 · U 85 · L 92" a partir das notas por atributo. */
function notas(attrs) {
  return ATRIBUTOS.map(({ chave, curto }) => {
    const nota = attrs[chave];
    return `${curto} ${nota === null || nota === undefined ? '—' : formatarNumero(nota, 0)}`;
  }).join(' · ');
}

export default function GaugeScore({ relatorio }) {
  const valor = relatorio?.score ?? null;
  const exibido = useContagem(valor);
  const preenchido = valor ?? 0;
  const dados = {
    datasets: [
      {
        data: [preenchido, 100 - preenchido],
        backgroundColor: [corDoTema('papel'), corDoTema('papel', 0.2)],
        borderWidth: 0,
      },
    ],
  };
  const opcoes = {
    cutout: '78%',
    responsive: true,
    maintainAspectRatio: false,
    animation: prefereMenosMovimento() ? false : { duration: 450 },
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
  };

  return (
    <Cartao variante="destaque">
      <Overline icone={Gauge} invertido>
        Score de qualidade
      </Overline>
      {!relatorio ? (
        <Esqueleto className="mx-auto mt-4 size-40 rounded-full" />
      ) : (
        <>
          <div
            className="relative mx-auto mt-4 size-40"
            role="img"
            aria-label={valor === null ? 'Score indisponível' : `Score ${formatarNumero(valor, 0)} de 100`}
          >
            <Doughnut data={dados} options={opcoes} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-titulo tabular-nums">
                {typeof exibido === 'number' ? formatarNumero(exibido, 0) : '—'}
              </span>
              <span className="text-overline uppercase text-papel/80">de 100</span>
            </div>
          </div>
          <p className="mt-3 text-center text-sm text-papel/80">
            {valor === null ? relatorio.message : notas(relatorio.attrs)}
          </p>
        </>
      )}
    </Cartao>
  );
}
