/**
 * Aviso global (RF14): faixa fixa enquanto houver vinheria em alerta ou
 * offline (ou a EC2 fora do ar) e toasts empilhados, um por evento, com
 * link para o detalhe da vinheria. Os toasts só somem quando fechados.
 */
import { Fragment } from 'react';
import { useFleet } from '../context/FleetContext.jsx';
import { BORDA_TOAST } from '../estilo.js';
import { bannerSummary, textoDoEvento } from '../lib/fleetEvents.js';
import { LinkVinheria } from './ui/index.js';

/** Nomes das vinherias separados por vírgula, cada um com link para o detalhe. */
function listaDeLinks(vinherias) {
  return vinherias.map((v, indice) => (
    <Fragment key={v.device_id}>
      {indice > 0 && ', '}
      <LinkVinheria deviceId={v.device_id}>{v.name}</LinkVinheria>
    </Fragment>
  ));
}

export default function AlertBanner() {
  const { fleet, toasts, fecharToast } = useFleet();
  const resumo = bannerSummary(fleet);

  return (
    <>
      {resumo?.visivel && (
        <div className="flex flex-wrap gap-4 border-b border-red-600 bg-red-50 px-4 py-2 text-sm" role="alert">
          {resumo.fiwareOffline && <span>EC2/FIWARE fora do ar: todas as vinherias offline.</span>}
          {resumo.emAlerta.length > 0 && <span>Em alerta: {listaDeLinks(resumo.emAlerta)}</span>}
          {resumo.offline.length > 0 && <span>Offline: {listaDeLinks(resumo.offline)}</span>}
        </div>
      )}
      <div className="fixed bottom-4 right-4 z-20 flex max-w-sm flex-col gap-2" aria-live="polite">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center gap-2 border border-l-4 border-gray-300 bg-white px-3 py-2 text-sm shadow ${BORDA_TOAST[toast.tipo]}`}
          >
            <span>{textoDoEvento(toast)}</span>
            {toast.device_id && <LinkVinheria deviceId={toast.device_id}>Ver detalhe</LinkVinheria>}
            <button
              type="button"
              onClick={() => fecharToast(toast.id)}
              aria-label="Fechar aviso"
              className="ml-auto px-1 text-gray-500 hover:text-gray-900"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
