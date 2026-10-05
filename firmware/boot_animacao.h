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

// Cada figura ocupa 2x1 caracteres (10x8 pixels): metade esquerda e direita.
// A uva fica na linha 0 (slots 0 e 1) e a taça na linha 1 (slots 2 e 3),
// centralizadas nas colunas 7 e 8 do display.
const uint8_t COLUNA_FIGURA = 7;

// Cacho de uva cheio: talo no alto, três uvas, duas e uma, afunilando.
// A última linha fica livre para a gota cair nos próximos quadros.
const byte UVA_CHEIA_ESQ[8] = {B00001, B01101, B01101, B00110, B00110, B00001, B00001, B00000};
const byte UVA_CHEIA_DIR[8] = {B10000, B10110, B10110, B01100, B01100, B10000, B10000, B00000};

// Taça vazia: só o contorno (borda, bojo, haste e base).
const byte TACA_VAZIA_ESQ[8] = {B10000, B10000, B10000, B01000, B00111, B00001, B00001, B01111};
const byte TACA_VAZIA_DIR[8] = {B00001, B00001, B00001, B00010, B11100, B10000, B10000, B11110};

// Redefine os slots 0 a 3 com os bitmaps dados. Quem chama deve usar
// setCursor() antes de escrever: o createChar deixa o cursor na CGRAM.
void definirFiguras(LiquidCrystal_I2C& lcd, const byte* uvaEsq, const byte* uvaDir,
                    const byte* tacaEsq, const byte* tacaDir) {
  lcd.createChar(0, (uint8_t*)uvaEsq);
  lcd.createChar(1, (uint8_t*)uvaDir);
  lcd.createChar(2, (uint8_t*)tacaEsq);
  lcd.createChar(3, (uint8_t*)tacaDir);
}

// Escreve uva (linha 0) e taça (linha 1) nas colunas centrais.
void desenharFiguras(LiquidCrystal_I2C& lcd) {
  lcd.setCursor(COLUNA_FIGURA, 0);
  lcd.write(byte(0));
  lcd.write(byte(1));
  lcd.setCursor(COLUNA_FIGURA, 1);
  lcd.write(byte(2));
  lcd.write(byte(3));
}

// Executa a animação. Usa delay() de propósito: roda uma única vez no
// setup(), antes do loop(), então não afeta os padrões não bloqueantes de
// LED e buzzer. Por enquanto mostra só o primeiro quadro (uva cheia e taça
// vazia); os demais quadros entram no próximo passo.
void animacaoBoot(LiquidCrystal_I2C& lcd) {
  lcd.clear();
  definirFiguras(lcd, UVA_CHEIA_ESQ, UVA_CHEIA_DIR, TACA_VAZIA_ESQ, TACA_VAZIA_DIR);
  desenharFiguras(lcd);
  delay(2000);
}

#endif
