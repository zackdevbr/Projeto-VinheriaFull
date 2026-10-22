/*
 * Smart Solutions — animação de boot do OLED 128x64.
 *
 * Um cacho de seis uvas se desfaz de baixo para cima: cada uva cai do cacho,
 * rola pelo chão, salta para dentro de uma taça e a taça enche de vinho a cada
 * uva que entra. Tudo é desenhado com primitivas do Adafruit GFX (círculos,
 * linhas, triângulos), sem bitmaps.
 *
 * A cena é função do tempo decorrido: cada quadro é calculado a partir de
 * millis(), então a duração total fica fixa mesmo que o display demore para
 * atualizar. Os tempos de cada etapa ficam nas constantes abaixo, para ajuste.
 *
 * Layout (pixels):
 *   cacho = canto superior esquerdo, talo em x 24
 *   chão  = linha em y 62, onde as uvas rolam até x 82
 *   taça  = à direita, boca em y 34 (x 94 a 122), base em y 61
 */

#ifndef BOOT_ANIMACAO_H
#define BOOT_ANIMACAO_H

#include <Adafruit_SSD1306.h>
#include <math.h>

// --- Tempos (ms) ---
const unsigned long ANIM_ATRASO_INICIAL = 300;  // cacho parado antes da primeira uva soltar
const unsigned long ANIM_INTERVALO_UVAS = 450;  // diferença entre a saída de uma uva e a seguinte
const unsigned long ANIM_QUEDA = 350;           // uva caindo do cacho até o chão
const unsigned long ANIM_ROLAGEM = 900;         // uva rolando pelo chão
const unsigned long ANIM_SALTO = 300;           // uva saltando para dentro da taça
const unsigned long ANIM_FINAL = 600;           // taça cheia parada no fim
const int QTD_UVAS = 6;
// Total: 300 + 5*450 + (350+900+300) + 600 = 4700 ms (abaixo do limite de 5 s).
const unsigned long ANIM_DURACAO_UVA = ANIM_QUEDA + ANIM_ROLAGEM + ANIM_SALTO;
const unsigned long ANIM_TOTAL = ANIM_ATRASO_INICIAL + (QTD_UVAS - 1) * ANIM_INTERVALO_UVAS
                                 + ANIM_DURACAO_UVA + ANIM_FINAL;

// --- Geometria ---
const int UVA_RAIO = 4;
const int Y_CHAO = 62;                   // linha do chão
const int Y_UVA_NO_CHAO = Y_CHAO - UVA_RAIO - 1;
const int X_FIM_ROLAGEM = 82;            // onde a uva para de rolar e salta
const int X_TACA_CENTRO = 108;           // eixo da taça
const int Y_TACA_BOCA = 34;              // borda de cima da taça
const int Y_TACA_FUNDO = 50;             // fundo do bojo
const int ALTURA_VINHO_MAX = 15;         // linhas de vinho com a taça cheia

// Posição de cada uva no cacho, na ordem em que se soltam (de baixo para cima).
const int UVA_X[QTD_UVAS] = {24, 20, 28, 16, 24, 32};
const int UVA_Y[QTD_UVAS] = {34, 26, 26, 18, 18, 18};

// Talo e folha do cacho (ficam depois que as uvas saem).
void desenharTalo(Adafruit_SSD1306& oled) {
  oled.drawLine(24, 4, 24, 14, SSD1306_WHITE);
  oled.fillTriangle(24, 8, 33, 4, 30, 11, SSD1306_WHITE);
}

// Contorno da taça: boca, duas paredes inclinadas, fundo, haste e base.
void desenharTaca(Adafruit_SSD1306& oled) {
  oled.drawFastHLine(94, Y_TACA_BOCA, 29, SSD1306_WHITE);
  oled.drawLine(94, Y_TACA_BOCA, 102, Y_TACA_FUNDO, SSD1306_WHITE);
  oled.drawLine(122, Y_TACA_BOCA, 114, Y_TACA_FUNDO, SSD1306_WHITE);
  oled.drawFastHLine(102, Y_TACA_FUNDO, 13, SSD1306_WHITE);
  oled.drawFastVLine(X_TACA_CENTRO, Y_TACA_FUNDO, 10, SSD1306_WHITE);
  oled.drawFastHLine(100, 60, 17, SSD1306_WHITE);
}

