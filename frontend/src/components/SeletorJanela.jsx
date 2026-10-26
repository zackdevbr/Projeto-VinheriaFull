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
 * Seletor da janela dos gráficos do detalhe (RF05): as últimas 20, 50 ou
 * 100 leituras do sensor, ou um intervalo de datas ("Por período"). Uma
 * frase embaixo explica o que está sendo mostrado. Uma janela só para os três gráficos.
 * A janela só muda com dados válidos (parametrosJanela).
 */
import { useState } from 'react';
import { descricaoJanela, parametrosJanela } from '../lib/serie.js';
import { Botao, BotoesSegmentados, Campo, MensagemErro } from './ui/index.js';

const OPCOES = [
  { valor: '20', rotulo: 'Últimas 20' },
  { valor: '50', rotulo: 'Últimas 50' },
  { valor: '100', rotulo: 'Últimas 100' },
  { valor: 'datas', rotulo: 'Por período' },
];

export default function SeletorJanela({ janela, aoMudar }) {
  const [modo, setModo] = useState(janela.tipo === 'datas' ? 'datas' : String(janela.n));
  const [datas, setDatas] = useState({ de: '', ate: '' });
  const [erro, setErro] = useState(null);

  function escolher(valor) {
    setModo(valor);
    setErro(null);
    if (valor !== 'datas') {
      aoMudar({ tipo: 'ultimos', n: Number(valor) });
    }
  }

  function aplicar(evento) {
    evento.preventDefault();
    const nova = { tipo: 'datas', ...datas };
    const { erro: invalida } = parametrosJanela(nova);
    if (invalida) {
      setErro(invalida);
      return;
    }
    setErro(null);
    aoMudar(nova);
  }

  return (
    <div className="flex flex-col gap-3">
      <BotoesSegmentados rotulo="Leituras mostradas nos gráficos" opcoes={OPCOES} valor={modo} aoMudar={escolher} />
      <p className="text-sm text-taupe">
        {descricaoJanela(modo === 'datas' ? { tipo: 'datas' } : { tipo: 'ultimos', n: Number(modo) })}
      </p>
      {modo === 'datas' && (
        <form onSubmit={aplicar} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Campo rotulo="De" type="datetime-local" value={datas.de} onChange={(e) => setDatas({ ...datas, de: e.target.value })} />
          <Campo rotulo="Até" type="datetime-local" value={datas.ate} onChange={(e) => setDatas({ ...datas, ate: e.target.value })} />
          <Botao type="submit" variante="secundario">
            Aplicar
          </Botao>
        </form>
      )}
      <MensagemErro erro={erro} />
    </div>
  );
}
