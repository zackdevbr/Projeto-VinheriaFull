/**
 * Layout e rotas do painel Smart Solutions.
 *
 * Rotas: / Visão geral · /vinherias/:id Detalhe · /alertas · /dispositivos
 * · /chat. As telas das Tasks 6 e 7A ainda são Placeholder.
 * A troca de página é sempre pelo react-router-dom (NavLink/Link/useNavigate),
 * sem recarregar: os toasts e o polling da frota continuam vivos.
 */
import { NavLink, Route, Routes } from 'react-router-dom';
import FiwareBar from './components/FiwareBar.jsx';
import { ConfigProvider } from './context/ConfigContext.jsx';
import Placeholder from './pages/Placeholder.jsx';

const MENU = [
  { to: '/', rotulo: 'Visão geral' },
  { to: '/dispositivos', rotulo: 'Dispositivos' },
  { to: '/alertas', rotulo: 'Alertas' },
  { to: '/chat', rotulo: 'Chat' },
];

/** Classes do item do menu; o NavLink informa se a rota está ativa. */
function classeDoMenu({ isActive }) {
  return isActive ? 'font-semibold underline' : 'text-gray-700 hover:underline';
}

export default function App() {
  return (
    <ConfigProvider>
      <FiwareBar />
      <nav className="flex gap-4 border-b border-gray-200 px-4 py-2 text-sm">
        {MENU.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'} className={classeDoMenu}>
            {item.rotulo}
          </NavLink>
        ))}
      </nav>
      <main className="p-4">
        <Routes>
          <Route path="/" element={<Placeholder titulo="Visão geral" task="Task 6" />} />
          <Route path="/vinherias/:id" element={<Placeholder titulo="Detalhe da vinheria" task="Task 6" />} />
          <Route path="/alertas" element={<Placeholder titulo="Alertas" task="Task 6" />} />
          <Route path="/dispositivos" element={<Placeholder titulo="Dispositivos" task="subtarefa 5A.8" />} />
          <Route path="/chat" element={<Placeholder titulo="Chat" task="Task 7A" />} />
          <Route path="*" element={<Placeholder titulo="Página não encontrada" />} />
        </Routes>
      </main>
    </ConfigProvider>
  );
}
