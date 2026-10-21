/**
 * Campos da faixa ideal (RF06): mínimo e máximo de temperatura, umidade e
 * luminosidade, cada um com o erro de validação embaixo. Usado no
 * cadastro da vinheria (faixa inicial) e no detalhe (edição). Quem usa
 * guarda os textos dos campos e valida com validarFaixa.
 */
import { ATRIBUTOS } from '../lib/atributos.js';
import { Campo } from './ui/index.js';

const LIMITES = [
  ['min', 'Mín'],
  ['max', 'Máx'],
];

/**
 * `campos` = { temperature: { min, max }, ... } em texto; `aoMudar(chave,
 * limite, valor)` recebe cada alteração; `erros` = { 'temperature.min': msg }.
 */
export default function CamposFaixa({ campos, aoMudar, erros = {} }) {
  return (
    <div className="flex flex-col gap-4">
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
                onChange={(e) => aoMudar(chave, limite, e.target.value)}
                erro={erros[`${chave}.${limite}`]}
              />
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
