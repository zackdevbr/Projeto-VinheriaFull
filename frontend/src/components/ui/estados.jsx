/**
 * Estados de tela sem conteúdo: vazio (nada a mostrar, com ação opcional)
 * e esqueleto (carregando), no lugar de spinner solto.
 */

/** Bloco central para lista vazia, tela em construção ou 404. `acao` é um botão ou link opcional. */
export function EstadoVazio({ titulo, texto, acao }) {
  return (
    <div className="flex animate-entrar flex-col items-center gap-3 rounded-2xl border border-dashed border-linha px-6 py-12 text-center">
      <p className="font-display text-subtitulo text-bordo">{titulo}</p>
      {texto && <p className="max-w-sm text-taupe">{texto}</p>}
      {acao}
    </div>
  );
}

/** Bloco de carregamento com brilho lento; a altura vem do `className` (ex.: "h-14"). */
export function Esqueleto({ className = '' }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-brilho rounded-lg bg-linear-to-r from-linha via-papel to-linha bg-size-[200%_100%] ${className}`}
    />
  );
}
