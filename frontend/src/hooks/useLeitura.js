/**
 * Hook de leitura de dados do backend com estado pronto para a tela:
 * { dados, erro, falha, carregando, recarregar }. `erro` é a mensagem pronta
 * para a tela e `falha` o ApiError original (status e service).
 *
 * Com `intervaloMs`, relê em cadeia de setTimeout depois que cada leitura
 * termina (como o usePolling, sem acumular requisições). Com null, lê uma
 * vez sempre que `carregar` muda. `carregar` null não lê nada. Quem chama
 * passa `carregar` de um useCallback: cada função nova recomeça a leitura
 * do zero (ex.: troca da janela do gráfico).
 */
import { useCallback, useEffect, useRef, useState } from 'react';

const INICIAL = { dados: null, erro: null, falha: null, carregando: true };

export function useLeitura(carregar, intervaloMs = null) {
  const [estado, setEstado] = useState(INICIAL);
  const [versao, setVersao] = useState(0);
  // Para saber se a mudança foi de `carregar` (limpa a tela) ou só um recarregar
  const ultimaCarga = useRef(carregar);

  useEffect(() => {
    if (ultimaCarga.current !== carregar) {
      ultimaCarga.current = carregar;
      setEstado(INICIAL);
    }
    if (!carregar) {
      setEstado({ dados: null, erro: null, falha: null, carregando: false });
      return undefined;
    }
    let ativo = true;
    let timer = null;
    async function ciclo() {
      try {
        const dados = await carregar();
        if (ativo) {
          setEstado({ dados, erro: null, falha: null, carregando: false });
        }
      } catch (falha) {
        if (ativo) {
          setEstado((atual) => ({ dados: atual.dados, erro: falha.message, falha, carregando: false }));
        }
      } finally {
        if (ativo && intervaloMs) {
          timer = setTimeout(ciclo, intervaloMs);
        }
      }
    }
    ciclo();
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [carregar, intervaloMs, versao]);

  const recarregar = useCallback(() => setVersao((atual) => atual + 1), []);
  return { ...estado, recarregar };
}
