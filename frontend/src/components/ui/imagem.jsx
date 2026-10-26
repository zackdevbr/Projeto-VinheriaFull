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
 * Imagens do painel. Nesta fase as fotos ainda não chegaram (spec R8):
 * cada lugar de imagem é um espaço reservado com proporção fixa, então a
 * foto real entra só passando `src` e `alt`, sem a página "pular".
 */

// Proporção de cada uso (classes inteiras para o Tailwind achar)
const PROPORCAO = {
  quadrada: 'aspect-square',
  '4/3': 'aspect-[4/3]',
  heroi: 'aspect-[4/3] md:aspect-[21/9]',
};

/** Logo da Smart Solutions; sem imagem, o nome em serifa bordô faz o papel de logo. */
export function Logo({ src }) {
  if (src) {
    return <img src={src} alt="Smart Solutions" className="h-8 w-auto" />;
  }
  return <span className="font-display text-xl whitespace-nowrap text-bordo">Smart Solutions</span>;
}

/** Imagem com proporção fixa; sem `src`, desenha um gradiente da marca com o `rotulo` no canto. */
export function ImagemReservada({ proporcao = '4/3', rotulo, src, alt = '', className = '' }) {
  if (src) {
    return <img src={src} alt={alt} loading="lazy" className={`w-full object-cover ${PROPORCAO[proporcao]} ${className}`} />;
  }
  return (
    <div
      role="img"
      aria-label={rotulo}
      className={`flex w-full items-start justify-end bg-linear-to-br from-bordo via-rose to-creme p-3 ${PROPORCAO[proporcao]} ${className}`}
    >
      <span className="text-overline uppercase text-papel/80">{rotulo}</span>
    </div>
  );
}

/** Herói da Visão geral (referência A): imagem larga com título display por cima e véu escuro para leitura. */
export function Heroi({ titulo, subtitulo, imagem }) {
  return (
    <section className="relative mb-8 animate-entrar overflow-hidden rounded-2xl shadow-media">
      <ImagemReservada proporcao="heroi" rotulo="imagem do vinhedo" src={imagem} alt="" />
      <div className="absolute inset-0 flex flex-col justify-end bg-linear-to-t from-vinho/85 via-bordo/40 to-transparent p-5 md:p-10">
        <h1 className="font-display text-display text-papel">{titulo}</h1>
        <p className="mt-2 max-w-md text-papel/90">{subtitulo}</p>
      </div>
    </section>
  );
}
