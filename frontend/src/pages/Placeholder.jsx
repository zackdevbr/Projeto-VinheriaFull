/**
 * Tela provisória das rotas que outras tasks ainda vão preencher
 * (Detalhe e Alertas na Task 6; Chat na Task 7A).
 * Sem `task`, serve de página "não encontrada".
 */
import { EstadoVazio, LinkInterno, Titulo } from '../components/ui/index.js';

export default function Placeholder({ titulo, task }) {
  if (!task) {
    return (
      <section>
        <Titulo overline="Erro 404">Página não encontrada</Titulo>
        <EstadoVazio
          titulo="Nada por aqui"
          texto="Confira o endereço ou volte para o painel."
          acao={<LinkInterno to="/">Ir para a Visão geral</LinkInterno>}
        />
      </section>
    );
  }

  return (
    <section>
      <Titulo overline="Em construção">{titulo}</Titulo>
      <EstadoVazio titulo={titulo} texto={`Esta tela chega na ${task}.`} />
    </section>
  );
}
