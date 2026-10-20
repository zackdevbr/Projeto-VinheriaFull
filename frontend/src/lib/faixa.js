/**
 * Faixa ideal de uma vinheria (RF06): validação do formulário antes de ir
 * ao backend e a pergunta "este valor está fora da faixa?" usada nos
 * cartões e nos gráficos.
 */
import { ATRIBUTOS } from './atributos.js';

const SEM_NUMERO = 'Informe um número';
const MIN_MAIOR = 'O mínimo precisa ser menor que o máximo';

/** Texto do campo (aceita vírgula) para número; vazio ou inválido vira NaN. */
function paraNumero(valor) {
  const texto = String(valor ?? '').trim().replace(',', '.');
  return texto === '' ? Number.NaN : Number(texto);
}

/**
 * Valida a faixa dos três atributos. Devolve { dados, erros }: `dados` com
 * números quando tudo está certo (senão null) e `erros` por campo, no
 * formato { 'temperature.min': 'mensagem' }.
 */
export function validarFaixa(campos) {
  const dados = {};
  const erros = {};
  for (const { chave } of ATRIBUTOS) {
    const min = paraNumero(campos[chave]?.min);
    const max = paraNumero(campos[chave]?.max);
    if (!Number.isFinite(min)) {
      erros[`${chave}.min`] = SEM_NUMERO;
    }
    if (!Number.isFinite(max)) {
      erros[`${chave}.max`] = SEM_NUMERO;
    }
    if (Number.isFinite(min) && Number.isFinite(max) && min >= max) {
      erros[`${chave}.max`] = MIN_MAIOR;
    }
    dados[chave] = { min, max };
  }
  return Object.keys(erros).length > 0 ? { dados: null, erros } : { dados, erros };
}

/** true quando o valor passa do mínimo ou do máximo; sem valor ou sem faixa, false. */
export function foraDaFaixa(valor, faixa) {
  if (valor === null || valor === undefined || !faixa) {
    return false;
  }
  return valor < faixa.min || valor > faixa.max;
}
