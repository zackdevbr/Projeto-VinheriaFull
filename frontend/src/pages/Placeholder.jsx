/**
 * Tela provisória das rotas que outras tasks ainda vão preencher
 * (Visão geral, Detalhe e Alertas na Task 6; Chat na Task 7A).
 * Com `heroi` (rota /), abre com o herói da marca no lugar do título.
 * Sem `task`, serve de página "não encontrada".
 */
import { IMAGEM_HEROI } from '../constants.js';
import { EstadoVazio, Heroi, LinkInterno, Titulo } from '../components/ui/index.js';

export default function Placeholder({ titulo, task, heroi = false }) {
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
      {heroi ? (
        <Heroi titulo="Smart Solutions" subtitulo="Monitoramento de vinherias" imagem={IMAGEM_HEROI} />
      ) : (
        <Titulo overline="Em construção">{titulo}</Titulo>
      )}
      <EstadoVazio titulo={titulo} texto={`Esta tela chega na ${task}.`} />
    </section>
  );
}
