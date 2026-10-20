/**
 * Seletor da janela dos gráficos do detalhe (RF05): últimos 20, 50 ou 100
 * pontos, ou um intervalo de datas. Uma janela só para os três gráficos.
 * A janela só muda com dados válidos (parametrosJanela).
 */
import { useState } from 'react';
import { parametrosJanela } from '../lib/serie.js';
import { Botao, BotoesSegmentados, Campo, MensagemErro } from './ui/index.js';

const OPCOES = [
  { valor: '20', rotulo: '20' },
  { valor: '50', rotulo: '50' },
  { valor: '100', rotulo: '100' },
  { valor: 'datas', rotulo: 'Datas' },
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
      <BotoesSegmentados rotulo="Janela dos gráficos" opcoes={OPCOES} valor={modo} aoMudar={escolher} />
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
