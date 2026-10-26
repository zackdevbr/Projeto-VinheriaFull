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
