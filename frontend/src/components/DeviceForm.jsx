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
 * Formulário de cadastro de vinheria (RF01 e RF06): device_id (vinheria00N,
 * igual ao ID_DEVICE do firmware), nome, cidade e a faixa ideal inicial
 * (já preenchida com a faixa padrão). Valida tudo no navegador, cadastra
 * (POST /api/devices, que provisiona no FIWARE e pode levar alguns
 * segundos) e em seguida grava a faixa (PUT .../triggers). Se a faixa
 * falhar depois do cadastro, a vinheria continua cadastrada com a faixa
 * padrão e a tela avisa para ajustar no detalhe.
 */
import { useState } from 'react';
import { api } from '../api/client.js';
import { FAIXA_PADRAO } from '../constants.js';
import { useAcao } from '../hooks/useAcao.js';
import { camposDaFaixa, validarFaixa } from '../lib/faixa.js';
import { validarCadastro } from '../lib/validation.js';
import CamposFaixa from './CamposFaixa.jsx';
import { Botao, Campo, MensagemErro, Overline } from './ui/index.js';

const VAZIO = { device_id: '', name: '', city: '' };

// Os três campos do cadastro: [name do input, rótulo, exemplo, tamanho máximo]
const CAMPOS = [
  ['device_id', 'Id do dispositivo', 'vinheria003', 11],
  ['name', 'Nome', 'Vinheria Recife', 60],
  ['city', 'Cidade', 'Recife', 60],
];

/**
 * Cadastra a vinheria e grava a faixa. Só o cadastro propaga erro; falha ao
 * salvar a faixa vira `avisoFaixa`, porque a vinheria já existe.
 */
async function cadastrarComFaixa(dados, faixa) {
  const device = await api.createDevice(dados);
  try {
    const salva = await api.saveTriggers(device.device_id, faixa);
    return { device, sync: salva.device_sync, avisoFaixa: null };
  } catch (falha) {
    return { device, sync: null, avisoFaixa: falha.message };
  }
}

/** Texto do resultado de um cadastro bem-sucedido. */
function mensagemFinal({ sync, avisoFaixa }) {
  if (avisoFaixa) {
    return {
      alerta: true,
      texto: `Vinheria cadastrada, mas a faixa não foi salva: ${avisoFaixa}. Ajuste no detalhe da vinheria.`,
    };
  }
  if (sync === 'enviado') {
    return { alerta: false, texto: 'Vinheria cadastrada e faixa enviada ao ESP32.' };
  }
  return { alerta: false, texto: 'Vinheria cadastrada. O ESP32 recebe a faixa quando ficar online.' };
}

export default function DeviceForm({ onCreated }) {
  const [campos, setCampos] = useState(VAZIO);
  const [faixa, setFaixa] = useState(() => camposDaFaixa(FAIXA_PADRAO));
  const [errosFaixa, setErrosFaixa] = useState({});
  const [final, setFinal] = useState(null);
  const cadastrar = useAcao(cadastrarComFaixa);

  function alterar(evento) {
    const { name, value } = evento.target;
    setCampos((atuais) => ({ ...atuais, [name]: value }));
  }

  function alterarFaixa(chave, limite, valor) {
    setFaixa((atuais) => ({ ...atuais, [chave]: { ...atuais[chave], [limite]: valor } }));
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    setFinal(null);
    const { dados, erro: invalido } = validarCadastro(campos);
    const { dados: faixaValida, erros } = validarFaixa(faixa);
    setErrosFaixa(erros);
    if (invalido) {
      cadastrar.setErro(invalido);
      return;
    }
    if (!faixaValida) {
      cadastrar.setErro(null);
      return;
    }
    const resultado = await cadastrar.executar(dados, faixaValida);
    if (resultado.ok) {
      setCampos(VAZIO);
      setFaixa(camposDaFaixa(FAIXA_PADRAO));
      setFinal(mensagemFinal(resultado.valor));
      await onCreated(resultado.valor.device);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={aoEnviar} noValidate>
      {CAMPOS.map(([nome, rotulo, exemplo, maximo]) => (
        <Campo
          key={nome}
          rotulo={rotulo}
          name={nome}
          value={campos[nome]}
          onChange={alterar}
          placeholder={exemplo}
          maxLength={maximo}
        />
      ))}
      <div className="border-t border-linha pt-4">
        <Overline>Faixa ideal</Overline>
        <p className="mb-3 mt-1 text-sm text-taupe">Limites dos alertas e referência do score. Pode ajustar depois.</p>
        <CamposFaixa campos={faixa} aoMudar={alterarFaixa} erros={errosFaixa} />
      </div>
      <MensagemErro erro={cadastrar.erro} />
      {final && (
        <p role={final.alerta ? 'alert' : 'status'} className={`text-sm ${final.alerta ? 'text-alerta' : 'text-ok'}`}>
          {final.texto}
        </p>
      )}
      <Botao type="submit" className="w-full" carregando={cadastrar.executando} textoCarregando="Provisionando no FIWARE…">
        Cadastrar vinheria
      </Botao>
    </form>
  );
}
