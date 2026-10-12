/**
 * Componentes básicos reaproveitados em todas as telas: título, campo com
 * rótulo, botão, mensagem de erro, texto secundário e link para o detalhe
 * de uma vinheria. Eles concentram as classes Tailwind repetidas, então a
 * Task 5B troca o visual aqui, num lugar só. Antes de escrever um destes
 * elementos à mão numa tela, use o daqui (ou acrescente uma variação aqui).
 */
import { Link } from 'react-router-dom';

/** Título de página. */
export function Titulo({ children }) {
  return <h1 className="mb-4 text-xl font-semibold">{children}</h1>;
}

/** Campo de texto com o rótulo em cima; as demais props vão para o <input>. */
export function Campo({ rotulo, ...props }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {rotulo}
      <input className="rounded border border-gray-300 px-2 py-1" {...props} />
    </label>
  );
}

/** Botão padrão. Com `carregando`, fica desabilitado e mostra `textoCarregando`. */
export function Botao({ carregando = false, textoCarregando, disabled, type = 'button', children, ...props }) {
  return (
    <button
      type={type}
      disabled={disabled || carregando}
      className="rounded border border-gray-400 px-3 py-1 text-sm hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
      {...props}
    >
      {carregando && textoCarregando ? textoCarregando : children}
    </button>
  );
}

/** Mensagem de erro; não desenha nada quando `erro` está vazio. */
export function MensagemErro({ erro }) {
  if (!erro) {
    return null;
  }
  return (
    <p className="mb-2 basis-full text-sm text-red-700" role="alert">
      {erro}
    </p>
  );
}

/** Texto secundário: avisos, "Carregando…", lista vazia. */
export function Nota({ children }) {
  return <p className="text-gray-600">{children}</p>;
}

/** Link (React Router, sem recarregar) para o detalhe de uma vinheria. */
export function LinkVinheria({ deviceId, children }) {
  return (
    <Link to={`/vinherias/${deviceId}`} className="underline hover:text-gray-600">
      {children}
    </Link>
  );
}
