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
 * Junta pausas seguidas em uma só. Duas pausas são "contínuas" quando as
 * leituras entre elas duram no máximo `juntarSeg` segundos (o sensor falhou,
 * voltou por instantes e falhou de novo). O grupo vai do primeiro ao último
 * ponto vazio, e `segundos` soma o tempo parado de todas.
 */
function juntarPausas(brutas, juntarSeg) {
  const grupos = [];
  for (const pausa of brutas) {
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && juntarSeg > 0 && (pausa.parada - ultimo.retomada) / 1000 <= juntarSeg) {
      ultimo.ultimoIndice = pausa.indice;
      ultimo.segundos += pausa.segundos;
      ultimo.pausas += 1;
      ultimo.retomada = pausa.retomada;
    } else {
      grupos.push({
        indice: pausa.indice,
        ultimoIndice: pausa.indice,
        segundos: pausa.segundos,
        pausas: 1,
        retomada: pausa.retomada,
      });
    }
  }
  return grupos.map(({ retomada, ...grupo }) => grupo);
}

/**
 * Rótulos dd/mm HH:mm:ss (hora local), valores e vãos, na ordem recebida. O
 * eixo do gráfico é por leitura, não por tempo; por isso, quando duas leituras
 * seguidas distam mais de `limiteLacunaSeg` segundos (sensor desligado ou
 * offline), entra um ponto vazio (null) entre elas, que quebra a linha. Os
 * vãos voltam em `lacunas` ({ indice, ultimoIndice, segundos, pausas }, índices
 * dos pontos vazios), já com as pausas contínuas juntas (`juntarSeg`) e o
 * total parado em `segundos`. Sem `limiteLacunaSeg`, nunca cria vãos; sem
 * `juntarSeg`, não junta nenhum.
 */
export function paraSerie(pontos, limiteLacunaSeg = Number.POSITIVE_INFINITY, juntarSeg = 0) {
  const rotulos = [];
  const valores = [];
  const brutas = [];
  pontos.forEach((ponto, i) => {
    if (i > 0) {
      const anterior = pontos[i - 1];
      const segundos = Math.round((new Date(ponto.ts) - new Date(anterior.ts)) / 1000);
      if (segundos > limiteLacunaSeg) {
        brutas.push({
          indice: valores.length,
          segundos,
          parada: new Date(anterior.ts).getTime(),
          retomada: new Date(ponto.ts).getTime(),
        });
        rotulos.push('');
        valores.push(null);
      }
    }
    rotulos.push(dataHoraLocal(ponto.ts));
    valores.push(ponto.value);
  });
  return { rotulos, valores, lacunas: juntarPausas(brutas, juntarSeg) };
}

/** Frase que explica os vãos do gráfico; null quando não houve nenhum. */
export function resumoLacunas(lacunas) {
  if (lacunas.length === 0) {
    return null;
  }
  const total = lacunas.reduce((soma, lacuna) => soma + lacuna.segundos, 0);
  if (lacunas.length === 1) {
    const { pausas } = lacunas[0];
    const seguidas = pausas > 1 ? `, em ${pausas} pausas seguidas` : '';
    return `O sensor ficou ${duracao(total)} sem enviar leituras${seguidas}.`;
  }
  const maior = Math.max(...lacunas.map((lacuna) => lacuna.segundos));
  return `O sensor ficou sem enviar leituras ${lacunas.length} vezes, somando ${duracao(total)}; a maior pausa foi de ${duracao(maior)}.`;
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
 * Marca do eixo horizontal: só o dia (dd/mm) do ponto; a hora fica para o
 * balão que aparece ao passar o mouse sobre ele. Cada marca mostra o próprio
 * dia, sem olhar as outras: o Chart.js só desenha algumas marcas (por
 * amostragem), então depender de uma marca anterior faria o dia sumir. O
 * ponto vazio de um vão não ganha marca.
 */
export function rotuloDoEixo(rotulo) {
  return rotulo ? rotulo.slice(0, 5) : '';
}

/** Título do balão de um ponto: "20/10 às 21:14:25". */
export function tituloDoPonto(rotulo) {
  return rotulo ? `${rotulo.slice(0, 5)} às ${rotulo.slice(6)}` : '';
}

/**
 * Título do balão a partir dos itens que o Chart.js entrega. A lista pode
 * vir vazia: o filtro do balão descarta tudo sobre um vão do gráfico (ponto
 * vazio), e ler o primeiro item ali quebraria o gráfico durante o mouse.
 */
export function tituloDoBalao(itens) {
  return itens.length > 0 ? tituloDoPonto(itens[0].label) : '';
}

/**
 * O backend responde 503 quando não consegue falar com o FIWARE (EC2
 * desligada, IP errado ou tempo esgotado). Para a tela, o histórico fica
 * indisponível até ele voltar, e o texto técnico do erro não ajuda ninguém.
 */
export function fiwareForaDoAr(falha) {
  return falha?.status === 503;
}
