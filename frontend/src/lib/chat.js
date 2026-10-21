/**
 * Lógica pura do chat (Task 7A): mensagens, histórico enviado ao backend e
 * estados das ações propostas pelo assistente. Sem React e sem fetch, para
 * ser testada com o Vitest.
 *
 * Mensagem: { id, role: 'user'|'model'|'erro', text, falhou?, acoes? }.
 * Ação: o ChatAction do backend + { estado, detalhe }.
 */

// Turnos anteriores mandados com cada pergunta (o backend aceita até 20). Poucos, para
// poupar tokens no plano gratuito do Gemini: três idas e vindas bastam para o contexto
export const MAX_HISTORICO = 6;

// Perguntas prontas mostradas acima do campo
export const SUGESTOES = [
  'Como está a vinheria de São Paulo?',
  'Alguma vinheria em alerta?',
  'Qual vinheria está mais úmida agora?',
  'Desligue o alerta da vinheria 001',
];

let contador = 0;

/** Cria uma mensagem com id único na sessão. */
export function novaMensagem(role, text, extras = {}) {
  contador += 1;
  return { id: `m${Date.now()}-${contador}`, role, text, ...extras };
}

/** Histórico para o backend: só usuário e modelo, sem erros e sem perguntas que falharam. */
export function montarHistorico(mensagens) {
  return mensagens
    .filter((m) => (m.role === 'user' || m.role === 'model') && !m.falhou)
    .slice(-MAX_HISTORICO)
    .map(({ role, text }) => ({ role, text }));
}

/** Marca a pergunta que não teve resposta, para não ir no próximo histórico. */
export function marcarFalha(mensagens, id) {
  return mensagens.map((m) => (m.id === id ? { ...m, falhou: true } : m));
}

/** Ações recebidas do backend, todas aguardando a decisão do usuário. */
export function acoesIniciais(actions = []) {
  return (actions ?? []).map((acao) => ({ ...acao, estado: 'pendente', detalhe: null }));
}

/** Nova lista de mensagens com o estado de uma ação trocado (sem alterar a original). */
export function trocarEstadoAcao(mensagens, mensagemId, indice, estado, detalhe = null) {
  return mensagens.map((m) => {
    if (m.id !== mensagemId) {
      return m;
    }
    const acoes = m.acoes.map((acao, i) => (i === indice ? { ...acao, estado, detalhe } : acao));
    return { ...m, acoes };
  });
}

/** Confirmar e Cancelar só aparecem em pendente e erro (executando bloqueia o clique duplo). */
export function podeDecidir(estado) {
  return estado === 'pendente' || estado === 'erro';
}

/** Texto mostrado depois que a ação deu certo; `resposta` é a do PUT /triggers. */
export function textoFeito(acao, resposta) {
  if (acao.kind !== 'limits') {
    return 'Comando enviado.';
  }
  return resposta?.device_sync === 'enviado'
    ? 'Faixa salva e enviada ao ESP32.'
    : 'Faixa salva; o ESP32 recebe quando voltar.';
}
