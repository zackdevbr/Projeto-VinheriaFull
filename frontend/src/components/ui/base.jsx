/**
 * Peças de texto do design system: rótulo em caixa alta (Overline), título
 * e subtítulo em serifa bordô, texto secundário, mensagem de erro e links
 * internos. Antes de escrever um destes à mão numa tela, use o daqui.
 */
import { CircleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';

/** Rótulo curto em caixa alta espaçada. `icone` é um componente Lucide; `invertido` para fundo bordô. */
export function Overline({ icone: Icone, invertido = false, children }) {
  const cor = invertido ? 'text-papel/80' : 'text-taupe';
  return (
    <p className={`flex items-center gap-1.5 text-overline uppercase ${cor}`}>
      {Icone && <Icone size={14} strokeWidth={1.5} aria-hidden="true" />}
      {children}
    </p>
  );
}

/** Título de página em serifa bordô, com `overline` opcional acima. */
export function Titulo({ overline, children }) {
  return (
    <div className="mb-6">
      {overline && <Overline>{overline}</Overline>}
      <h1 className="mt-1 font-display text-titulo text-bordo">{children}</h1>
    </div>
  );
}

/** Subtítulo de seção ou de cartão. */
export function Subtitulo({ children }) {
  return <h2 className="mb-4 font-display text-subtitulo text-bordo">{children}</h2>;
}

/** Texto secundário: avisos, "Carregando…". */
export function Nota({ children }) {
  return <p className="text-taupe">{children}</p>;
}

/** Mensagem de erro com ícone; não desenha nada quando `erro` está vazio. */
export function MensagemErro({ erro }) {
  if (!erro) {
    return null;
  }
  return (
    <p className="mb-2 flex basis-full items-start gap-1.5 text-sm text-alerta" role="alert">
      <CircleAlert size={16} strokeWidth={1.5} className="mt-0.5 shrink-0" aria-hidden="true" />
      {erro}
    </p>
  );
}

/** Link interno (React Router, sem recarregar a página) no estilo da marca. */
export function LinkInterno({ to, children }) {
  return (
    <Link to={to} className="text-bordo underline-offset-4 hover:underline focus-visible:underline">
      {children}
    </Link>
  );
}

/** Link para o detalhe de uma vinheria. */
export function LinkVinheria({ deviceId, children }) {
  return <LinkInterno to={`/vinherias/${deviceId}`}>{children}</LinkInterno>;
}
