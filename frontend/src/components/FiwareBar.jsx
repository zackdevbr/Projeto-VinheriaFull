/**
 * Barra fixa do topo: marca Smart Solutions, indicador de saúde do FIWARE
 * com o IP em uso e o painel "Avançado" (recolhido) para trocar o IP da EC2
 * em runtime. O IP padrão vem do .env do backend (IP elástico).
 */
import { useState } from 'react';
import { useConfig } from '../context/ConfigContext.jsx';
import { COR_SAUDE } from '../estilo.js';
import { useAcao } from '../hooks/useAcao.js';
import { Botao, Campo, MensagemErro } from './ui/index.js';

const ROTULO = {
  verificando: 'Verificando FIWARE…',
  online: 'FIWARE online',
  offline: 'FIWARE fora do ar',
  sem_backend: 'Backend indisponível',
};

const SERVICOS = [
  ['orion', 'Orion'],
  ['iota', 'IoT Agent'],
  ['sth', 'STH-Comet'],
];

/** Texto do resultado de um serviço no health. */
function descreverServico(servico) {
  if (servico.ok) {
    return `ok (${servico.latency_ms} ms)`;
  }
  return servico.error ? `falhou — ${servico.error}` : 'falhou';
}

export default function FiwareBar() {
  const { config, health, healthState, salvarIp } = useConfig();
  const [ip, setIp] = useState('');
  const [salvo, setSalvo] = useState(null);
  const salvar = useAcao(salvarIp);

  async function aoSalvar(evento) {
    evento.preventDefault();
    setSalvo(null);
    const resultado = await salvar.executar(ip);
    if (resultado.ok) {
      setSalvo(`IP salvo: ${resultado.valor.ec2_ip}`);
      setIp('');
    }
  }

  return (
    <header className="sticky top-0 z-10 flex flex-wrap items-center gap-4 border-b border-gray-300 bg-white px-4 py-2">
      <strong className="text-lg font-semibold">Smart Solutions</strong>
      <span className="flex items-center gap-2 text-sm">
        <span className={`h-2.5 w-2.5 rounded-full ${COR_SAUDE[healthState]}`} aria-hidden="true" />
        {ROTULO[healthState]}
        {config ? ` · ${config.ec2_ip}` : ''}
      </span>
      <details className="ml-auto text-sm">
        <summary className="cursor-pointer select-none">Avançado</summary>
        <form onSubmit={aoSalvar} className="mt-2 flex items-end gap-2">
          <Campo
            rotulo="IP do FIWARE (EC2)"
            value={ip}
            onChange={(e) => setIp(e.target.value)}
            placeholder={config?.ec2_ip ?? ''}
            required
          />
          <Botao type="submit" carregando={salvar.executando} textoCarregando="Salvando…">
            Salvar
          </Botao>
        </form>
        <MensagemErro erro={salvar.erro} />
        {salvo && <p role="status" className="mt-1">{salvo}</p>}
        {health && (
          <ul className="mt-2 space-y-0.5 text-gray-700">
            {SERVICOS.map(([chave, nome]) => (
              <li key={chave}>
                {nome}: {descreverServico(health[chave])}
              </li>
            ))}
          </ul>
        )}
      </details>
    </header>
  );
}
