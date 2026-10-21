/**
 * Cartão de uma ação proposta pelo assistente (bloco B da Task 7A).
 * Mostra o resumo e, enquanto pendente ou com erro, Confirmar e Cancelar.
 * Confirmar executa pelas rotas que o painel já usa (comando manual e
 * faixa ideal); o backend recusa vinheria offline (409) e o erro aparece
 * aqui. O estado fica no ChatContext para sobreviver à troca de tela.
 */
import { api } from '../api/client.js';
import { useChat } from '../context/ChatContext.jsx';
import { podeDecidir, textoFeito } from '../lib/chat.js';
import { Botao, MensagemErro } from './ui/index.js';

/** Executa a ação no backend e devolve o texto de sucesso. */
async function executarAcao(acao) {
  if (acao.kind === 'command') {
    await api.sendCommand(acao.device_id, acao.command);
    return textoFeito(acao, null);
  }
  return textoFeito(acao, await api.saveTriggers(acao.device_id, acao.limits));
}

export default function CartaoAcao({ mensagemId, indice, acao }) {
  const { atualizarAcao } = useChat();
  const executando = acao.estado === 'executando';

  async function confirmar() {
    atualizarAcao(mensagemId, indice, 'executando');
    try {
      atualizarAcao(mensagemId, indice, 'feito', await executarAcao(acao));
    } catch (falha) {
      atualizarAcao(mensagemId, indice, 'erro', falha.message);
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-linha bg-papel p-3 text-vinho">
      <p className="text-sm font-medium">{acao.summary}</p>
      {acao.estado === 'feito' && (
        <p role="status" className="mt-2 text-sm text-ok">
          {acao.detalhe}
        </p>
      )}
      {acao.estado === 'cancelado' && <p className="mt-2 text-sm text-taupe">Cancelado.</p>}
      {acao.estado === 'erro' && (
        <div className="mt-2">
          <MensagemErro erro={acao.detalhe} />
        </div>
      )}
      {(podeDecidir(acao.estado) || executando) && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Botao carregando={executando} textoCarregando="Enviando…" onClick={confirmar}>
            {acao.estado === 'erro' ? 'Tentar de novo' : 'Confirmar'}
          </Botao>
          <Botao
            variante="secundario"
            disabled={executando}
            onClick={() => atualizarAcao(mensagemId, indice, 'cancelado')}
          >
            Cancelar
          </Botao>
        </div>
      )}
    </div>
  );
}
