/**
 * Hook da contagem animada: quando `valor` muda, devolve números
 * intermediários a cada quadro (requestAnimationFrame) até chegar nele.
 * Na primeira vez conta a partir de 0. Devolve `valor` direto quando ele
 * não é número (null vira "—" na tela) ou quando o sistema pede menos
 * movimento (prefers-reduced-motion).
 */
import { useEffect, useRef, useState } from 'react';
import { interpolar } from '../lib/contagem.js';
import { prefereMenosMovimento } from '../lib/movimento.js';

export function useContagem(valor, duracaoMs = 450) {
  const numerico = typeof valor === 'number' && Number.isFinite(valor);
  const [exibido, setExibido] = useState(numerico ? 0 : valor);
  // Último número mostrado: a próxima animação parte dele
  const ultimo = useRef(0);

  useEffect(() => {
    if (!numerico || prefereMenosMovimento()) {
      setExibido(valor);
      if (numerico) {
        ultimo.current = valor;
      }
      return undefined;
    }
    const de = ultimo.current;
    const inicio = performance.now();
    let quadro;
    function passo(agora) {
      const progresso = (agora - inicio) / duracaoMs;
      const atual = interpolar(de, valor, progresso);
      ultimo.current = atual;
      setExibido(atual);
      if (progresso < 1) {
        quadro = requestAnimationFrame(passo);
      }
    }
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, [valor, numerico, duracaoMs]);

  return exibido;
}
