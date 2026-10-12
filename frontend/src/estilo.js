/**
 * Cores semânticas de cada status, como mapas de classes Tailwind.
 * Visual PROVISÓRIO da Task 5A: a Task 5B troca pelas cores do design
 * system. As classes ficam escritas por inteiro de propósito, para o
 * Tailwind encontrá-las ao gerar o CSS. As classes de título, campo,
 * botão etc. não ficam aqui: moram nos componentes de components/ui.jsx.
 */

// Cor do texto do status de uma vinheria (tabela de dispositivos)
export const COR_STATUS = {
  ok: 'text-green-700',
  alerta: 'text-red-700',
  configurando: 'text-amber-700',
  offline: 'text-gray-500',
  aguardando: 'text-gray-500',
};

// Cor da bolinha do indicador de saúde do FIWARE
export const COR_SAUDE = {
  verificando: 'bg-gray-400',
  online: 'bg-green-600',
  offline: 'bg-red-600',
  sem_backend: 'bg-red-600',
};

// Cor da borda esquerda de cada toast
export const BORDA_TOAST = {
  alerta: 'border-l-red-600',
  fiware_offline: 'border-l-red-600',
  offline: 'border-l-gray-500',
  normal: 'border-l-green-600',
  fiware_online: 'border-l-green-600',
};
