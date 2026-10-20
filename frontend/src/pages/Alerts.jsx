/**
 * Histórico de alertas (RF10): linha do tempo geral, filtrável por vinheria
 * ou pela EC2. O filtro mora na URL (?vinheria=), então o link pode ser
 * compartilhado e o Voltar do navegador desfaz a troca.
 */
import { BellRing, CircleDot } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import AlertTimeline from '../components/AlertTimeline.jsx';
import { Cartao, CartaoKpi, GradeBento, Seletor, Titulo } from '../components/ui/index.js';
import { ID_FIWARE } from '../constants.js';
import { useFleet } from '../context/FleetContext.jsx';
import { useAlertas } from '../hooks/useAlertas.js';

const LIMITE = 100;

export default function Alerts() {
  const { fleet } = useFleet();
  const [params, setParams] = useSearchParams();
  const filtro = params.get('vinheria') ?? '';
  const leitura = useAlertas(filtro || null, LIMITE);

  const vinherias = fleet?.vinherias ?? [];
  const nomes = Object.fromEntries(vinherias.map((v) => [v.device_id, v.name]));
  const opcoes = [
    { valor: '', rotulo: 'Todas as vinherias' },
    ...vinherias.map((v) => ({ valor: v.device_id, rotulo: `${v.name} · ${v.city}` })),
    { valor: ID_FIWARE, rotulo: 'EC2 / FIWARE' },
  ];
  const lista = leitura.dados ?? [];
  const abertos = lista.filter((alerta) => alerta.closed_at === null || alerta.closed_at === undefined).length;

  function trocar(evento) {
    const valor = evento.target.value;
    setParams(valor ? { vinheria: valor } : {});
  }

  return (
    <section>
      <Titulo overline="Histórico">Alertas</Titulo>
      <GradeBento>
        <Cartao larg={2}>
          <Seletor rotulo="Vinheria" opcoes={opcoes} value={filtro} onChange={trocar} />
        </Cartao>
        <CartaoKpi
          rotulo="Em aberto"
          icone={CircleDot}
          valor={leitura.dados ? abertos : null}
          variante={abertos > 0 ? 'destaque' : 'padrao'}
        />
        <CartaoKpi
          rotulo="Registrados"
          icone={BellRing}
          valor={leitura.dados ? lista.length : null}
          rodape={`últimos ${LIMITE}`}
        />
        <Cartao larg={4}>
          <AlertTimeline leitura={leitura} mostrarVinheria={!filtro} nomes={nomes} />
        </Cartao>
      </GradeBento>
    </section>
  );
}
