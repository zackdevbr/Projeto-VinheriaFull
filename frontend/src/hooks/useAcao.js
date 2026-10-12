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
