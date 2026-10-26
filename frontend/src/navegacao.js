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
 * Itens do menu do painel, compartilhados pelo menu do topo (desktop) e
 * pela barra inferior (celular), para os dois nunca divergirem.
 * `contaAtencao` marca o item que mostra o selo com o número de vinherias
 * em alerta ou offline.
 */
import { BellRing, Cpu, LayoutGrid, MessageCircle } from 'lucide-react';

export const MENU = [
  { to: '/', rotulo: 'Visão geral', icone: LayoutGrid },
  { to: '/dispositivos', rotulo: 'Dispositivos', icone: Cpu },
  { to: '/alertas', rotulo: 'Alertas', icone: BellRing, contaAtencao: true },
  { to: '/chat', rotulo: 'Chat', icone: MessageCircle },
];
