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

/*
 * Faixa ideal da vinheria recebida do backend pelo comando set_limits.
 *
 * Formato do valor: "tmin,tmax,hmin,hmax,lmin,lmax", separado por vírgula (o
 * Orion rejeita ; em valores de atributo), com decimais opcionais
 * (ex.: "12.5,18,50,70,0,30"). Funções puras: não usam o display, MQTT nem as
 * variáveis globais do .ino.
 */
#ifndef LIMITES_H
#define LIMITES_H

#include <Arduino.h>

// Faixa ideal dos três atributos (mínimo e máximo de cada)
struct Faixa {
  float tempMin, tempMax;
  float humMin, humMax;
  float luxMin, luxMax;
};

// Converte texto em número aceitando só sinal opcional, dígitos e no
// máximo um ponto decimal. Rejeita vazio, letras e "1.2.3" (o toFloat()
// da String aceitaria lixo e devolveria 0).
bool parseDecimal(String s, float &out) {
  s.trim();
  if (s.length() == 0) return false;
  int i = (s[0] == '-') ? 1 : 0;
  bool temDigito = false;
  bool temPonto = false;
  for (; i < (int)s.length(); i++) {
    if (isDigit(s[i])) {
      temDigito = true;
    } else if (s[i] == '.' && !temPonto) {
      temPonto = true;
    } else {
      return false;
    }
  }
  if (!temDigito) return false;
  out = s.toFloat();
  return true;
}

// Lê os 6 valores na ordem canônica. Só devolve true com exatamente 6
// números e mínimo < máximo em cada par; caso contrário não altera
// `faixa` (validação atômica: ou aplica tudo, ou nada).
bool parseFaixa(String args, Faixa &faixa) {
  float v[6];
  int inicio = 0;
  for (int i = 0; i < 6; i++) {
    int fim = args.indexOf(',', inicio);
    if (i < 5 && fim < 0) return false;   // faltam campos
    if (i == 5 && fim >= 0) return false; // sobrou campo (7º valor)
    String campo = (fim >= 0) ? args.substring(inicio, fim) : args.substring(inicio);
    if (!parseDecimal(campo, v[i])) return false;
    inicio = fim + 1;
  }
  if (v[0] >= v[1] || v[2] >= v[3] || v[4] >= v[5]) return false;
  faixa = {v[0], v[1], v[2], v[3], v[4], v[5]};
  return true;
}

// Imprime um limite no display sem casas quando é inteiro (12) e com uma casa
// quando não é (12.5), para caber na linha do rodapé.
void imprimirLimite(Print &saida, float valor) {
  if (valor == (int)valor) {
    saida.print((int)valor);
  } else {
    saida.print(valor, 1);
  }
}

#endif
