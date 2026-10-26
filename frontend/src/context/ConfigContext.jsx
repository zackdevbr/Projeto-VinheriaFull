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
 * Contexto da configuração do backend e da saúde do FIWARE.
 *
 * A cada 30 s lê GET /api/config e GET /api/config/health. Expõe o IP em
 * uso, o resultado do health e salvarIp(), que troca o IP do FIWARE em
 * runtime (PUT /api/config) e revalida a saúde na hora.
 */
import { useCallback, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { HEALTH_POLL_MS } from '../constants.js';
import { usePolling } from '../hooks/usePolling.js';
import { criarContexto } from './criarContexto.js';

const [Provedor, useConfig] = criarContexto('Config');
export { useConfig };

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [health, setHealth] = useState(null);
  // verificando | online | offline | sem_backend
  const [healthState, setHealthState] = useState('verificando');

  /** Recarrega config e saúde; o config também, para aparecer se o backend voltou. */
  const verificarSaude = useCallback(async () => {
    try {
      const [novoConfig, novoHealth] = await Promise.all([api.getConfig(), api.getHealth()]);
      setConfig(novoConfig);
      setHealth(novoHealth);
      setHealthState(novoHealth.ok ? 'online' : 'offline');
    } catch {
      setHealth(null);
      setHealthState('sem_backend');
    }
  }, []);

  usePolling(verificarSaude, HEALTH_POLL_MS);

  /** Grava o novo IP do FIWARE; erros sobem para o formulário mostrar. */
  const salvarIp = useCallback(async (ip) => {
    const novo = await api.saveConfig({ ec2_ip: ip });
    setConfig(novo);
    setHealthState('verificando');
    await verificarSaude();
    return novo;
  }, [verificarSaude]);

  const valor = useMemo(
    () => ({ config, health, healthState, salvarIp, verificarSaude }),
    [config, health, healthState, salvarIp, verificarSaude],
  );
  return <Provedor value={valor}>{children}</Provedor>;
}
