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
 * Barra de navegação inferior do celular (abaixo de 768 px): quatro ícones
 * com rótulo ao alcance do polegar. O item Alertas mostra quantas vinherias
 * pedem atenção, contadas do FleetContext (sem chamada HTTP nova).
 */
import { NavLink } from 'react-router-dom';
import { useFleet } from '../context/FleetContext.jsx';
import { contarAtencao } from '../lib/fleetEvents.js';
import { MENU } from '../navegacao.js';

function classeDoItem({ isActive }) {
  const cor = isActive ? 'border-bordo text-bordo' : 'border-transparent text-taupe';
  return `relative flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 border-t-2 text-xs font-medium ${cor}`;
}

export default function NavInferior() {
  const { fleet } = useFleet();
  const atencao = contarAtencao(fleet);

  return (
    <nav
      aria-label="Navegação principal"
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-linha bg-papel pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      {MENU.map(({ to, rotulo, icone: Icone, contaAtencao }) => (
        <NavLink key={to} to={to} end={to === '/'} className={classeDoItem}>
          <Icone size={22} strokeWidth={1.5} aria-hidden="true" />
          {rotulo}
          {contaAtencao && atencao > 0 && (
            <span className="absolute top-1.5 left-1/2 ml-2 min-w-5 rounded-full bg-alerta px-1 text-center leading-5 text-papel">
              {atencao}
              <span className="sr-only"> vinherias precisam de atenção</span>
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
