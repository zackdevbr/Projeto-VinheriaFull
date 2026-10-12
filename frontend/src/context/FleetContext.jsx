/**
 * Contexto da frota: lê GET /api/fleet a cada 5 s, guarda o retrato
 * anterior e transforma as mudanças de status em toasts (RF14).
 *
 * Expõe o retrato atual (`fleet`), o erro da última leitura, a pilha de
 * toasts, fecharToast(id) e atualizar() para pedir uma leitura na hora.
 */
import { useCallback, useMemo, useRef, useState } from 'react';
import { api } from '../api/client.js';
import { FLEET_POLL_MS } from '../constants.js';
import { usePolling } from '../hooks/usePolling.js';
import { diffFleet, empilharToasts } from '../lib/fleetEvents.js';
import { criarContexto } from './criarContexto.js';

const [Provedor, useFleet] = criarContexto('Fleet');
export { useFleet };

export function FleetProvider({ children }) {
  const [fleet, setFleet] = useState(null);
  const [error, setError] = useState(null);
  const [toasts, setToasts] = useState([]);
  // Retrato anterior para comparar; ref porque não precisa redesenhar a tela
  const anterior = useRef(null);

  /** Uma leitura da frota: atualiza o retrato e empilha os eventos novos. */
  const atualizar = useCallback(async () => {
    try {
      const atual = await api.getFleet();
      const eventos = diffFleet(anterior.current, atual);
      anterior.current = atual;
      setFleet(atual);
      setError(null);
      if (eventos.length > 0) {
        setToasts((atuais) => empilharToasts(atuais, eventos));
      }
    } catch (erro) {
      setError(erro.message);
    }
  }, []);

  usePolling(atualizar, FLEET_POLL_MS);

  const fecharToast = useCallback((id) => {
    setToasts((atuais) => atuais.filter((toast) => toast.id !== id));
  }, []);

  const valor = useMemo(
    () => ({ fleet, error, toasts, fecharToast, atualizar }),
    [fleet, error, toasts, fecharToast, atualizar],
  );
  return <Provedor value={valor}>{children}</Provedor>;
}
