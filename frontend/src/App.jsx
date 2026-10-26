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
 * Layout e rotas do painel Smart Solutions.
 *
 * Rotas: / Visão geral · /vinherias/:id Detalhe · /alertas · /dispositivos
 * · /chat. O Placeholder fica só para o 404.
 * A troca de página é sempre pelo react-router-dom (NavLink/Link/useNavigate),
 * sem recarregar: os toasts e o polling da frota continuam vivos.
 * Navegação: menu na barra do topo a partir de 768 px (FiwareBar) e barra
 * inferior abaixo disso (NavInferior); os dois leem o mesmo MENU.
 * O ChatFlutuante abre o assistente de qualquer tela, menos de /chat.
 */
import { Route, Routes } from 'react-router-dom';
import AlertBanner from './components/AlertBanner.jsx';
import ChatFlutuante from './components/ChatFlutuante.jsx';
import FiwareBar from './components/FiwareBar.jsx';
import NavInferior from './components/NavInferior.jsx';
import { ChatProvider } from './context/ChatContext.jsx';
import { ConfigProvider } from './context/ConfigContext.jsx';
import { FleetProvider } from './context/FleetContext.jsx';
import Devices from './pages/Devices.jsx';
import Alerts from './pages/Alerts.jsx';
import Chat from './pages/Chat.jsx';
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
              <Route path="/chat" element={<Chat />} />
              <Route path="*" element={<Placeholder titulo="Página não encontrada" />} />
            </Routes>
          </main>
          <ChatFlutuante />
          <NavInferior />
        </ChatProvider>
      </FleetProvider>
    </ConfigProvider>
  );
}
