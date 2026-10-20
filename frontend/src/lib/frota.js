/**
 * Contas sobre o retrato da frota (GET /api/fleet) para a Visão geral:
 * quantas vinherias em cada status, em que ordem mostrar os cartões e o
 * texto de "visto há".
 */

// Quem precisa de atenção aparece primeiro; status desconhecido vai para o fim
const ORDEM = { alerta: 0, offline: 1, configurando: 2, ok: 3 };

function peso(status) {
  return Object.hasOwn(ORDEM, status) ? ORDEM[status] : 4;
}

/** Total e quantidade por status. Com frota null, tudo zero. */
export function resumoFrota(frota) {
  const resumo = { total: 0, ok: 0, alerta: 0, offline: 0, configurando: 0 };
  for (const vinheria of frota?.vinherias ?? []) {
    resumo.total += 1;
    if (Object.hasOwn(ORDEM, vinheria.status)) {
      resumo[vinheria.status] += 1;
    }
  }
  return resumo;
}

/** Nova lista ordenada por status (alerta, offline, configurando, ok) e depois por device_id. */
export function ordenarFrota(vinherias) {
  return [...vinherias].sort(
    (a, b) => peso(a.status) - peso(b.status) || a.device_id.localeCompare(b.device_id),
  );
}

/** Tempo desde a última leitura em texto curto. */
export function vistoHa(segundos) {
  if (segundos === null || segundos === undefined) {
    return 'sem leitura';
  }
  if (segundos < 5) {
    return 'agora';
  }
  if (segundos < 60) {
    return `há ${segundos} s`;
  }
  if (segundos < 3600) {
    return `há ${Math.floor(segundos / 60)} min`;
  }
  return `há ${Math.floor(segundos / 3600)} h`;
}

/** Rodapé de uma vinheria: "EC2 fora" quando a queda é da EC2; senão o vistoHa. */
export function textoVisto(vinheria) {
  return vinheria.offline_reason === 'fiware' ? 'EC2 fora' : vistoHa(vinheria.seconds_since);
}
