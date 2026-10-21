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
 *
 * O estado guarda de qual `carregar` ele veio (`origem`). Quando `carregar`
 * muda, o estado antigo é ignorado já no mesmo render, em vez de aparecer
 * por um quadro (dados da janela ou da vinheria anterior).
 */
import { useCallback, useEffect, useState } from 'react';

const INICIAL = { dados: null, erro: null, falha: null, carregando: true };

export function useLeitura(carregar, intervaloMs = null) {
  const [estado, setEstado] = useState({ ...INICIAL, origem: carregar });
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    if (!carregar) {
      setEstado({ origem: carregar, dados: null, erro: null, falha: null, carregando: false });
      return undefined;
    }
    let ativo = true;
    let timer = null;
    async function ciclo() {
      try {
        const dados = await carregar();
        if (ativo) {
          setEstado({ origem: carregar, dados, erro: null, falha: null, carregando: false });
        }
      } catch (falha) {
        if (ativo) {
          // Mantém os dados da leitura anterior só se forem desta mesma leitura
          setEstado((atual) => ({
            origem: carregar,
            dados: atual.origem === carregar ? atual.dados : null,
            erro: falha.message,
            falha,
            carregando: false,
          }));
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
  const vigente = estado.origem === carregar ? estado : INICIAL;
  return {
    dados: vigente.dados,
    erro: vigente.erro,
    falha: vigente.falha,
    carregando: vigente.carregando,
    recarregar,
  };
}
