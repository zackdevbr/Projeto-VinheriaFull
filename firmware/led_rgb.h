/*
 * LED RGB de status da vinheria (catodo comum, um resistor de 220 ohms por canal).
 *
 * A cor espelha o estado que o backend mostra no painel:
 *   verde    = conectado, com faixa recebida e sem alerta (ok)
 *   vermelho = alerta ativo, piscando no ritmo do sensor (alerta)
 *   amarelo  = conectando, sem Wi-Fi/MQTT ou aguardando o set_limits (offline/configurando)
 * Amarelo é vermelho + verde acesos juntos; o canal azul fica sempre desligado.
 */
#ifndef LED_RGB_H
#define LED_RGB_H

#include <Arduino.h>

#define LED_R 25
#define LED_G 26
#define LED_B 27

enum CorLed { COR_APAGADO, COR_VERDE, COR_AMARELO, COR_VERMELHO };

// Escolhe a cor do LED a partir do estado do dispositivo. Função pura.
// Prioridade: sem conexão (amarelo) > alerta (vermelho) > sem faixa (amarelo) > ok (verde).
// `faseAcesa` só importa no alerta: na fase apagada do pisca o LED fica desligado.
CorLed escolherCor(bool conectado, bool emAlerta, bool configurado, bool faseAcesa) {
  if (!conectado) return COR_AMARELO;
  if (emAlerta) return faseAcesa ? COR_VERMELHO : COR_APAGADO;
  if (!configurado) return COR_AMARELO;
  return COR_VERDE;
}

// Última cor escrita nos pinos; evita repetir digitalWrite a cada loop().
// Começa em um valor fora do enum para forçar a primeira escrita.
static int ultimaCorAplicada = -1;

// Liga os três pinos como saída e apaga o LED.
void iniciarLedRgb() {
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  digitalWrite(LED_R, LOW);
  digitalWrite(LED_G, LOW);
  digitalWrite(LED_B, LOW);
  ultimaCorAplicada = COR_APAGADO;
}

// Acende o LED na cor pedida, só escrevendo nos pinos quando a cor muda.
void aplicarCor(CorLed cor) {
  if ((int)cor == ultimaCorAplicada) return;
  ultimaCorAplicada = cor;
  digitalWrite(LED_R, (cor == COR_VERMELHO || cor == COR_AMARELO) ? HIGH : LOW);
  digitalWrite(LED_G, (cor == COR_VERDE || cor == COR_AMARELO) ? HIGH : LOW);
  digitalWrite(LED_B, LOW);
}

#endif
