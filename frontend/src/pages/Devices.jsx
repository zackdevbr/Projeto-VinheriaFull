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
 * Página /dispositivos: cadastro e lista das vinherias. Depois de cadastrar
 * ou remover, recarrega a lista e pede uma leitura imediata da frota para
 * o status aparecer sem esperar o próximo ciclo do polling.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import DeviceForm from '../components/DeviceForm.jsx';
import DeviceList from '../components/DeviceList.jsx';
import { Cartao, Esqueleto, GradeBento, MensagemErro, Nota, Subtitulo, Titulo } from '../components/ui/index.js';
import { useFleet } from '../context/FleetContext.jsx';
import { useAcao } from '../hooks/useAcao.js';

export default function Devices() {
  const { fleet, atualizar } = useFleet();
  // null = lista ainda não carregada (mostra "Carregando…")
  const [devices, setDevices] = useState(null);
  const listar = useAcao(api.listDevices);
  const executarListar = listar.executar;

  const carregar = useCallback(async () => {
    const resultado = await executarListar();
    if (resultado.ok) {
      setDevices(resultado.valor);
    }
  }, [executarListar]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // device_id -> status, a partir do último retrato da frota
  const statusPorId = useMemo(
    () => Object.fromEntries((fleet?.vinherias ?? []).map((v) => [v.device_id, v.status])),
    [fleet],
  );

  const aposMudanca = useCallback(async () => {
    await carregar();
    atualizar();
  }, [carregar, atualizar]);

  return (
    <section>
      <Titulo overline="Cadastro">Dispositivos</Titulo>
      <GradeBento>
        <Cartao className="md:col-span-2 lg:col-span-1">
          <Subtitulo>Nova vinheria</Subtitulo>
          <DeviceForm onCreated={aposMudanca} />
        </Cartao>
        <Cartao larg={3}>
          <Subtitulo>Vinherias</Subtitulo>
          <MensagemErro erro={listar.erro} />
          {devices === null ? (
            listar.erro ? (
              <Nota>Não foi possível carregar a lista.</Nota>
            ) : (
              <div className="flex flex-col gap-3">
                <Esqueleto className="h-16" />
                <Esqueleto className="h-16" />
                <Esqueleto className="h-16" />
              </div>
            )
          ) : (
            <DeviceList devices={devices} statusPorId={statusPorId} onDeleted={aposMudanca} />
          )}
        </Cartao>
      </GradeBento>
    </section>
  );
}
