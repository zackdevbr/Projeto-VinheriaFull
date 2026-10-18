/**
 * Página /dispositivos: cadastro e lista das vinherias. Depois de cadastrar
 * ou remover, recarrega a lista e pede uma leitura imediata da frota para
 * o status aparecer sem esperar o próximo ciclo do polling.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import DeviceForm from '../components/DeviceForm.jsx';
import DeviceList from '../components/DeviceList.jsx';
import { MensagemErro, Nota, Titulo } from '../components/ui/index.js';
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
      <Titulo>Dispositivos</Titulo>
      <DeviceForm onCreated={aposMudanca} />
      <MensagemErro erro={listar.erro} />
      {devices === null ? (
        <Nota>{listar.erro ? 'Não foi possível carregar a lista.' : 'Carregando…'}</Nota>
      ) : (
        <DeviceList devices={devices} statusPorId={statusPorId} onDeleted={aposMudanca} />
      )}
    </section>
  );
}
