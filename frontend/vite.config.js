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
 * Configuração do Vite (servidor de desenvolvimento e build) e do Vitest.
 *
 * O painel chama sempre caminhos relativos (/api/...). Aqui o Vite encaminha
 * esses caminhos para o backend FastAPI (proxy), então não há CORS nem
 * endereço do backend dentro do código. O destino vem de BACKEND_URL no
 * frontend/.env; sem ela, usa o backend local na porta 8000.
 * O Tailwind CSS v4 entra pelo plugin oficial do Vite.
 */
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxy = { '/api': env.BACKEND_URL || 'http://localhost:8000' };
  return {
    plugins: [react(), tailwindcss()],
    server: { port: 5173, strictPort: true, proxy },
    preview: { proxy },
    test: { environment: 'node', include: ['src/**/*.test.js'] },
  };
});
