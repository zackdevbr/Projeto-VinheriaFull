/*
 * Smart Solutions — animação de boot do LCD 16x2.
 *
 * Mostra um cacho de uva sendo espremido e enchendo uma taça de vinho. O
 * display HD44780 guarda só 8 caracteres customizados, e os slots 0 a 3 são
 * usados pelos ícones do carrossel (taça, gota, sol). Por isso a animação
 * redefine esses slots a cada quadro e o .ino recarrega os ícones depois.
 */

#ifndef BOOT_ANIMACAO_H
#define BOOT_ANIMACAO_H

#include <LiquidCrystal_I2C.h>

// Executa a animação completa. Usa delay() de propósito: roda uma única vez
// no setup(), antes do loop(), então não afeta os padrões não bloqueantes de
// LED e buzzer.
void animacaoBoot(LiquidCrystal_I2C& lcd) {
  // Os quadros entram nos próximos passos.
}

#endif
