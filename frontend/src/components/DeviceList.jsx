/**
 * Lista das vinherias cadastradas (RF02) com o status vindo da frota e o
 * botão de remover. A remoção apaga o cadastro local, o device no IoT Agent
 * e a entidade no Orion; o histórico do STH-Comet é mantido.
 *
 * Uma única marcação para todos os tamanhos: no celular cada vinheria é um
 * cartão empilhado; a partir de 768 px as mesmas linhas alinham em colunas
 * (CSS grid) sob um cabeçalho.
 */
import { useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { statusConhecido } from '../lib/status.js';
import { Botao, EstadoVazio, MensagemErro, SeloStatus } from './ui/index.js';

// Colunas a partir de md, iguais no cabeçalho e nas linhas: Id · Nome · Cidade · Status · ação
const COLUNAS = 'md:grid md:grid-cols-[8.5rem_minmax(0,1fr)_minmax(0,1fr)_10rem_7.5rem] md:items-center md:gap-4';

const CABECALHO = ['Id', 'Nome', 'Cidade', 'Status', ''];

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
    return <EstadoVazio titulo="Nenhuma vinheria cadastrada" texto="Cadastre a primeira no formulário." />;
  }

  return (
    <>
      <MensagemErro erro={excluir.erro} />
      <div className={`hidden border-b border-linha pb-2 ${COLUNAS}`} aria-hidden="true">
        {CABECALHO.map((rotulo) => (
          <span key={rotulo || 'acao'} className="text-overline uppercase text-taupe">
            {rotulo}
          </span>
        ))}
      </div>
      <ul className="flex flex-col gap-3 md:gap-0">
        {devices.map((device) => {
          // Recém-cadastrada só entra na frota no próximo ciclo do poller
          const status = statusConhecido(statusPorId[device.device_id] ?? 'aguardando');
          return (
            <li
              key={device.device_id}
              className={`flex min-w-0 flex-col gap-2 rounded-xl border border-linha p-4 md:rounded-none md:border-0 md:border-b md:px-0 md:py-3 ${COLUNAS}`}
            >
              <span className="order-1 font-mono text-xs text-taupe md:order-none">{device.device_id}</span>
              <span className="font-display text-lg break-words text-vinho">{device.name}</span>
              <span className="text-sm break-words text-taupe">{device.city}</span>
              <span className="order-2 md:order-none">
                <SeloStatus status={status} />
              </span>
              <Botao
                variante="perigo"
                className="order-3 self-start md:order-none md:w-full md:self-auto"
                onClick={() => remover(device)}
                disabled={removendo !== null}
                carregando={removendo === device.device_id}
                textoCarregando="Removendo…"
              >
                Excluir
              </Botao>
            </li>
          );
        })}
      </ul>
    </>
  );
}
