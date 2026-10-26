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
 * Contexto do chat (Task 7A): a conversa vive aqui, acima das rotas, para a
 * página /chat e o painel flutuante mostrarem a mesma conversa e ela
 * sobreviver à troca de página. Recarregar o navegador zera a conversa.
 *
 * enviar(texto) manda a pergunta com o histórico; em falha, acrescenta uma
 * mensagem de erro e devolve o texto para o campo. atualizarAcao troca o
 * estado de um cartão de ação (bloco B).
 */
import { useCallback, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { acoesIniciais, marcarFalha, montarHistorico, novaMensagem, trocarEstadoAcao } from '../lib/chat.js';
import { criarContexto } from './criarContexto.js';

const [Provedor, useChat] = criarContexto('Chat');
export { useChat };

export function ChatProvider({ children }) {
  const [mensagens, setMensagens] = useState([]);
  const [enviando, setEnviando] = useState(false);

  const enviar = useCallback(async (texto) => {
    const limpo = texto.trim();
    if (!limpo || enviando) {
      return { ok: false, texto };
    }
    const historico = montarHistorico(mensagens);
    const pergunta = novaMensagem('user', limpo);
    setMensagens((atuais) => [...atuais, pergunta]);
    setEnviando(true);
    try {
      const resposta = await api.sendChat(limpo, historico);
      const doBot = novaMensagem('model', resposta.reply, { acoes: acoesIniciais(resposta.actions) });
      setMensagens((atuais) => [...atuais, doBot]);
      return { ok: true };
    } catch (falha) {
      setMensagens((atuais) => [...marcarFalha(atuais, pergunta.id), novaMensagem('erro', falha.message)]);
      return { ok: false, texto: limpo };
    } finally {
      setEnviando(false);
    }
  }, [mensagens, enviando]);

  const atualizarAcao = useCallback((mensagemId, indice, estado, detalhe = null) => {
    setMensagens((atuais) => trocarEstadoAcao(atuais, mensagemId, indice, estado, detalhe));
  }, []);

  const valor = useMemo(
    () => ({ mensagens, enviando, enviar, atualizarAcao }),
    [mensagens, enviando, enviar, atualizarAcao],
  );
  return <Provedor value={valor}>{children}</Provedor>;
}
