/**
 * Cartão de uma vinheria na Visão geral (RF12): faixa de rótulo bordô com o
 * nome e o status (como o rótulo do produto na referência A), cidade, valores
 * atuais, score e tempo desde a última leitura. O cartão inteiro leva ao
 * detalhe. Atributo com alerta aberto aparece em vermelho, com ícone.
 */
import { TriangleAlert } from 'lucide-react';
import { ATRIBUTOS } from '../lib/atributos.js';
import { textoVisto } from '../lib/frota.js';
import { formatarNumero } from '../lib/numero.js';
import { caminhoVinheria } from '../lib/rotas.js';
import { Cartao, SeloStatus } from './ui/index.js';

export default function VinheriaCard({ vinheria }) {
  const emAlerta = new Set(vinheria.active_alerts.map((alerta) => alerta.attr));
  return (
    <Cartao larg={2} para={caminhoVinheria(vinheria.device_id)}>
      <div className="-mx-4 -mt-4 flex items-center justify-between gap-3 bg-bordo px-4 py-3 md:-mx-6 md:-mt-6 md:px-6">
        <span className="min-w-0 truncate font-display text-xl text-papel">{vinheria.name}</span>
        <span className="shrink-0 rounded-full bg-papel">
          <SeloStatus status={vinheria.status} />
        </span>
      </div>
      <p className="mt-3 text-sm text-taupe">{vinheria.city}</p>
      <dl className="mt-4 grid grid-cols-3 gap-2">
        {ATRIBUTOS.map(({ chave, abreviado, unidade }) => {
          const valor = vinheria.current[chave];
          const semValor = valor === null || valor === undefined;
          const alerta = emAlerta.has(chave);
          return (
            <div key={chave} className="min-w-0">
              <dt className="text-overline uppercase text-taupe">{abreviado}</dt>
              <dd className={`mt-1 flex items-baseline gap-1 font-display text-2xl tabular-nums ${alerta ? 'text-alerta' : 'text-vinho'}`}>
                {alerta && <TriangleAlert size={16} strokeWidth={1.75} className="self-center" aria-label="fora da faixa" />}
                {semValor ? '—' : formatarNumero(valor)}
                {!semValor && <span className="font-sans text-sm">{unidade}</span>}
              </dd>
            </div>
          );
        })}
      </dl>
      <p className="mt-4 flex justify-between gap-3 border-t border-linha pt-3 text-sm text-taupe">
        <span>Score {vinheria.score === null || vinheria.score === undefined ? '—' : formatarNumero(vinheria.score, 0)}</span>
        <span>{textoVisto(vinheria)}</span>
      </p>
    </Cartao>
  );
}
