/**
 * Uma mensagem da conversa: bolha do usuário à direita (bordô), do
 * assistente à esquerda (papel) e erro do sistema com o ícone de alerta.
 * O texto do assistente vem sem markdown; as quebras de linha são mantidas.
 */
import { MensagemErro } from './ui/index.js';

export default function ChatMensagem({ mensagem }) {
  if (mensagem.role === 'erro') {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl border border-alerta/30 bg-alerta/10 px-4 pt-3 pb-1">
          <MensagemErro erro={mensagem.text} />
        </div>
      </div>
    );
  }
  const doUsuario = mensagem.role === 'user';
  return (
    <div className={`flex ${doUsuario ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${doUsuario ? 'bg-bordo text-papel' : 'border border-linha bg-papel text-vinho'}`}
      >
        <p className="break-words whitespace-pre-wrap">{mensagem.text}</p>
      </div>
    </div>
  );
}
