/**
 * Mapas de estilo por estado: classes Tailwind dos tokens do design system
 * (styles.css) e ícones Lucide. As classes ficam escritas por inteiro de
 * propósito, para o Tailwind encontrá-las ao gerar o CSS. As peças de
 * tela (título, botão, cartão...) moram em components/ui/.
 */
import {
  CircleCheck,
  Hourglass,
  Server,
  ServerCrash,
  SlidersHorizontal,
  TriangleAlert,
  WifiOff,
} from 'lucide-react';

// Selo de status de uma vinheria: texto, fundo a 10 % e borda na cor do estado
export const COR_STATUS = {
  ok: 'border-ok/30 bg-ok/10 text-ok',
  alerta: 'border-alerta/30 bg-alerta/10 text-alerta',
  configurando: 'border-config/30 bg-config/10 text-config',
  offline: 'border-taupe/30 bg-taupe/10 text-taupe',
  aguardando: 'border-taupe/30 bg-taupe/10 text-taupe',
};

// Ícone do selo de status (sempre junto do texto: a cor sozinha não basta)
export const ICONE_STATUS = {
  ok: CircleCheck,
  alerta: TriangleAlert,
  configurando: SlidersHorizontal,
  offline: WifiOff,
  aguardando: Hourglass,
};

// Cor do ponto do indicador de saúde do FIWARE
export const COR_SAUDE = {
  verificando: 'bg-taupe',
  online: 'bg-ok',
  offline: 'bg-alerta',
  sem_backend: 'bg-alerta',
};

// Cor da faixa esquerda de cada toast
export const BORDA_TOAST = {
  alerta: 'border-l-alerta',
  fiware_offline: 'border-l-alerta',
  offline: 'border-l-taupe',
  normal: 'border-l-ok',
  fiware_online: 'border-l-ok',
};

// Ícone de cada toast
export const ICONE_TOAST = {
  alerta: TriangleAlert,
  offline: WifiOff,
  normal: CircleCheck,
  fiware_offline: ServerCrash,
  fiware_online: Server,
};
