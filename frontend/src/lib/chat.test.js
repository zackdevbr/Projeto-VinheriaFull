/** Testes da lógica pura do chat (Task 7A). */
import { describe, expect, it } from 'vitest';
import {
  MAX_HISTORICO,
  acoesIniciais,
  marcarFalha,
  montarHistorico,
  novaMensagem,
  podeDecidir,
  textoFeito,
  trocarEstadoAcao,
} from './chat.js';

describe('novaMensagem', () => {
  it('gera ids diferentes', () => {
    expect(novaMensagem('user', 'a').id).not.toBe(novaMensagem('user', 'a').id);
  });
});

describe('montarHistorico', () => {
  it('manda só turnos de usuário e modelo, sem erros nem perguntas que falharam', () => {
    const mensagens = [
      novaMensagem('user', 'oi'),
      novaMensagem('model', 'olá', { acoes: [] }),
      novaMensagem('user', 'caiu', { falhou: true }),
      novaMensagem('erro', 'Backend indisponível'),
    ];
    expect(montarHistorico(mensagens)).toEqual([
      { role: 'user', text: 'oi' },
      { role: 'model', text: 'olá' },
    ]);
  });

  it('corta nos últimos turnos', () => {
    const mensagens = Array.from({ length: 30 }, (_, i) => novaMensagem(i % 2 ? 'model' : 'user', `t${i}`));
    const historico = montarHistorico(mensagens);
    expect(historico).toHaveLength(MAX_HISTORICO);
    expect(historico.at(-1).text).toBe('t29');
  });
});

describe('marcarFalha', () => {
  it('marca só a mensagem indicada', () => {
    const [a, b] = [novaMensagem('user', 'a'), novaMensagem('user', 'b')];
    const resultado = marcarFalha([a, b], b.id);
    expect(resultado.map((m) => Boolean(m.falhou))).toEqual([false, true]);
    expect(a.falhou).toBeUndefined();
  });
});

describe('ações', () => {
  const acao = { kind: 'command', device_id: 'vinheria002', name: 'Vinheria Mineira', summary: 'Piscar', command: 'blink_lux' };

  it('nascem pendentes', () => {
    expect(acoesIniciais([acao])[0]).toMatchObject({ estado: 'pendente', detalhe: null });
    expect(acoesIniciais(undefined)).toEqual([]);
  });

  it('trocam de estado sem mexer nas outras mensagens', () => {
    const msg = novaMensagem('model', 'ok', { acoes: acoesIniciais([acao, acao]) });
    const outra = novaMensagem('user', 'x');
    const [m1, m2] = trocarEstadoAcao([msg, outra], msg.id, 1, 'feito', 'Comando enviado.');
    expect(m1.acoes.map((a) => a.estado)).toEqual(['pendente', 'feito']);
    expect(m1.acoes[1].detalhe).toBe('Comando enviado.');
    expect(m2).toBe(outra);
    expect(msg.acoes[1].estado).toBe('pendente');
  });

  it('só pendente e erro podem ser decididos (sem clique duplo em executando)', () => {
    expect(['pendente', 'executando', 'feito', 'cancelado', 'erro'].map(podeDecidir))
      .toEqual([true, false, false, false, true]);
  });

  it('descrevem o resultado', () => {
    expect(textoFeito(acao, null)).toBe('Comando enviado.');
    expect(textoFeito({ kind: 'limits' }, { device_sync: 'enviado' })).toBe('Faixa salva e enviada ao ESP32.');
    expect(textoFeito({ kind: 'limits' }, { device_sync: 'pendente' })).toBe('Faixa salva; o ESP32 recebe quando voltar.');
  });
});
