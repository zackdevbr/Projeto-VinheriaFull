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
 * Fábrica de contexto React: devolve o Provider e um hook de acesso que
 * falha cedo quando usado fora dele. Evita repetir createContext +
 * useContext + checagem em cada contexto do painel (Config, Fleet e os das
 * próximas tasks).
 */
import { createContext, useContext } from 'react';

export function criarContexto(nome) {
  const Contexto = createContext(null);
  function useContexto() {
    const valor = useContext(Contexto);
    if (!valor) {
      throw new Error(`use${nome} precisa estar dentro de <${nome}Provider>`);
    }
    return valor;
  }
  return [Contexto.Provider, useContexto];
}
