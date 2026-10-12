/**
 * Ponto de entrada do painel. Versão provisória da 5A.1: só confirma que o
 * Vite, o React e o Tailwind estão de pé. A 5A.5 liga o roteador e o App.
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <h1 className="p-4 text-2xl font-semibold text-green-700">Smart Solutions</h1>
  </StrictMode>,
);
