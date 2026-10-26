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
 * Linha do tempo de alertas (RF10): ícone do tipo, o que aconteceu, início,
 * fim (ou "em aberto" pulsando) e duração. Mostra a vinheria de cada alerta
 * quando a lista mistura várias. Recebe a leitura pronta (useAlertas).
 */
import { TriangleAlert } from 'lucide-react';
import { ID_FIWARE } from '../constants.js';
import { ICONE_ATRIBUTO } from '../estilo.js';
import { duracao, formatarDataHora, rotuloAlerta } from '../lib/alertas.js';
import { Esqueleto, LinkVinheria, MensagemErro, Nota } from './ui/index.js';

/** Nome da vinheria com link, ou "EC2" para a queda do FIWARE. */
function Origem({ deviceId, nomes }) {
  if (deviceId === ID_FIWARE) {
    return <span className="text-taupe">EC2</span>;
  }
  return <LinkVinheria deviceId={deviceId}>{nomes[deviceId] ?? deviceId}</LinkVinheria>;
}

/** Selo "em aberto" com o ponto pulsando. */
function EmAberto() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-alerta/10 px-2 text-alerta">
      <span className="size-1.5 animate-pulsar rounded-full bg-alerta" aria-hidden="true" />
      em aberto
    </span>
  );
}

export default function AlertTimeline({ leitura, mostrarVinheria = false, nomes = {} }) {
  const { dados, erro, carregando } = leitura;
  if (carregando && !dados) {
    return <Esqueleto className="h-40" />;
  }
  return (
    <>
      <MensagemErro erro={erro} />
      {dados && dados.length === 0 && <Nota>Nenhum alerta registrado.</Nota>}
      <ol className="flex flex-col">
        {(dados ?? []).map((alerta) => {
          // Atributo que o painel não conhece (alerta novo no backend) ganha um ícone genérico em vez de quebrar a tela
          const Icone = ICONE_ATRIBUTO[alerta.device_id === ID_FIWARE ? ID_FIWARE : alerta.attr] ?? TriangleAlert;
          const aberto = alerta.closed_at === null || alerta.closed_at === undefined;
          return (
            <li
              key={alerta.id}
              className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 border-b border-linha py-3 last:border-b-0 md:grid-cols-[auto_minmax(0,1fr)_auto_6rem] md:items-center md:gap-x-6"
            >
              <Icone
                size={20}
                strokeWidth={1.5}
                aria-hidden="true"
                className={`row-span-3 mt-0.5 md:row-span-1 md:mt-0 ${aberto ? 'text-alerta' : 'text-taupe'}`}
              />
              <div className="min-w-0">
                <p className="font-medium text-vinho">{rotuloAlerta(alerta)}</p>
                {mostrarVinheria && (
                  <p className="text-sm">
                    <Origem deviceId={alerta.device_id} nomes={nomes} />
                  </p>
                )}
              </div>
              <p className="text-sm text-taupe tabular-nums">
                {formatarDataHora(alerta.opened_at)} → {aberto ? <EmAberto /> : formatarDataHora(alerta.closed_at)}
              </p>
              <p className="text-sm text-taupe tabular-nums md:text-right">{aberto ? '' : duracao(alerta.duration_seconds)}</p>
            </li>
          );
        })}
      </ol>
    </>
  );
}
