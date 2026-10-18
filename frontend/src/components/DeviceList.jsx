/**
 * Lista das vinherias cadastradas (RF02) com o status vindo da frota e o
 * botão de remover. A remoção apaga o cadastro local, o device no IoT Agent
 * e a entidade no Orion; o histórico do STH-Comet é mantido.
 */
import { useState } from 'react';
import { api } from '../api/client.js';
import { STATUS_ROTULO } from '../constants.js';
import { COR_STATUS } from '../estilo.js';
import { useAcao } from '../hooks/useAcao.js';
import { Botao, MensagemErro, Nota } from './ui/index.js';

// Classes das células da tabela (provisório 5A; vira componente de tabela
// em ui.jsx quando a Task 6 precisar de uma segunda tabela)
const CELULA = 'border-b border-gray-200 px-3 py-1.5 text-left';

export default function DeviceList({ devices, statusPorId, onDeleted }) {
  // device_id em remoção, para o texto "Removendo…" sair só na linha certa
  const [removendo, setRemovendo] = useState(null);
  const excluir = useAcao(api.deleteDevice);

  async function remover(device) {
    const confirmado = window.confirm(
      `Remover ${device.name} (${device.device_id})?\n\n` +
        'Serão apagados o cadastro, o device no IoT Agent e a entidade no Orion. ' +
        'O histórico no STH-Comet é mantido.',
    );
    if (!confirmado) {
      return;
    }
    setRemovendo(device.device_id);
    const resultado = await excluir.executar(device.device_id);
    setRemovendo(null);
    if (resultado.ok) {
      await onDeleted(device.device_id);
    }
  }

  if (devices.length === 0) {
    return <Nota>Nenhuma vinheria cadastrada.</Nota>;
  }

  return (
    <>
      <MensagemErro erro={excluir.erro} />
      <table className="border-collapse text-sm">
        <thead>
          <tr className="font-semibold">
            <th className={CELULA}>Id</th>
            <th className={CELULA}>Nome</th>
            <th className={CELULA}>Cidade</th>
            <th className={CELULA}>Status</th>
            <th className={CELULA} aria-label="Ações" />
          </tr>
        </thead>
        <tbody>
          {devices.map((device) => {
            // Recém-cadastrada só entra na frota no próximo ciclo do poller
            const status = statusPorId[device.device_id] ?? 'aguardando';
            return (
              <tr key={device.device_id}>
                <td className={CELULA}>{device.device_id}</td>
                <td className={CELULA}>{device.name}</td>
                <td className={CELULA}>{device.city}</td>
                <td className={`${CELULA} ${COR_STATUS[status]}`}>{STATUS_ROTULO[status]}</td>
                <td className={CELULA}>
                  <Botao
                    onClick={() => remover(device)}
                    disabled={removendo !== null}
                    carregando={removendo === device.device_id}
                    textoCarregando="Removendo…"
                  >
                    Excluir
                  </Botao>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
