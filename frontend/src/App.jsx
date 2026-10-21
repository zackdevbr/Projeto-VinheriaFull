/**
 * Layout e rotas do painel Smart Solutions.
 *
 * Rotas: / Visão geral · /vinherias/:id Detalhe · /alertas · /dispositivos
 * · /chat. Só o /chat (Task 7A) ainda é Placeholder.
 * A troca de página é sempre pelo react-router-dom (NavLink/Link/useNavigate),
 * sem recarregar: os toasts e o polling da frota continuam vivos.
 * Navegação: menu na barra do topo a partir de 768 px (FiwareBar) e barra
 * inferior abaixo disso (NavInferior); os dois leem o mesmo MENU.
 */
import { Route, Routes } from 'react-router-dom';
import AlertBanner from './components/AlertBanner.jsx';
import FiwareBar from './components/FiwareBar.jsx';
import NavInferior from './components/NavInferior.jsx';
import { ChatProvider } from './context/ChatContext.jsx';
import { ConfigProvider } from './context/ConfigContext.jsx';
import { FleetProvider } from './context/FleetContext.jsx';
import Devices from './pages/Devices.jsx';
import Alerts from './pages/Alerts.jsx';
import Overview from './pages/Overview.jsx';
import Placeholder from './pages/Placeholder.jsx';
import VinheriaDetail from './pages/VinheriaDetail.jsx';

export default function App() {
  return (
    <ConfigProvider>
      <FleetProvider>
        <ChatProvider>
          <FiwareBar />
          <AlertBanner />
          <main className="mx-auto w-full max-w-pagina px-4 pt-6 pb-28 md:px-6 md:pt-10 md:pb-16">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/vinherias/:id" element={<VinheriaDetail />} />
              <Route path="/alertas" element={<Alerts />} />
              <Route path="/dispositivos" element={<Devices />} />
              <Route path="/chat" element={<Placeholder titulo="Chat" task="Task 7A" />} />
              <Route path="*" element={<Placeholder titulo="Página não encontrada" />} />
            </Routes>
          </main>
          <NavInferior />
        </ChatProvider>
      </FleetProvider>
    </ConfigProvider>
  );
}
