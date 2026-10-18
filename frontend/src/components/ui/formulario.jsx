/**
 * Peças de formulário do design system: campo com rótulo, botão com
 * variantes e botão só de ícone. Todos têm pelo menos 44 px de altura,
 * para o toque no celular. Em React 19, `ref` chega como prop comum e
 * vai junto do `...props` para o elemento nativo.
 */

// Cores de cada variante do Botao (classes inteiras para o Tailwind achar)
const VARIANTES = {
  primario: 'border-bordo bg-bordo text-papel hover:bg-vinho hover:border-vinho',
  secundario: 'border-bordo bg-transparent text-bordo hover:bg-bordo/8',
  perigo: 'border-alerta bg-transparent text-alerta hover:bg-alerta/8',
};

/** Campo de texto com o rótulo em caixa alta em cima; as demais props vão para o <input>. */
export function Campo({ rotulo, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-overline uppercase text-taupe">{rotulo}</span>
      <input
        className="min-h-11 rounded border border-linha bg-papel px-3 text-vinho placeholder:text-taupe/70 focus:border-bordo"
        {...props}
      />
    </label>
  );
}

/** Botão padrão. Com `carregando`, fica desabilitado e mostra `textoCarregando`. */
export function Botao({
  variante = 'primario',
  carregando = false,
  textoCarregando,
  disabled,
  type = 'button',
  className = '',
  children,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || carregando}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded border px-4 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTES[variante]} ${className}`}
      {...props}
    >
      {carregando && textoCarregando ? textoCarregando : children}
    </button>
  );
}

/** Botão só de ícone (Lucide), redondo, 44 px; `rotulo` vira o nome acessível. */
export function BotaoIcone({ icone: Icone, rotulo, className = '', ...props }) {
  return (
    <button
      type="button"
      aria-label={rotulo}
      title={rotulo}
      className={`inline-flex size-11 shrink-0 items-center justify-center rounded-full text-taupe transition-colors duration-150 hover:bg-bordo/8 hover:text-bordo ${className}`}
      {...props}
    >
      <Icone size={20} strokeWidth={1.5} aria-hidden="true" />
    </button>
  );
}
