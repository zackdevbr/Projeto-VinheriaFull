/**
 * Chat flutuante: botão redondo no canto inferior esquerdo (o direito é dos
 * toasts) que abre o assistente sem sair da tela atual. No desktop vira um
 * painel de 400 px no mesmo canto; no celular ocupa a tela toda. Fecha com
 * Esc ou com o X. Não aparece em /chat, onde a página já é o chat.
 */
import { MessageCircle, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import ChatBox from './ChatBox.jsx';
import { BotaoIcone, Subtitulo } from './ui/index.js';

export default function ChatFlutuante() {
  const { pathname } = useLocation();
  const [aberto, setAberto] = useState(false);

  useEffect(() => {
    if (!aberto) {
      return undefined;
    }
    function aoTeclar(evento) {
      if (evento.key === 'Escape') {
        setAberto(false);
      }
    }
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  }, [aberto]);

  if (pathname === '/chat') {
    return null;
  }

  if (!aberto) {
    return (
      <button
        type="button"
        aria-label="Abrir o chat com o assistente"
        title="Assistente"
        onClick={() => setAberto(true)}
        className="fixed bottom-20 left-4 z-30 inline-flex size-14 items-center justify-center rounded-full bg-bordo text-papel shadow-media transition-colors duration-150 hover:bg-vinho md:bottom-6 md:left-6"
      >
        <MessageCircle size={24} strokeWidth={1.5} aria-hidden="true" />
      </button>
    );
  }

  return (
    <div
      role="dialog"
      aria-label="Chat com o assistente"
      className="fixed inset-0 z-50 flex animate-entrar flex-col bg-papel p-4 md:inset-auto md:bottom-6 md:left-6 md:h-[min(40rem,calc(100dvh-3rem))] md:w-100 md:rounded-2xl md:border md:border-linha md:shadow-media"
    >
      <div className="flex items-center justify-between">
        <Subtitulo>Assistente</Subtitulo>
        <BotaoIcone icone={X} rotulo="Fechar o chat" className="-mt-4" onClick={() => setAberto(false)} />
      </div>
      <ChatBox className="min-h-0 flex-1" />
    </div>
  );
}
