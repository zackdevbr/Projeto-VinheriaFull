/**
 * Peças de painel no estilo bento (referência B, nas cores da referência A):
 * grade, cartão, cartão de indicador (KPI) e selo de status de vinheria.
 * A Task 6 monta a Visão geral e o detalhe só com estas peças.
 */
import { STATUS_ROTULO } from '../../constants.js';
import { COR_STATUS, ICONE_STATUS } from '../../estilo.js';
import { useContagem } from '../../hooks/useContagem.js';
import { statusConhecido } from '../../lib/status.js';
import { Overline } from './base.jsx';

// Quantas colunas o item ocupa: 2 no md e até 4 no lg (classes inteiras para o Tailwind achar)
const LARGURA = {
  1: '',
  2: 'md:col-span-2',
  3: 'md:col-span-2 lg:col-span-3',
  4: 'md:col-span-2 lg:col-span-4',
};

/** Grade bento: 1 coluna no celular, 2 no md, 4 no lg. Os filhos se entregam em cascata. */
export function GradeBento({ children }) {
  return <div className="cascata grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 lg:grid-cols-4">{children}</div>;
}

/** Cartão do bento. `destaque` = fundo bordô sólido (o cartão vermelho da referência B). */
export function Cartao({ variante = 'padrao', larg = 1, className = '', children }) {
  const cores = variante === 'destaque' ? 'border-bordo bg-bordo text-papel' : 'border-linha bg-papel';
  return (
    <section className={`min-w-0 animate-entrar rounded-2xl border p-4 shadow-baixa md:p-6 ${cores} ${LARGURA[larg]} ${className}`}>
      {children}
    </section>
  );
}

/** Formata o número com as casas do valor final (inteiro fica inteiro, decimal com 1 casa). */
function formatar(numero, valorFinal) {
  const casas = Number.isInteger(valorFinal) ? 0 : 1;
  return numero.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

/** Cartão de indicador: rótulo com ícone, número grande em serifa que conta até o valor, unidade e rodapé. */
export function CartaoKpi({ rotulo, icone, valor, unidade, rodape, variante = 'padrao', larg = 1 }) {
  const exibido = useContagem(valor);
  const invertido = variante === 'destaque';
  const temNumero = typeof exibido === 'number';
  return (
    <Cartao variante={variante} larg={larg}>
      <Overline icone={icone} invertido={invertido}>{rotulo}</Overline>
      <p className="mt-3 font-display text-titulo tabular-nums">
        {temNumero ? formatar(exibido, valor) : '—'}
        {temNumero && unidade && <span className="ml-1 font-sans text-base">{unidade}</span>}
      </p>
      {rodape && <p className={`mt-2 text-sm ${invertido ? 'text-papel/80' : 'text-taupe'}`}>{rodape}</p>}
    </Cartao>
  );
}

/** Selo de status de uma vinheria: ícone + texto + cor. Em alerta, o ícone pulsa. */
export function SeloStatus({ status }) {
  const chave = statusConhecido(status);
  const Icone = ICONE_STATUS[chave];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${COR_STATUS[chave]}`}>
      <Icone size={14} strokeWidth={1.75} aria-hidden="true" className={chave === 'alerta' ? 'animate-pulsar' : ''} />
      {STATUS_ROTULO[chave]}
    </span>
  );
}
