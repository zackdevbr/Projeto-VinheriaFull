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
 * Caixa de conversa usada pela página /chat e pelo painel flutuante:
 * mensagens com rolagem automática, sugestões de pergunta (numa linha com
 * rolagem horizontal, para sobrar altura à conversa) e o campo de texto
 * (Enter envia, Shift+Enter quebra a linha). Se o envio falha, o texto
 * volta para o campo.
 */
import { SendHorizontal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useChat } from '../context/ChatContext.jsx';
import { SUGESTOES } from '../lib/chat.js';
import ChatMensagem from './ChatMensagem.jsx';
import { AreaTexto, Botao, EstadoVazio } from './ui/index.js';

export default function ChatBox({ className = '' }) {
  const { mensagens, enviando, enviar } = useChat();
  const [texto, setTexto] = useState('');
  const fim = useRef(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: 'end' });
  }, [mensagens, enviando]);

  async function mandar(conteudo) {
    if (!conteudo.trim() || enviando) {
      return;
    }
    setTexto('');
    const resultado = await enviar(conteudo);
    if (!resultado.ok && resultado.texto) {
      setTexto(resultado.texto);
    }
  }

  function aoTeclar(evento) {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault();
      mandar(texto);
    }
  }

  return (
    <div className={`flex min-h-0 flex-col ${className}`}>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pb-3" aria-live="polite">
        {mensagens.length === 0 ? (
          <EstadoVazio
            titulo="Pergunte sobre as vinherias"
            texto="O assistente responde com os dados reais do FIWARE. Experimente uma das sugestões abaixo."
          />
        ) : (
          mensagens.map((mensagem) => <ChatMensagem key={mensagem.id} mensagem={mensagem} />)
        )}
        {enviando && (
          <p role="status" className="text-sm text-taupe">
            Pensando…
          </p>
        )}
        <div ref={fim} />
      </div>
      <div className="flex gap-2 overflow-x-auto pb-3">
        {SUGESTOES.map((sugestao) => (
          <Botao
            key={sugestao}
            variante="secundario"
            className="shrink-0 whitespace-nowrap"
            disabled={enviando}
            onClick={() => mandar(sugestao)}
          >
            {sugestao}
          </Botao>
        ))}
      </div>
      <form
        className="flex items-end gap-2"
        onSubmit={(evento) => {
          evento.preventDefault();
          mandar(texto);
        }}
      >
        <AreaTexto
          rotulo="Mensagem para o assistente"
          rotuloOculto
          rows={2}
          maxLength={1000}
          placeholder="Pergunte sobre uma vinheria…"
          value={texto}
          disabled={enviando}
          onChange={(evento) => setTexto(evento.target.value)}
          onKeyDown={aoTeclar}
        />
        <Botao type="submit" disabled={!texto.trim()} carregando={enviando} textoCarregando="Enviando…">
          <SendHorizontal size={18} strokeWidth={1.5} aria-hidden="true" />
          Enviar
        </Botao>
      </form>
    </div>
  );
}
