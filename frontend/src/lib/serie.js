/**
 * Janela dos gráficos (últimos N pontos ou intervalo de datas) e conversão
 * do histórico do STH-Comet ([{ ts, value }]) para o formato do Chart.js.
 */
import { INTERVALO_LEITURA_S } from '../constants.js';
import { duracao } from './alertas.js';

/**
 * Parâmetros do GET de histórico para a janela escolhida. Datas vêm do
 * campo datetime-local (hora local) e saem em ISO. Janela inválida
 * devolve { erro } em vez dos parâmetros.
 */
export function parametrosJanela(janela) {
  if (janela.tipo === 'ultimos') {
    return { lastN: janela.n };
  }
  if (!janela.de || !janela.ate) {
    return { erro: 'Informe o início e o fim.' };
  }
  const de = new Date(janela.de);
  const ate = new Date(janela.ate);
  if (Number.isNaN(de.getTime()) || Number.isNaN(ate.getTime())) {
    return { erro: 'Data inválida.' };
  }
  if (de >= ate) {
    return { erro: 'O início precisa ser antes do fim.' };
  }
  return { dateFrom: de.toISOString(), dateTo: ate.toISOString() };
}

/** Data e hora locais (dd/mm HH:mm:ss) de um instante ISO. */
function dataHoraLocal(iso) {
  const data = new Date(iso);
  const dia = data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  const hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  return `${dia} ${hora}`;
}

/**
 * Rótulos dd/mm HH:mm:ss (hora local), valores e vãos, na ordem recebida. O eixo
 * do gráfico é por leitura, não por tempo; por isso, quando duas leituras
 * seguidas distam mais de `limiteLacunaSeg` segundos (sensor desligado ou
 * offline), entra um ponto vazio (null) entre elas, que quebra a linha, e o
 * vão é devolvido em `lacunas` com o índice do ponto vazio e o tamanho da
 * pausa. Sem `limiteLacunaSeg`, nunca cria vãos.
 */
export function paraSerie(pontos, limiteLacunaSeg = Number.POSITIVE_INFINITY) {
  const rotulos = [];
  const valores = [];
  const lacunas = [];
  pontos.forEach((ponto, i) => {
    if (i > 0) {
      const segundos = Math.round((new Date(ponto.ts) - new Date(pontos[i - 1].ts)) / 1000);
      if (segundos > limiteLacunaSeg) {
        lacunas.push({ indice: valores.length, segundos });
        rotulos.push('');
        valores.push(null);
      }
    }
    rotulos.push(dataHoraLocal(ponto.ts));
    valores.push(ponto.value);
  });
  return { rotulos, valores, lacunas };
}

/** Frase que explica os vãos do gráfico; null quando não houve nenhum. */
export function resumoLacunas(lacunas) {
  if (lacunas.length === 0) {
    return null;
  }
  if (lacunas.length === 1) {
    return `O sensor ficou ${duracao(lacunas[0].segundos)} sem enviar leituras.`;
  }
  const maior = Math.max(...lacunas.map((lacuna) => lacuna.segundos));
  return `O sensor ficou sem enviar leituras ${lacunas.length} vezes; a maior pausa foi de ${duracao(maior)}.`;
}

/** Frase embaixo do seletor: o que é "últimas N leituras" e quanto tempo isso cobre. */
export function descricaoJanela(janela) {
  if (janela.tipo === 'ultimos') {
    return `Mostra as últimas ${janela.n} leituras do sensor (uma a cada ~${INTERVALO_LEITURA_S} s, cerca de ${duracao(janela.n * INTERVALO_LEITURA_S)}).`;
  }
  return 'Escolha o início e o fim para ver as leituras desse intervalo.';
}

/**
 * O STH-Comet responde 404 quando o intervalo pedido não tem nenhuma
 * leitura (o sensor estava desligado ou offline). Para a tela isso não é
 * falha: é "sem leituras neste período".
 */
export function semLeituras(falha) {
  return falha?.status === 404 && falha?.service === 'sth';
}

/**
 * Marca do eixo horizontal: só o dia (dd/mm), e só quando ele muda em relação
 * à marca anterior; a hora fica para o balão que aparece ao passar o mouse
 * sobre o ponto. O ponto vazio de um vão não ganha marca.
 */
export function rotuloDoEixo(rotulo, rotuloAnterior) {
  if (!rotulo) {
    return '';
  }
  const dia = rotulo.slice(0, 5);
  return rotuloAnterior && rotuloAnterior.slice(0, 5) === dia ? '' : dia;
}

/** Título do balão de um ponto: "20/10 às 21:14:25". */
export function tituloDoPonto(rotulo) {
  return rotulo ? `${rotulo.slice(0, 5)} às ${rotulo.slice(6)}` : '';
}