// Preenche o vinho de baixo para cima; cada linha acompanha a inclinação da parede.
void desenharVinho(Adafruit_SSD1306& oled, int linhas) {
  for (int r = 0; r < linhas; r++) {
    int y = Y_TACA_FUNDO - 1 - r;
    int esquerda = 94 + (y - Y_TACA_BOCA) / 2;
    int direita = 122 - (y - Y_TACA_BOCA) / 2;
    oled.drawFastHLine(esquerda + 1, y, direita - esquerda - 1, SSD1306_WHITE);
  }
}

// Uva com um ponto preto que gira com a posição, para parecer que rola.
void desenharUva(Adafruit_SSD1306& oled, int x, int y, float angulo) {
  oled.fillCircle(x, y, UVA_RAIO, SSD1306_WHITE);
  oled.drawPixel(x + (int)(2 * cosf(angulo)), y + (int)(2 * sinf(angulo)), SSD1306_BLACK);
}

// Desenha a cena no instante t (ms desde o início da animação).
void desenharQuadroBoot(Adafruit_SSD1306& oled, unsigned long t) {
  oled.clearDisplay();
  oled.drawFastHLine(0, Y_CHAO, 128, SSD1306_WHITE);
  desenharTalo(oled);
  desenharTaca(oled);

  int uvasNaTaca = 0;
  for (int i = 0; i < QTD_UVAS; i++) {
    long inicio = ANIM_ATRASO_INICIAL + (long)i * ANIM_INTERVALO_UVAS;
    long u = (long)t - inicio; // tempo desde que esta uva se soltou

    if (u < 0) {
      desenharUva(oled, UVA_X[i], UVA_Y[i], 0); // ainda no cacho
    } else if (u < (long)ANIM_QUEDA) {
      float f = (float)u / ANIM_QUEDA;           // queda acelerada pela gravidade
      desenharUva(oled, UVA_X[i], UVA_Y[i] + (int)((Y_UVA_NO_CHAO - UVA_Y[i]) * f * f), 0);
    } else if (u < (long)(ANIM_QUEDA + ANIM_ROLAGEM)) {
      float f = (float)(u - ANIM_QUEDA) / ANIM_ROLAGEM;
      int x = UVA_X[i] + (int)((X_FIM_ROLAGEM - UVA_X[i]) * f);
      desenharUva(oled, x, Y_UVA_NO_CHAO, x / 4.0f);
    } else if (u < (long)ANIM_DURACAO_UVA) {
      float f = (float)(u - ANIM_QUEDA - ANIM_ROLAGEM) / ANIM_SALTO;
      int x = X_FIM_ROLAGEM + (int)((X_TACA_CENTRO - X_FIM_ROLAGEM) * f);
      int y = Y_UVA_NO_CHAO - (int)(36 * sqrtf(f)); // sobe rápido e passa por cima da borda
      desenharUva(oled, x, y, x / 4.0f);
    } else {
      uvasNaTaca++;
    }
  }
  desenharVinho(oled, uvasNaTaca * ALTURA_VINHO_MAX / QTD_UVAS);
  oled.display();
}

// Executa a animação inteira. Usa o relógio em vez de delay(), então a duração
// não depende de quanto tempo cada atualização do display leva. Roda uma única
// vez no setup(), antes do loop(), sem afetar os padrões de LED e buzzer.
void animacaoBoot(Adafruit_SSD1306& oled) {
  unsigned long inicio = millis();
  unsigned long t;
  while ((t = millis() - inicio) < ANIM_TOTAL) {
    desenharQuadroBoot(oled, t);
  }
}

#endif
