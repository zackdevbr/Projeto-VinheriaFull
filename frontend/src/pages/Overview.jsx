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
 * Visão geral da frota (RF12): herói da marca, quatro indicadores (total,
 * ok, em alerta, offline) e um cartão por vinheria, com quem precisa de
 * atenção primeiro. Tudo vem do FleetContext (polling de 5 s), sem chamada
 * nova ao backend.
 */
import { CircleCheck, LayoutGrid, TriangleAlert, WifiOff } from 'lucide-react';
import VinheriaCard from '../components/VinheriaCard.jsx';
import { CartaoKpi, Esqueleto, EstadoVazio, GradeBento, Heroi, LinkInterno } from '../components/ui/index.js';
import { IMAGEM_HEROI } from '../constants.js';
import { useFleet } from '../context/FleetContext.jsx';
import { ordenarFrota, resumoFrota } from '../lib/frota.js';

/** Esqueleto enquanto a primeira leitura da frota não chega. */
function Carregando() {
  return (
    <GradeBento>
      <Esqueleto className="h-32" />
      <Esqueleto className="h-32" />
      <Esqueleto className="h-32" />
      <Esqueleto className="h-32" />
      <Esqueleto className="h-56 md:col-span-2" />
      <Esqueleto className="h-56 md:col-span-2" />
    </GradeBento>
  );
}

/** Indicadores e cartões da frota já carregada. */
function Frota({ frota }) {
  const resumo = resumoFrota(frota);
  return (
    <div className="flex flex-col gap-6">
      <GradeBento>
        <CartaoKpi rotulo="Vinherias" icone={LayoutGrid} valor={resumo.total} />
        <CartaoKpi
          rotulo="OK"
          icone={CircleCheck}
          valor={resumo.ok}
          rodape={resumo.configurando > 0 ? `${resumo.configurando} configurando` : undefined}
        />
        <CartaoKpi
          rotulo="Em alerta"
          icone={TriangleAlert}
          valor={resumo.alerta}
          variante={resumo.alerta > 0 ? 'destaque' : 'padrao'}
        />
        <CartaoKpi rotulo="Offline" icone={WifiOff} valor={resumo.offline} />
      </GradeBento>
      <GradeBento>
        {ordenarFrota(frota.vinherias).map((vinheria) => (
          <VinheriaCard key={vinheria.device_id} vinheria={vinheria} />
        ))}
      </GradeBento>
    </div>
  );
}

export default function Overview() {
  const { fleet } = useFleet();
  let conteudo;
  if (!fleet) {
    conteudo = <Carregando />;
  } else if (fleet.vinherias.length === 0) {
    conteudo = (
      <EstadoVazio
        titulo="Nenhuma vinheria cadastrada"
        texto="Cadastre a primeira para começar o monitoramento."
        acao={<LinkInterno to="/dispositivos">Cadastrar vinheria</LinkInterno>}
      />
    );
  } else {
    conteudo = <Frota frota={fleet} />;
  }
  return (
    <section>
      <Heroi titulo="Smart Solutions" subtitulo="Monitoramento de vinherias" imagem={IMAGEM_HEROI} />
      {conteudo}
    </section>
  );
}
