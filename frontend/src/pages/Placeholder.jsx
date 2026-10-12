/**
 * Tela provisória das rotas que outras tasks ainda vão preencher
 * (Visão geral, Detalhe e Alertas na Task 6; Chat na Task 7A).
 * Sem `task`, serve de página "não encontrada".
 */
import { Nota, Titulo } from '../components/ui.jsx';

export default function Placeholder({ titulo, task }) {
  return (
    <section>
      <Titulo>{titulo}</Titulo>
      <Nota>{task ? `Esta tela chega na ${task}.` : 'Confira o endereço ou use o menu acima.'}</Nota>
    </section>
  );
}
