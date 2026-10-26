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
 * Menu do topo, só a partir de 768 px (no celular quem navega é a
 * NavInferior). O item ativo fica bordô e sublinhado, como na referência A.
 */
import { NavLink } from 'react-router-dom';
import { MENU } from '../navegacao.js';

function classeDoItem({ isActive }) {
  const cor = isActive ? 'text-bordo underline' : 'text-taupe hover:text-bordo';
  return `flex min-h-11 items-center text-sm decoration-2 underline-offset-8 ${cor}`;
}

export default function MenuTopo() {
  return (
    <nav aria-label="Navegação principal" className="hidden items-center gap-6 md:flex">
      {MENU.map(({ to, rotulo }) => (
        <NavLink key={to} to={to} end={to === '/'} className={classeDoItem}>
          {rotulo}
        </NavLink>
      ))}
    </nav>
  );
}
