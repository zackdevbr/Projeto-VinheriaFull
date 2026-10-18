/**
 * Peças de formulário do design system: campo com rótulo e botões.
 */

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
