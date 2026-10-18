/**
 * Aviso global (RF14): faixa fixa enquanto houver vinheria em alerta ou
 * offline (ou a EC2 fora do ar) e toasts empilhados, um por evento, com
 * link para o detalhe da vinheria. Os toasts só somem quando fechados.
 * No celular, a faixa abre com um resumo ("2 vinherias precisam de
 * atenção") e os toasts ficam acima da barra de navegação inferior.
 */
import { TriangleAlert, X } from 'lucide-react';
import { Fragment } from 'react';
import { useFleet } from '../context/FleetContext.jsx';
import { BORDA_TOAST, ICONE_TOAST } from '../estilo.js';
import { bannerSummary, contarAtencao, textoDoEvento } from '../lib/fleetEvents.js';
import { BotaoIcone, LinkVinheria } from './ui/index.js';

/** Nomes das vinherias separados por vírgula, cada um com link para o detalhe. */
function listaDeLinks(vinherias) {
  return vinherias.map((v, indice) => (
    <Fragment key={v.device_id}>
      {indice > 0 && ', '}
      <LinkVinheria deviceId={v.device_id}>{v.name}</LinkVinheria>
    </Fragment>
  ));
}

/** Frase de resumo do celular. */
function resumoCurto(total) {
  return total === 1 ? '1 vinheria precisa de atenção' : `${total} vinherias precisam de atenção`;
}

export default function AlertBanner() {
  const { fleet, toasts, fecharToast } = useFleet();
  const resumo = bannerSummary(fleet);
  const total = contarAtencao(fleet);

  return (
    <>
      {resumo?.visivel && (
        <div className="border-b border-alerta bg-alerta/8" role="alert">
          <div className="mx-auto flex max-w-pagina flex-wrap items-start gap-x-4 gap-y-1 px-4 py-2.5 text-sm md:px-6">
            <TriangleAlert size={18} strokeWidth={1.75} className="mt-0.5 shrink-0 text-alerta" aria-hidden="true" />
            {resumo.fiwareOffline && (
              <span className="font-medium">EC2/FIWARE fora do ar: todas as vinherias offline.</span>
            )}
            {!resumo.fiwareOffline && <span className="font-medium md:hidden">{resumoCurto(total)}</span>}
            {resumo.emAlerta.length > 0 && (
              <span className="basis-full md:basis-auto">Em alerta: {listaDeLinks(resumo.emAlerta)}</span>
            )}
            {resumo.offline.length > 0 && (
              <span className="basis-full md:basis-auto">Offline: {listaDeLinks(resumo.offline)}</span>
            )}
          </div>
        </div>
      )}
      <div
        className="fixed inset-x-4 bottom-20 z-40 flex flex-col gap-2 md:inset-x-auto md:right-6 md:bottom-6 md:w-96"
        aria-live="polite"
      >
        {toasts.map((toast) => {
          const Icone = ICONE_TOAST[toast.tipo];
          return (
            <div
              key={toast.id}
              className={`flex animate-entrar items-center gap-3 rounded-lg border border-l-4 border-linha bg-papel py-1 pl-3 text-sm shadow-media ${BORDA_TOAST[toast.tipo]}`}
            >
              <Icone size={18} strokeWidth={1.5} className="shrink-0" aria-hidden="true" />
              <span className="min-w-0 flex-1">
                {textoDoEvento(toast)}{' '}
                {toast.device_id && <LinkVinheria deviceId={toast.device_id}>Ver detalhe</LinkVinheria>}
              </span>
              <BotaoIcone icone={X} rotulo="Fechar aviso" onClick={() => fecharToast(toast.id)} />
            </div>
          );
        })}
      </div>
    </>
  );
}
