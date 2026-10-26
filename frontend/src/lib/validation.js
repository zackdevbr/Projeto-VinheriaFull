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
 * Validação do cadastro de vinheria feita no navegador, antes de chamar o
 * backend. Repete as regras do DeviceCreate (backend/app/models/schemas.py)
 * para o usuário ver o erro na hora; o backend continua validando.
 */

const ID_VALIDO = /^vinheria\d{3}$/;
const LIMITE_TEXTO = 60;

/**
 * Limpa e confere os campos do formulário.
 * Devolve { dados, erro: null } quando está tudo certo, ou { dados: null, erro }.
 */
export function validarCadastro(campos) {
  const dados = {
    device_id: campos.device_id.trim().toLowerCase(),
    name: campos.name.trim(),
    city: campos.city.trim(),
  };
  if (!ID_VALIDO.test(dados.device_id)) {
    return { dados: null, erro: 'O id deve seguir o formato vinheria00N (ex.: vinheria003).' };
  }
  if (!dados.name || !dados.city) {
    return { dados: null, erro: 'Informe nome e cidade.' };
  }
  if (dados.name.length > LIMITE_TEXTO || dados.city.length > LIMITE_TEXTO) {
    return { dados: null, erro: `Nome e cidade têm no máximo ${LIMITE_TEXTO} caracteres.` };
  }
  return { dados, erro: null };
}
