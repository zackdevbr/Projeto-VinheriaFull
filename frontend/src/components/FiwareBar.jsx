/**
 * Barra fixa do topo: logo Smart Solutions, indicador de saúde do FIWARE
 * (com o IP em uso a partir de 768 px), menu do desktop e a engrenagem que
 * abre o painel Avançado. O painel fecha pela engrenagem ou pela tecla Esc,
 * e o foco volta para a engrenagem.
 */
import { Settings } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { LOGO_SRC } from '../constants.js';
import { useConfig } from '../context/ConfigContext.jsx';
import { COR_SAUDE } from '../estilo.js';
import MenuTopo from './MenuTopo.jsx';
import PainelAvancado from './PainelAvancado.jsx';
import { BotaoIcone, Logo } from './ui/index.js';

const ROTULO = {
  verificando: 'Verificando FIWARE…',
  online: 'FIWARE online',
  offline: 'FIWARE fora do ar',
  sem_backend: 'Backend indisponível',
};

/** Ponto colorido + texto; no celular só "FIWARE", para caber na barra. */
function SeloSaude({ estado, ip }) {
  return (
    <span className="flex items-center gap-2 text-sm" title={ROTULO[estado]}>
      <span className={`size-2.5 shrink-0 rounded-full ${COR_SAUDE[estado]}`} aria-hidden="true" />
      <span className="md:hidden">
        FIWARE<span className="sr-only">: {ROTULO[estado]}</span>
      </span>
      <span className="hidden md:inline">
        {ROTULO[estado]}
        {ip && <span className="ml-2 font-mono text-xs text-taupe">{ip}</span>}
      </span>
    </span>
  );
}

export default function FiwareBar() {
  const { config, healthState } = useConfig();
  const [aberto, setAberto] = useState(false);
  const engrenagem = useRef(null);

  const fechar = useCallback(() => {
    setAberto(false);
    engrenagem.current?.focus();
  }, []);

  // Esc fecha o painel enquanto ele estiver aberto
  useEffect(() => {
    if (!aberto) {
      return undefined;
    }
    function aoTeclar(evento) {
      if (evento.key === 'Escape') {
        fechar();
      }
    }
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [aberto, fechar]);

  return (
    <header className="sticky top-0 z-30 border-b border-linha bg-papel">
      <div className="mx-auto flex min-h-14 max-w-pagina items-center gap-3 px-4 md:gap-6 md:px-6">
        <Logo src={LOGO_SRC} />
        <SeloSaude estado={healthState} ip={config?.ec2_ip} />
        <div className="ml-auto flex items-center gap-4">
          <MenuTopo />
          <BotaoIcone
            ref={engrenagem}
            icone={Settings}
            rotulo="Configurações avançadas"
            aria-expanded={aberto}
            aria-controls="painel-avancado"
            onClick={() => (aberto ? fechar() : setAberto(true))}
          />
        </div>
      </div>
      {aberto && <PainelAvancado />}
    </header>
  );
}
