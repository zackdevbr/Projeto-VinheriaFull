/**
 * Faixa ideal da vinheria (RF06): mínimo e máximo de cada atributo. A mesma
 * faixa é limite dos alertas e referência do score. Valida no navegador
 * (números, mínimo < máximo) e salva pelo backend, que grava no Orion e
 * manda o set_limits ao ESP32; offline, o envio fica pendente.
 */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { useLeitura } from '../hooks/useLeitura.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import { validarFaixa } from '../lib/faixa.js';
import { Botao, Campo, Cartao, Esqueleto, MensagemErro, Subtitulo } from './ui/index.js';

const SUCESSO = {
  enviado: 'Faixa salva e enviada ao ESP32.',
  pendente: 'Faixa salva. O ESP32 recebe quando voltar a ficar online.',
};

const LIMITES = [
  ['min', 'Mín'],
  ['max', 'Máx'],
];

/** Faixa do backend (números) para os campos do formulário (texto). */
function paraCampos(faixa) {
  return Object.fromEntries(
    ATRIBUTOS.map(({ chave }) => [chave, { min: String(faixa[chave].min), max: String(faixa[chave].max) }]),
  );
}

export default function TriggerPanel({ deviceId, onSalvo }) {
  const carregar = useCallback(() => api.getTriggers(deviceId), [deviceId]);
  const { dados, erro: erroLeitura } = useLeitura(carregar);
  const [campos, setCampos] = useState(null);
  const [erros, setErros] = useState({});
  const [aviso, setAviso] = useState(null);
  const salvar = useAcao(api.saveTriggers);

  useEffect(() => {
    if (dados) {
      setCampos(paraCampos(dados));
    }
  }, [dados]);

  function alterar(chave, limite, valor) {
    setCampos((atuais) => ({ ...atuais, [chave]: { ...atuais[chave], [limite]: valor } }));
  }

  async function aoSalvar(evento) {
    evento.preventDefault();
    setAviso(null);
    const { dados: faixa, erros: invalidos } = validarFaixa(campos);
    setErros(invalidos);
    if (!faixa) {
      return;
    }
    const resultado = await salvar.executar(deviceId, faixa);
    if (resultado.ok) {
      setAviso(SUCESSO[resultado.valor.device_sync]);
      onSalvo();
    }
  }

  return (
    <Cartao larg={2}>
      <Subtitulo>Faixa ideal</Subtitulo>
      <MensagemErro erro={erroLeitura} />
      {!campos ? (
        <Esqueleto className="h-64" />
      ) : (
        <form onSubmit={aoSalvar} className="flex flex-col gap-4" noValidate>
          {ATRIBUTOS.map(({ chave, rotulo, unidade }) => (
            <fieldset key={chave}>
              <legend className="mb-2 text-overline uppercase text-taupe">{`${rotulo} (${unidade})`}</legend>
              <div className="grid grid-cols-2 gap-3">
                {LIMITES.map(([limite, nome]) => (
                  <Campo
                    key={limite}
                    rotulo={nome}
                    inputMode="decimal"
                    value={campos[chave][limite]}
                    onChange={(e) => alterar(chave, limite, e.target.value)}
                    erro={erros[`${chave}.${limite}`]}
                  />
                ))}
              </div>
            </fieldset>
          ))}
          <MensagemErro erro={salvar.erro} />
          {aviso && (
            <p role="status" className="text-sm text-ok">
              {aviso}
            </p>
          )}
          <Botao type="submit" className="w-full" carregando={salvar.executando} textoCarregando="Salvando…">
            Salvar faixa
          </Botao>
        </form>
      )}
    </Cartao>
  );
}
