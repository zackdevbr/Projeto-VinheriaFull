/**
 * Formulário de cadastro de vinheria (RF01): device_id (vinheria00N, igual
 * ao ID_DEVICE do firmware), nome e cidade. Valida no navegador e chama
 * POST /api/devices, que provisiona no FIWARE e pode levar alguns segundos.
 */
import { useState } from 'react';
import { api } from '../api/client.js';
import { useAcao } from '../hooks/useAcao.js';
import { validarCadastro } from '../lib/validation.js';
import { Botao, Campo, MensagemErro } from './ui/index.js';

const VAZIO = { device_id: '', name: '', city: '' };

// Os três campos do cadastro: [name do input, rótulo, exemplo, tamanho máximo]
const CAMPOS = [
  ['device_id', 'Id do dispositivo', 'vinheria003', 11],
  ['name', 'Nome', 'Vinheria Recife', 60],
  ['city', 'Cidade', 'Recife', 60],
];

export default function DeviceForm({ onCreated }) {
  const [campos, setCampos] = useState(VAZIO);
  const cadastrar = useAcao(api.createDevice);

  function alterar(evento) {
    const { name, value } = evento.target;
    setCampos((atuais) => ({ ...atuais, [name]: value }));
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    const { dados, erro: invalido } = validarCadastro(campos);
    if (invalido) {
      cadastrar.setErro(invalido);
      return;
    }
    const resultado = await cadastrar.executar(dados);
    if (resultado.ok) {
      setCampos(VAZIO);
      await onCreated(resultado.valor);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={aoEnviar}>
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
      <MensagemErro erro={cadastrar.erro} />
      <Botao type="submit" className="w-full" carregando={cadastrar.executando} textoCarregando="Provisionando no FIWARE…">
        Cadastrar vinheria
      </Botao>
    </form>
  );
}
