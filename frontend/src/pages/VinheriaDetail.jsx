/**
 * Detalhe de uma vinheria (RF04, RF05, RF06, RF09, RF10, RF11): cabeçalho
 * com status, score em rosca, valores atuais com a faixa, três gráficos do
 * STH-Comet com uma janela comum, faixa editável, alerta manual e a linha
 * do tempo da vinheria. Nome, status e valores vêm do FleetContext; score,
 * histórico e alertas são lidos aqui a cada 10 s.
 */
import { ArrowLeft } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import AlertTimeline from '../components/AlertTimeline.jsx';
import GaugeScore from '../components/GaugeScore.jsx';
import PainelComandos from '../components/PainelComandos.jsx';
import SeletorJanela from '../components/SeletorJanela.jsx';
import SensorChart from '../components/SensorChart.jsx';
import TriggerPanel from '../components/TriggerPanel.jsx';
import {
  Cartao,
  CartaoKpi,
  Esqueleto,
  EstadoVazio,
  GradeBento,
  LinkInterno,
  Overline,
  SeloStatus,
  Subtitulo,
  Titulo,
} from '../components/ui/index.js';
import { JANELA_PADRAO, LEITURA_POLL_MS } from '../constants.js';
import { useFleet } from '../context/FleetContext.jsx';
import { ICONE_ATRIBUTO } from '../estilo.js';
import { useAlertas } from '../hooks/useAlertas.js';
import { useLeitura } from '../hooks/useLeitura.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import { foraDaFaixa } from '../lib/faixa.js';
import { textoVisto } from '../lib/frota.js';
import { formatarNumero } from '../lib/numero.js';

/** Id fora da frota: recém-cadastrada (aguardando o 1º ciclo) ou inexistente. */
function VinheriaAusente({ id }) {
  const carregar = useCallback(() => api.getDevice(id), [id]);
  const { dados, erro, carregando } = useLeitura(carregar);
  if (carregando) {
    return <Esqueleto className="h-64" />;
  }
  if (dados) {
    return (
      <EstadoVazio
        titulo={dados.name}
        texto="Aguardando o primeiro ciclo do monitoramento. Os dados aparecem em alguns segundos."
      />
    );
  }
  return (
    <EstadoVazio
      titulo="Vinheria não encontrada"
      texto={erro}
      acao={<LinkInterno to="/">Voltar para a Visão geral</LinkInterno>}
    />
  );
}

/** Valor atual de um atributo com a faixa no rodapé (vermelho quando fora). */
function KpiAtributo({ atributo, valor, faixa }) {
  const fora = foraDaFaixa(valor, faixa);
  const rodape = faixa
    ? `${fora ? 'Fora da faixa' : 'Faixa'} ${formatarNumero(faixa.min)}–${formatarNumero(faixa.max)} ${atributo.unidade}`
    : undefined;
  return (
    <CartaoKpi
      rotulo={atributo.rotulo}
      icone={ICONE_ATRIBUTO[atributo.chave]}
      valor={valor ?? null}
      unidade={atributo.unidade}
      rodape={rodape}
      rodapeAlerta={fora}
    />
  );
}

export default function VinheriaDetail() {
  const { id } = useParams();
  const { fleet } = useFleet();
  const vinheria = fleet?.vinherias.find((v) => v.device_id === id) ?? null;
  const carregarScore = useCallback(() => api.getScore(id), [id]);
  const score = useLeitura(vinheria ? carregarScore : null, LEITURA_POLL_MS);
  const alertas = useAlertas(id, 20);
  const [janela, setJanela] = useState(JANELA_PADRAO);

  if (!fleet) {
    return <Esqueleto className="h-64" />;
  }
  if (!vinheria) {
    return <VinheriaAusente id={id} />;
  }
  const limites = score.dados?.limits ?? null;

  return (
    <section className="flex flex-col gap-6">
      <div>
        <LinkInterno to="/">
          <span className="inline-flex min-h-11 items-center gap-1">
            <ArrowLeft size={16} aria-hidden="true" />
            Visão geral
          </span>
        </LinkInterno>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <Titulo overline={vinheria.city}>{vinheria.name}</Titulo>
          <div className="flex flex-col items-start gap-1 md:items-end">
            <SeloStatus status={vinheria.status} />
            <span className="text-sm text-taupe">{textoVisto(vinheria)}</span>
          </div>
        </div>
      </div>

      <GradeBento>
        <GaugeScore relatorio={score.dados} />
        {ATRIBUTOS.map((atributo) => (
          <KpiAtributo
            key={atributo.chave}
            atributo={atributo}
            valor={vinheria.current[atributo.chave]}
            faixa={limites?.[atributo.chave] ?? null}
          />
        ))}
      </GradeBento>

      <div className="flex flex-col gap-2">
        <Overline>Janela dos gráficos</Overline>
        <SeletorJanela janela={janela} aoMudar={setJanela} />
      </div>

      <GradeBento>
        {ATRIBUTOS.map(({ chave }) => (
          <SensorChart key={chave} deviceId={id} attr={chave} janela={janela} faixa={limites?.[chave] ?? null} />
        ))}
        <TriggerPanel deviceId={id} onSalvo={score.recarregar} />
        <PainelComandos deviceId={id} status={vinheria.status} />
        <Cartao larg={4}>
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <Subtitulo>Linha do tempo</Subtitulo>
            <LinkInterno to={`/alertas?vinheria=${encodeURIComponent(id)}`}>Ver todos os alertas</LinkInterno>
          </div>
          <AlertTimeline leitura={alertas} />
        </Cartao>
      </GradeBento>
    </section>
  );
}
