/**
 * Peças de texto do design system: título de página, texto secundário,
 * mensagem de erro e links internos. Antes de escrever um destes à mão
 * numa tela, use o daqui (ou acrescente uma variação aqui).
 */
import { Link } from 'react-router-dom';

/** Título de página. */
export function Titulo({ children }) {
  return <h1 className="mb-4 text-xl font-semibold">{children}</h1>;
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
