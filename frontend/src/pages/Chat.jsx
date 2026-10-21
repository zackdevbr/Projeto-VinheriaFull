/**
 * Página /chat: o assistente ocupando a altura útil da tela. A conversa é a
 * mesma do painel flutuante (ChatContext).
 */
import ChatBox from '../components/ChatBox.jsx';
import { Cartao, Titulo } from '../components/ui/index.js';

export default function Chat() {
  return (
    <div className="flex h-[calc(100dvh-14rem)] min-h-96 flex-col md:h-[calc(100dvh-12rem)]">
      <Titulo overline="Assistente">Chat</Titulo>
      <Cartao className="flex min-h-0 flex-1 flex-col">
        <ChatBox className="flex-1" />
      </Cartao>
    </div>
  );
}
