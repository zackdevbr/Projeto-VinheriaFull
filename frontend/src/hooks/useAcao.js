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
 * Hook para ações assíncronas disparadas pelo usuário (salvar, cadastrar,
 * remover, carregar). Controla o "executando" e guarda a mensagem do
 * ApiError, para nenhuma tela repetir o mesmo try/catch/finally.
 *
 * executar(...args) nunca lança: devolve { ok: true, valor } ou { ok: false }.
 * setErro permite mostrar um erro de validação feito antes da chamada.
 */
import { useCallback, useState } from 'react';

export function useAcao(acao) {
  const [executando, setExecutando] = useState(false);
  const [erro, setErro] = useState(null);

  const executar = useCallback(async (...args) => {
    setExecutando(true);
    setErro(null);
    try {
      return { ok: true, valor: await acao(...args) };
    } catch (falha) {
      setErro(falha.message);
      return { ok: false };
    } finally {
      setExecutando(false);
    }
  }, [acao]);

  return { executar, executando, erro, setErro };
}
