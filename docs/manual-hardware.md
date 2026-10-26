# Manual de hardware — Smart Solutions

Este manual descreve o circuito de uma vinheria: o que comprar, como ligar cada peça no ESP32, o que significam o LED e o buzzer e como gravar o firmware em uma placa física. O mesmo circuito é simulado no Wokwi (`firmware/diagram.json`).

## 1. Lista de materiais

| Qtd | Peça | Observação |
|---|---|---|
| 1 | ESP32 DevKit V1 (30 ou 38 pinos) | Wi-Fi 2,4 GHz |
| 1 | Protoboard (meia, 400 pontos) | |
| 1 | Sensor DHT-11 (ou DHT-22) | Temperatura e umidade; ver seção 6 |
| 1 | Resistor de 10 kΩ | Pull-up do dado do DHT |
| 1 | LDR (fotoresistor) | Luminosidade |
| 1 | Resistor de 10 kΩ | Divisor de tensão do LDR |
| 1 | LED RGB (catodo comum) | LED de status |
| 3 | Resistor de 220 Ω | Um por cor do LED RGB |
| 1 | Buzzer passivo | Alerta sonoro; o firmware gera o tom de 2 kHz com `tone()` |
| 1 | Display OLED SSD1306 128x64 I2C | Endereço `0x3C` |
| — | Jumpers macho-macho | |
| 1 | Cabo micro-USB | Alimentação e gravação |

## 2. Pinagem

| Componente | Pino do ESP32 | Função |
|---|---|---|
| DHT-11 (DHT-22 no Wokwi) | GPIO 4 | Dado de temperatura e umidade |
| LDR (divisor de tensão) | GPIO 34 (ADC) | Luminosidade, mapeada de 0 a 100 % |
| Buzzer | GPIO 5 | Alerta sonoro, tom de 2 kHz |
| LED RGB — vermelho | GPIO 25 | Status e alerta |
| LED RGB — verde | GPIO 26 | Status |
| LED RGB — azul | GPIO 27 | Reservado; o firmware mantém apagado (amarelo = vermelho + verde) |
| OLED SSD1306 — SDA | GPIO 21 | I2C |
| OLED SSD1306 — SCL | GPIO 22 | I2C |

Se o OLED não responder no boot, o firmware segue funcionando sem display.

## 3. Montagem

Ligações, uma por uma (GND de tudo é comum):

1. **DHT**: pino VCC em 3V3; pino GND em GND; pino de dado em GPIO 4. Resistor de 10 kΩ entre o dado e o 3V3.
2. **LDR**: um terminal do LDR em 3V3; o outro terminal no GPIO 34. Resistor de 10 kΩ entre o GPIO 34 e o GND. O GPIO 34 lê o ponto entre o LDR e o resistor.
3. **LED RGB**: catodo comum em GND. Cada ânodo passa por um resistor de 220 Ω: vermelho no GPIO 25, verde no GPIO 26, azul no GPIO 27.
4. **Buzzer**: terminal positivo no GPIO 5; negativo em GND.
5. **OLED**: VCC em 3V3; GND em GND; SDA no GPIO 21; SCL no GPIO 22.

Circuito montado no Wokwi:

<!-- Adicionar o print em docs/img/wokwi-circuito.png e descomentar a linha abaixo. -->
<!-- ![Circuito no Wokwi](img/wokwi-circuito.png) -->

Peças usadas no `firmware/diagram.json`: esp32-devkit-v1, breadboard-half, dht22 com resistor, photoresistor-sensor, rgb-led com três resistores, buzzer e ssd1306.

## 4. Cuidados

- **Pull-up do DHT:** resistor de 10 kΩ entre o dado e o 3V3. Sem ele a leitura falha de forma intermitente.
- **Divisor de tensão do LDR:** resistor de 10 kΩ para o GND. Sem ele o GPIO 34 fica flutuando.
- **LED RGB:** um resistor de 220 Ω por cor. Nunca ligue o LED direto no pino.
- **OLED:** alimente em 3,3 V, não em 5 V.
- O GPIO 34 só serve como entrada; não ligue nada que precise de saída nele.

## 5. LED RGB e buzzer

| Cor do LED | Significado |
|---|---|
| Verde | Conectado e configurado (a faixa ideal já chegou) |
| Amarelo | Conectando, sem Wi-Fi ou MQTT, ou aguardando o primeiro `set_limits` |
| Vermelho piscando | Alerta ativo |

| Anomalia | Comando | LED vermelho | Buzzer |
|---|---|---|---|
| Temperatura | `blink_temp` | pisca a cada 500 ms | 2 bipes curtos a cada 2 s |
| Umidade | `blink_hum` | pisca a cada 250 ms | 1 bipe longo a cada 3 s |
| Luminosidade | `blink_lux` | pisca a cada 125 ms | 3 bipes rápidos a cada 2 s |
| — | `alert_off` | volta ao verde | silêncio |

Os padrões usam uma máquina de estado com `millis()`, sem `delay()`: o ESP32 continua lendo e publicando enquanto alerta.

## 6. DHT-11 versus DHT-22

| | DHT-11 | DHT-22 |
|---|---|---|
| Temperatura | 0 a 50 °C, ±2 °C | −40 a 80 °C, ±0,5 °C |
| Umidade | 20 a 80 %, ±5 % | 0 a 100 %, ±2 % |
| Intervalo mínimo entre leituras | 1 s | 2 s |

O hardware real da vinheria usa o DHT-11. O Wokwi não tem DHT-11, então a simulação usa o DHT-22. A pinagem é a mesma; para trocar, edite `DHTTYPE` no bloco `CONFIGURAÇÃO DESTA INSTÂNCIA` do `firmware/vinheria_full.ino`:

```cpp
#define DHTTYPE DHT11   // hardware real
#define DHTTYPE DHT22   // simulação no Wokwi
```

O firmware lê a cada 2 s, dentro do limite dos dois modelos.

## 7. Gravar no ESP32 físico (Arduino IDE)

1. Instale a Arduino IDE e o pacote de placas **esp32** (Gerenciador de Placas).
2. Selecione a placa **ESP32 Dev Module** e a porta COM do cabo.
3. Instale, pelo Gerenciador de Bibliotecas, as bibliotecas de `firmware/libraries.txt`: PubSubClient, DHT sensor library, Adafruit Unified Sensor, Adafruit GFX Library e Adafruit SSD1306.
4. Abra `firmware/vinheria_full.ino` (os arquivos `.h` da mesma pasta abrem junto).
5. No bloco `CONFIGURAÇÃO DESTA INSTÂNCIA`, ajuste `ID_DEVICE`, `SSID`, `PASSWORD`, `BROKER_MQTT` (IP elástico da EC2) e `DHTTYPE`.
6. Grave. No monitor serial (115200) acompanhe a conexão; o LED fica amarelo até o `set_limits` chegar e então passa a verde.

O device precisa estar cadastrado no painel (ou provisionado pelo Postman) antes de o ESP32 enviar dados. Ver [`manual-software.md`](manual-software.md).
