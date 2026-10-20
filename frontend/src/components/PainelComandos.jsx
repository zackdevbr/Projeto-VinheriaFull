/**
 * Alerta manual (RF09): dispara pelo painel o padrão de luz e som de cada
 * anomalia no ESP32, ou desliga o alerta. O backend recusa (409) vinheria
 * offline ou ainda sem faixa; aqui os botões já ficam desabilitados nesses
 * estados, com o motivo escrito.
 */
import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { ATRIBUTOS } from '../lib/atributos.js';
import { Botao, Cartao, MensagemErro, Nota, Subtitulo } from './ui/index.js';

const BLOQUEIO = {
  offline: 'Vinheria offline: os comandos voltam quando ela reconectar.',
  configurando: 'Vinheria aguardando a faixa (configurando).',
};

// Quanto tempo o "Comando enviado." fica na tela
const AVISO_MS = 4000;

export default function PainelComandos({ deviceId, status }) {
  const enviar = useAcao(api.sendCommand);
  const [ativo, setAtivo] = useState(null);
  const [enviado, setEnviado] = useState(false);
  const bloqueio = Object.hasOwn(BLOQUEIO, status) ? BLOQUEIO[status] : null;

  useEffect(() => {
    if (!enviado) {
      return undefined;
    }
    const timer = setTimeout(() => setEnviado(false), AVISO_MS);
    return () => clearTimeout(timer);
  }, [enviado]);

  async function disparar(comando) {
    setAtivo(comando);
    setEnviado(false);
    const resultado = await enviar.executar(deviceId, comando);
    setAtivo(null);
    if (resultado.ok) {
      setEnviado(true);
    }
  }

  const desabilitado = bloqueio !== null || ativo !== null;
  return (
    <Cartao larg={2}>
      <Subtitulo>Alerta manual</Subtitulo>
      {bloqueio && <Nota>{bloqueio}</Nota>}
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {ATRIBUTOS.map(({ comando, botao }) => (
          <Botao
            key={comando}
            variante="secundario"
            disabled={desabilitado}
            carregando={ativo === comando}
            textoCarregando="Enviando…"
            onClick={() => disparar(comando)}
          >
            {botao}
          </Botao>
        ))}
      </div>
      <Botao
        variante="perigo"
        className="mt-3 w-full"
        disabled={desabilitado}
        carregando={ativo === 'alert_off'}
        textoCarregando="Enviando…"
        onClick={() => disparar('alert_off')}
      >
        Desligar alerta
      </Botao>
      <div className="mt-3">
        <MensagemErro erro={enviar.erro} />
      </div>
      {enviado && (
        <p role="status" className="text-sm text-ok">
          Comando enviado.
        </p>
      )}
    </Cartao>
  );
}
