/**
 * Peças de painel no estilo bento (referência B, nas cores da referência A):
 * grade, cartão, cartão de indicador (KPI) e selo de status de vinheria.
 * A Task 6 monta a Visão geral e o detalhe só com estas peças.
 */
import { TriangleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { STATUS_ROTULO } from '../../constants.js';
import { COR_STATUS, ICONE_STATUS } from '../../estilo.js';
import { useContagem } from '../../hooks/useContagem.js';
import { formatarNumero } from '../../lib/numero.js';
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

/**
 * Cartão do bento. `destaque` = fundo bordô sólido (o cartão vermelho da
 * referência B). Com `para`, o cartão inteiro vira link (React Router) e
 * sobe 2 px no hover.
 */
export function Cartao({ variante = 'padrao', larg = 1, para, className = '', children }) {
  const cores = variante === 'destaque' ? 'border-bordo bg-bordo text-papel' : 'border-linha bg-papel';
  // O recorte (overflow-hidden) é só do cartão-link, para a faixa bordô de dentro seguir o canto arredondado
  const interativo = para ? 'block overflow-hidden transition duration-150 hover:-translate-y-0.5 hover:shadow-media' : '';
  const classes = `min-w-0 animate-entrar rounded-2xl border p-4 shadow-baixa md:p-6 ${cores} ${interativo} ${LARGURA[larg]} ${className}`;
  if (para) {
    return (
      <Link to={para} className={classes}>
        {children}
      </Link>
    );
  }
  return <section className={classes}>{children}</section>;
}

/**
 * Cartão de indicador: rótulo com ícone, número grande em serifa que conta
 * até o valor, unidade e rodapé. `rodapeAlerta` pinta o rodapé de vermelho
 * com ícone (ex.: valor fora da faixa).
 */
export function CartaoKpi({ rotulo, icone, valor, unidade, rodape, rodapeAlerta = false, variante = 'padrao', larg = 1 }) {
  const exibido = useContagem(valor);
  const invertido = variante === 'destaque';
  const temNumero = typeof exibido === 'number';
  const corRodape = rodapeAlerta ? 'text-alerta' : invertido ? 'text-papel/80' : 'text-taupe';
  return (
    <Cartao variante={variante} larg={larg}>
      <Overline icone={icone} invertido={invertido}>{rotulo}</Overline>
      <p className="mt-3 font-display text-titulo tabular-nums">
        {temNumero ? formatarNumero(exibido, Number.isInteger(valor) ? 0 : 1) : '—'}
        {temNumero && unidade && <span className="ml-1 font-sans text-base">{unidade}</span>}
      </p>
      {rodape && (
        <p className={`mt-2 flex items-center gap-1 text-sm ${corRodape}`}>
          {rodapeAlerta && <TriangleAlert size={14} strokeWidth={1.75} aria-hidden="true" />}
          {rodape}
        </p>
      )}
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
