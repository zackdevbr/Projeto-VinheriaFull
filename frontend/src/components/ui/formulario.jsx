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

/** Campo de texto com o rótulo em caixa alta em cima; `erro` aparece embaixo; as demais props vão para o <input>. */
export function Campo({ rotulo, erro, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-overline uppercase text-taupe">{rotulo}</span>
      <input
        aria-invalid={erro ? true : undefined}
        className={`min-h-11 rounded border bg-papel px-3 text-vinho placeholder:text-taupe/70 focus:border-bordo ${erro ? 'border-alerta' : 'border-linha'}`}
        {...props}
      />
      {erro && <span className="text-xs text-alerta">{erro}</span>}
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

/** Lista de escolha com o mesmo visual do Campo; `opcoes` = [{ valor, rotulo }]. */
export function Seletor({ rotulo, opcoes, ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-overline uppercase text-taupe">{rotulo}</span>
      <select className="min-h-11 rounded border border-linha bg-papel px-3 text-vinho focus:border-bordo" {...props}>
        {opcoes.map((opcao) => (
          <option key={opcao.valor} value={opcao.valor}>
            {opcao.rotulo}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Botões lado a lado em que só um fica ativo (aria-pressed), como 20 | 50 | 100. */
export function BotoesSegmentados({ rotulo, opcoes, valor, aoMudar }) {
  return (
    <div role="group" aria-label={rotulo} className="inline-flex self-start rounded border border-linha bg-papel p-0.5">
      {opcoes.map((opcao) => {
        const ativo = opcao.valor === valor;
        return (
          <button
            key={opcao.valor}
            type="button"
            aria-pressed={ativo}
            onClick={() => aoMudar(opcao.valor)}
            className={`min-h-11 min-w-11 rounded-sm px-3 text-sm font-medium transition-colors duration-150 ${ativo ? 'bg-bordo text-papel' : 'text-taupe hover:text-bordo'}`}
          >
            {opcao.rotulo}
          </button>
        );
      })}
    </div>
  );
}
