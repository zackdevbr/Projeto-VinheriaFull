/**
 * Painel "Avançado" aberto pela engrenagem da barra superior: troca do IP
 * do FIWARE (EC2) em runtime e resultado do health de cada serviço. O IP
 * padrão vem do .env do backend (IP elástico); este é o único lugar onde
 * ele pode ser trocado. Ao abrir, o foco vai para o campo do IP.
 */
import { useEffect, useRef, useState } from 'react';
import { useConfig } from '../context/ConfigContext.jsx';
import { useAcao } from '../hooks/useAcao.js';
import { Botao, Campo, MensagemErro, Overline } from './ui/index.js';

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

export default function PainelAvancado() {
  const { config, health, salvarIp } = useConfig();
  const [ip, setIp] = useState('');
  const [salvo, setSalvo] = useState(null);
  const salvar = useAcao(salvarIp);
  const campo = useRef(null);

  useEffect(() => {
    campo.current?.focus();
  }, []);

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
    <div
      id="painel-avancado"
      className="animate-entrar border-t border-linha bg-papel px-4 py-4 shadow-media md:absolute md:top-full md:right-6 md:w-90 md:rounded-2xl md:border"
    >
      <Overline>FIWARE na EC2</Overline>
      <form onSubmit={aoSalvar} className="mt-3 flex flex-col gap-3">
        <Campo
          ref={campo}
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
      <div className="mt-2">
        <MensagemErro erro={salvar.erro} />
      </div>
      {salvo && <p role="status" className="text-sm text-ok">{salvo}</p>}
      {health && (
        <ul className="mt-3 space-y-1 border-t border-linha pt-3 text-sm">
          {SERVICOS.map(([chave, nome]) => (
            <li key={chave} className="flex justify-between gap-3">
              <span>{nome}</span>
              <span className="text-right font-mono text-xs text-taupe">{descreverServico(health[chave])}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
