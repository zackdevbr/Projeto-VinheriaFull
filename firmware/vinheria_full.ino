/*
 * Smart Solutions — monitoramento de vinherias (firmware ESP32)
 *
 * Lê temperatura, umidade (DHT) e luminosidade (LDR), publica no FIWARE por
 * MQTT em UltraLight 2.0, executa comandos de alerta (LED RGB e buzzer) e
 * mostra os dados num OLED 128x64. O ID da vinheria e a rede ficam no bloco
 * "CONFIGURAÇÃO DESTA INSTÂNCIA" abaixo.
 *
 * Nasce sem faixa ideal: mostra "Configure o dispositivo" e recusa alertas
 * até o backend mandar o set_limits.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <time.h>
#include "boot_animacao.h"
#include "limites.h"
#include "led_rgb.h"

// ===== CONFIGURAÇÃO DESTA INSTÂNCIA =====
// Único bloco a editar ao rodar o firmware em outro computador ou ESP32.
// Cada vinheria precisa de um ID_DEVICE próprio (vinheria001, vinheria002...)
// e do device correspondente já provisionado no FIWARE.

// Identificação do device (nomes canônicos do plano FIWARE).
const char* ID_DEVICE = "vinheria001";

// Credenciais de rede (Wokwi usa rede aberta "Wokwi-GUEST").
const char* SSID = "Wokwi-GUEST";
const char* PASSWORD = "";

// Broker MQTT (Mosquitto do FIWARE na EC2). A EC2 usa IP elástico (fixo entre
// liga e desliga), então o IP pode ficar aqui.
const char* BROKER_MQTT = "3.215.3.216";
const int BROKER_PORT = 1883;

// Sensor de temperatura/umidade. Simulação no Wokwi usa DHT22 (não tem DHT11
// no simulador); hardware real da vinheria usa DHT11. Para trocar: mudar
// DHTTYPE para DHT11, pinagem não muda.
#define DHTTYPE DHT22
// ===== FIM DA CONFIGURAÇÃO DESTA INSTÂNCIA =====

// --- Sensor de temperatura/umidade (pino) ---
#define DHTPIN 4
DHT dht(DHTPIN, DHTTYPE);

// --- LDR (luminosidade) ---
// Leitura ADC 0-4095 (12 bits do ESP32) convertida para percentual 0-100%.
#define LDRPIN 34

// --- Buzzer de alerta (o LED RGB de status e seus pinos ficam em led_rgb.h) ---
#define BUZZER_PIN 5

// --- Display OLED SSD1306 128x64 I2C (endereço 0x3C, pinos SDA 21 e SCL 22) ---
#define LARGURA_OLED 128
#define ALTURA_OLED 64
Adafruit_SSD1306 oled(LARGURA_OLED, ALTURA_OLED, &Wire, -1);
bool oledOk = false; // false se o display não respondeu no setup(): o firmware segue sem ele

// --- Faixa ideal recebida do backend (comando set_limits) ---
// O ESP32 nasce SEM faixa: até o backend mandar o set_limits, o OLED mostra
// "Configure o dispositivo" e os comandos de alerta são recusados, para
// nenhum alerta disparar com parâmetros que não foram cadastrados. A faixa
// é só informativa no OLED (quem decide o alerta é o backend). `configurado`
// vai na telemetria (c|0 ou c|1): é por ele que o backend percebe que o
// ESP32 reiniciou e reenvia a faixa na hora.
Faixa faixa;
bool configurado = false;

// Flags por atributo: o OLED precisa saber se cada atributo está em alerta
// mesmo quando o alertMode (que só governa o padrão de LED/buzzer) está
// ocupado com outro atributo — duas anomalias podem estar ativas ao mesmo
// tempo. alert_off limpa as três de uma vez; quando uma anomalia normaliza
// e outra continua, o backend manda alert_off e em seguida o blink da que restou.
bool alertTemp = false;
bool alertHum = false;
bool alertLux = false;

// Últimas leituras válidas — usadas pelo publish MQTT e pelas telas do OLED.
// Começam em 0 porque o OLED só as exibe depois da primeira leitura válida.
float ultimaTemperatura = 0;
float ultimaUmidade = 0;
int ultimaLuminosidade = 0;

// Estado da máquina de alerta: qual anomalia está ativa agora (ou nenhuma).
enum AlertMode { ALERT_NONE, ALERT_TEMP, ALERT_HUM, ALERT_LUX };
AlertMode alertMode = ALERT_NONE;

// Ícones desenhados nos títulos das telas. Fica aqui no topo (antes da primeira
// função) porque o Arduino gera os protótipos das funções antes do resto do código.
enum Icone { ICONE_TACA, ICONE_GOTA, ICONE_SOL };
unsigned long alertCycleStart = 0; // referência de tempo do ciclo de buzzer atual

// --- Tópicos UltraLight 2.0 derivados do ID_DEVICE ---
// attrs: telemetria publicada pelo device
// cmd: comandos recebidos do backend/Orion
// cmdexe: confirmação (ack) de execução do comando
char topicAttrs[50];
char topicCmd[50];
char topicCmdExe[50];

WiFiClient espClient;
PubSubClient MQTT(espClient);

// Monta os tópicos a partir do ID_DEVICE (evita hardcode duplicado)
void montarTopicos() {
  snprintf(topicAttrs, sizeof(topicAttrs), "/TEF/%s/attrs", ID_DEVICE);
  snprintf(topicCmd, sizeof(topicCmd), "/TEF/%s/cmd", ID_DEVICE);
  snprintf(topicCmdExe, sizeof(topicCmdExe), "/TEF/%s/cmdexe", ID_DEVICE);
}

void conectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(100); // delay aceitável aqui: é só durante o handshake de boot, não é padrão de alerta
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi conectado, IP: ");
  Serial.println(WiFi.localIP());
}

// --- Relógio via NTP (substitui o RTC DS1307 do CP2) ---
#define FUSO_HORARIO_SEG (-3 * 3600) // UTC-3 (horário de Brasília, sem horário de verão)

void iniciarRelogio() {
  configTime(FUSO_HORARIO_SEG, 0, "pool.ntp.org");
}

// Escreve o texto centralizado na horizontal, na linha y, com o tamanho dado.
void centralizar(const String& texto, uint8_t tamanho, int16_t y) {
  int16_t x1, y1;
  uint16_t w, h;
  oled.setTextSize(tamanho);
  oled.getTextBounds(texto, 0, 0, &x1, &y1, &w, &h);
  oled.setCursor((LARGURA_OLED - w) / 2, y);
  oled.print(texto);
}

// Preenche dois dígitos com zero à esquerda, igual ao CP2.
String doisDigitos(int valor) {
  return (valor < 10 ? "0" : "") + String(valor);
}

// Desenha um ícone de 10x10 pixels com primitivas do GFX, a partir do canto
// superior esquerdo (x, y). Substitui os caracteres customizados do LCD.
void desenharIcone(Icone tipo, int16_t x, int16_t y) {
  switch (tipo) {
    case ICONE_TACA:
      oled.fillTriangle(x, y, x + 10, y, x + 5, y + 5, SSD1306_WHITE);
      oled.drawFastVLine(x + 5, y + 5, 4, SSD1306_WHITE);
      oled.drawFastHLine(x + 2, y + 9, 7, SSD1306_WHITE);
      break;
    case ICONE_GOTA:
      oled.fillCircle(x + 5, y + 6, 4, SSD1306_WHITE);
      oled.fillTriangle(x + 5, y, x + 1, y + 5, x + 9, y + 5, SSD1306_WHITE);
      break;
    case ICONE_SOL:
      oled.fillCircle(x + 5, y + 5, 2, SSD1306_WHITE);
      oled.drawFastVLine(x + 5, y, 2, SSD1306_WHITE);
      oled.drawFastVLine(x + 5, y + 8, 2, SSD1306_WHITE);
      oled.drawFastHLine(x, y + 5, 2, SSD1306_WHITE);
      oled.drawFastHLine(x + 8, y + 5, 2, SSD1306_WHITE);
      oled.drawLine(x + 1, y + 1, x + 2, y + 2, SSD1306_WHITE);
      oled.drawLine(x + 8, y + 1, x + 7, y + 2, SSD1306_WHITE);
      oled.drawLine(x + 1, y + 8, x + 2, y + 7, SSD1306_WHITE);
      oled.drawLine(x + 8, y + 8, x + 7, y + 7, SSD1306_WHITE);
      break;
  }
}

// Mini cabeçalho de todas as telas: data à esquerda, hora (HH:MM) à direita e
// uma linha embaixo. Enquanto o NTP não sincronizou, mostra traços no lugar.
// getLocalTime com timeout 0 não bloqueia o loop esperando a sincronização.
void desenharCabecalho() {
  struct tm dt;
  String data = "--/--/----";
  String hora = "--:--";
  if (getLocalTime(&dt, 0)) {
    data = doisDigitos(dt.tm_mday) + "/" + doisDigitos(dt.tm_mon + 1) + "/" + String(dt.tm_year + 1900);
    hora = doisDigitos(dt.tm_hour) + ":" + doisDigitos(dt.tm_min);
  }
  oled.setTextSize(1);
  oled.setCursor(0, 2);
  oled.print(data);
  oled.setCursor(LARGURA_OLED - 6 * hora.length(), 2); // fonte padrão: 6 px por caractere
  oled.print(hora);
  oled.drawFastHLine(0, 12, LARGURA_OLED, SSD1306_WHITE);
}

// Título do atributo logo abaixo do cabeçalho: texto à esquerda e ícone opcional à direita.
void desenharTitulo(const String& texto, bool comIcone, Icone icone) {
  oled.setTextSize(1);
  oled.setCursor(0, 16);
  oled.print(texto);
  if (comIcone) desenharIcone(icone, LARGURA_OLED - 10, 15);
}

// Valor principal em tamanho 3, centralizado (3 linhas de 24 px, entre o título e o rodapé).
void desenharValor(const String& texto) {
  centralizar(texto, 3, 27);
}

// Rodapé da tela de um atributo. Em alerta, um retângulo branco cheio com o
// texto em preto chama a atenção; sem alerta, mostra a faixa ideal.
// `desenharFaixa` escreve a faixa com o cursor já posicionado no rodapé.
void desenharRodape(bool emAlerta, void (*desenharFaixa)()) {
  oled.setTextSize(1);
  if (emAlerta) {
    oled.fillRect(0, 52, LARGURA_OLED, 12, SSD1306_WHITE);
    oled.setTextColor(SSD1306_BLACK);
    centralizar("FORA DA FAIXA", 1, 54);
    oled.setTextColor(SSD1306_WHITE);
  } else {
    oled.setCursor(0, 54);
    desenharFaixa();
  }
}

void faixaTemp() {
  oled.print("Ideal ");
  imprimirLimite(oled, faixa.tempMin);
  oled.print("-");
  imprimirLimite(oled, faixa.tempMax);
  oled.print(" C");
}

void faixaUmidade() {
  oled.print("Ideal ");
  imprimirLimite(oled, faixa.humMin);
  oled.print("-");
  imprimirLimite(oled, faixa.humMax);
  oled.print(" %");
}

void faixaLuz() {
  oled.print("Ideal ate ");
  imprimirLimite(oled, faixa.luxMax);
  oled.print(" %");
}

// Tela de temperatura atual. O rodapé mostra a faixa configurada (set_limits)
// quando normal, ou aviso de fora da faixa quando o backend mandou alerta.
void telaTemp() {
  desenharTitulo("Temperatura", true, ICONE_TACA);
  // O símbolo de grau não existe no GFX padrão: é um círculo entre o valor e o "C".
  String valor = String(ultimaTemperatura, 1);
  int16_t x1, y1;
  uint16_t wValor, h;
  oled.setTextSize(3);
  oled.getTextBounds(valor, 0, 0, &x1, &y1, &wValor, &h);
  int16_t xInicial = (LARGURA_OLED - (wValor + 8 + 12)) / 2; // valor + grau + "C" em tamanho 2
  oled.setCursor(xInicial, 27);
  oled.print(valor);
  oled.drawCircle(xInicial + wValor + 4, 29, 2, SSD1306_WHITE);
  oled.setTextSize(2);
  oled.setCursor(xInicial + wValor + 8, 27);
  oled.print("C");
  desenharRodape(alertTemp, faixaTemp);
}

// Tela 2: umidade atual, com o ícone de gota.
void telaUmidade() {
  desenharTitulo("Umidade", true, ICONE_GOTA);
  desenharValor(String(ultimaUmidade, 0) + "%");
  desenharRodape(alertHum, faixaUmidade);
}

// Tela de luminosidade atual, com o ícone de sol.
void telaLuz() {
  desenharTitulo("Luminosidade", true, ICONE_SOL);
  desenharValor(String(ultimaLuminosidade) + "%");
  desenharRodape(alertLux, faixaLuz);
}

// Uma linha da tela de alerta: "Temp 21.4C alta". O sentido sai da comparação
// da leitura com a faixa; "fora" cobre o instante em que o backend já mandou o
// alerta mas a leitura local voltou para dentro da faixa.
String linhaAlerta(const char* nome, float valor, int casas, const char* unidade, float minimo, float maximo) {
  const char* sentido = valor < minimo ? "baixa" : (valor > maximo ? "alta" : "fora");
  return String(nome) + " " + String(valor, casas) + unidade + " " + sentido;
}

// Tela de alerta: faixa branca "ALERTA" e uma linha por atributo em alerta
// (até 3). Enquanto houver alerta ativa fica fixa, no lugar do carrossel.
void telaAlerta() {
  oled.fillRect(0, 14, LARGURA_OLED, 12, SSD1306_WHITE);
  oled.setTextColor(SSD1306_BLACK);
  centralizar("ALERTA", 1, 16);
  oled.setTextColor(SSD1306_WHITE);

  int16_t y = 30;
  oled.setTextSize(1);
  if (alertTemp) {
    oled.setCursor(0, y);
    oled.print(linhaAlerta("Temp", ultimaTemperatura, 1, "C", faixa.tempMin, faixa.tempMax));
    y += 11;
  }
  if (alertHum) {
    oled.setCursor(0, y);
    oled.print(linhaAlerta("Umid", ultimaUmidade, 0, "%", faixa.humMin, faixa.humMax));
    y += 11;
  }
  if (alertLux) {
    oled.setCursor(0, y);
    oled.print(linhaAlerta("Luz", ultimaLuminosidade, 0, "%", faixa.luxMin, faixa.luxMax));
  }
}

bool emAlertaOled() {
  return alertTemp || alertHum || alertLux;
}

// Limpa o OLED e mostra até duas linhas de texto centralizadas (tamanho 1).
void telaTexto(const String& linha1, const String& linha2) {
  if (!oledOk) return;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  centralizar(linha1, 1, 24);
  centralizar(linha2, 1, 38);
  oled.display();
}

// Tela de espera enquanto o backend não mandou a faixa. Os pontos animados
// mostram que o dispositivo está vivo; sem MQTT, avisa que está conectando.
int pontosCarregando = 0;

void telaConfigurar() {
  String pontos = "";
  for (int i = 0; i < pontosCarregando; i++) {
    pontos += ".";
  }
  if (MQTT.connected()) {
    telaTexto("Configure o", "dispositivo" + pontos);
  } else {
    telaTexto("Conectando" + pontos, ID_DEVICE);
  }
  pontosCarregando = (pontosCarregando + 1) % 4;
}

// Despacha a tela atual do carrossel (0-2). O buffer do OLED é limpo antes de
// desenhar para não sobrepor o conteúdo da tela anterior. Com alerta ativo, o
// carrossel pausa e a tela de alerta é redesenhada a cada T_ALERTA, para o
// cabeçalho e os valores continuarem atualizados.
const int TOTAL_TELAS = 3;
int telaAtual = 0;

// Intervalo de troca das telas do OLED e ritmo dos pontos da tela de espera.
const unsigned long T_TELA = 3000;
const unsigned long T_ALERTA = 1000;
const unsigned long T_CARREGANDO = 500;
unsigned long ultimaTela = 0;

void telaOLED() {
  if (!oledOk) return;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  desenharCabecalho();
  if (emAlertaOled()) {
    telaAlerta();
  } else {
    switch (telaAtual) {
      case 0: telaTemp(); break;
      case 1: telaUmidade(); break;
      case 2: telaLuz(); break;
    }
    telaAtual = (telaAtual + 1) % TOTAL_TELAS;
  }
  oled.display();
}

// Troca o modo de alerta e reinicia o ciclo do buzzer (evita salto de fase).
void setAlertMode(AlertMode modo) {
  if (alertMode != modo) {
    alertMode = modo;
    alertCycleStart = millis();
  }
}

// Responde o comando no tópico cmdexe: "<device_id>@<comando>|<ok|erro>".
void publicarAck(const String &cmd, const char *resultado) {
  char ack[60];
  snprintf(ack, sizeof(ack), "%s@%s|%s", ID_DEVICE, cmd.c_str(), resultado);
  MQTT.publish(topicCmdExe, ack);
}

// Callback de mensagens MQTT recebidas no tópico de comando.
// Payload no formato UltraLight do IoT Agent: "<device_id>@<comando>|<args>".
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  Serial.print("Comando recebido [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(msg);

  int posArroba = msg.indexOf('@');
  int posPipe = msg.indexOf('|');
  String cmd = msg;
  if (posArroba >= 0) {
    cmd = (posPipe > posArroba) ? msg.substring(posArroba + 1, posPipe) : msg.substring(posArroba + 1);
  }

  // Sem faixa cadastrada, nenhum alerta toca: evita disparo ao ligar com
  // parâmetros que não vieram do backend. alert_off é sempre aceito.
  bool ehBlink = (cmd == "blink_temp" || cmd == "blink_hum" || cmd == "blink_lux");
  if (ehBlink && !configurado) {
    Serial.println("Alerta recusado: dispositivo ainda nao configurado (aguardando set_limits)");
    publicarAck(cmd, "erro");
    return;
  }

  if (cmd == "blink_temp") {
    alertTemp = true;
    setAlertMode(ALERT_TEMP);
  } else if (cmd == "blink_hum") {
    alertHum = true;
    setAlertMode(ALERT_HUM);
  } else if (cmd == "blink_lux") {
    alertLux = true;
    setAlertMode(ALERT_LUX);
  } else if (cmd == "alert_off") {
    alertTemp = false;
    alertHum = false;
    alertLux = false;
    setAlertMode(ALERT_NONE);
  } else if (cmd == "set_limits") {
    String args = (posPipe >= 0) ? msg.substring(posPipe + 1) : "";
    Faixa nova;
    if (!parseFaixa(args, nova)) {
      Serial.print("set_limits invalido, comando ignorado: ");
      Serial.println(args);
      publicarAck(cmd, "erro");
      return;
    }
    bool primeiraVez = !configurado;
    faixa = nova;
    configurado = true;
    if (primeiraVez) {
      // Sai da tela de espera: mostra a confirmação e o carrossel segue depois
      telaTexto("Configurado!", ID_DEVICE);
      telaAtual = 0;
      ultimaTela = millis();
    }
  } else {
    Serial.print("Comando desconhecido: ");
    Serial.println(cmd);
    return;
  }

  publicarAck(cmd, "ok");
}

// Tenta reconectar ao broker sem travar o loop() — se falhar, não insiste
// imediatamente, só tenta de novo depois de INTERVALO_RECONEXAO_MQTT. Assim
// o OLED, o LED e o buzzer continuam funcionando mesmo com a EC2 fora do ar.
const unsigned long INTERVALO_RECONEXAO_MQTT = 2000;
unsigned long ultimaTentativaMQTT = 0;

void reconectarMQTT() {
  if (MQTT.connected()) return;

  unsigned long agora = millis();
  if (agora - ultimaTentativaMQTT < INTERVALO_RECONEXAO_MQTT) return;
  ultimaTentativaMQTT = agora;

  Serial.print("Conectando ao broker MQTT...");
  if (MQTT.connect(ID_DEVICE)) {
    Serial.println("conectado");
    MQTT.subscribe(topicCmd);
  } else {
    Serial.println("falhou, tentando novamente em 2s");
  }
}

// Lê o LDR e converte para percentual de luminosidade (0-100%).
// Invertido de propósito: no módulo de LDR usado, o pino AO sobe quando
// escurece (resistência do LDR cresce no escuro). Sem a inversão, 100% de
// luz no simulador aparecia como 0% na tela.
int lerLuminosidade() {
  int leituraAdc = analogRead(LDRPIN);
  return map(leituraAdc, 0, 4095, 100, 0);
}

// --- Publicação periódica de telemetria (não bloqueante via millis) ---
const unsigned long INTERVALO_PUBLICACAO_MS = 2000;
unsigned long ultimaPublicacao = 0;

// Lê DHT+LDR e publica "t|<temp>|h|<umid>|l|<lux>|c|<0 ou 1>" em topicAttrs.
// Se a leitura do DHT vier NaN, pula o ciclo (não publica) e loga no Serial.
void publicarTelemetria() {
  float temperatura = dht.readTemperature();
  float umidade = dht.readHumidity();
  int luminosidade = lerLuminosidade();

  if (isnan(temperatura) || isnan(umidade)) {
    Serial.println("Leitura do DHT invalida (NaN) - ciclo descartado");
    return;
  }

  ultimaTemperatura = temperatura;
  ultimaUmidade = umidade;
  ultimaLuminosidade = luminosidade;

  char payload[80];
  snprintf(payload, sizeof(payload), "t|%.1f|h|%.1f|l|%d|c|%d",
           temperatura, umidade, luminosidade, configurado ? 1 : 0);

  MQTT.publish(topicAttrs, payload);
  Serial.print("Publicado em ");
  Serial.print(topicAttrs);
  Serial.print(": ");
  Serial.println(payload);
}

// Padrões de buzzer por anomalia (duração em ms, alternando ON/OFF a partir
// de ON). Soma de cada array = duração total do ciclo, que se repete.
const int PADRAO_TEMP[] = {100, 100, 100, 1700};      // 2 bipes curtos / ciclo de 2s
const int PADRAO_HUM[] = {700, 2300};                  // 1 bipe longo / ciclo de 3s
const int PADRAO_LUX[] = {60, 60, 60, 60, 60, 1700};   // 3 bipes rápidos / ciclo de 2s

// Dado o tempo decorrido dentro do ciclo, diz se o buzzer deve estar ligado.
// Índices pares do padrão = ON, ímpares = OFF (começa sempre em ON).
bool estadoBuzzer(unsigned long decorrido, const int* padrao, int tamanho) {
  unsigned long acumulado = 0;
  for (int i = 0; i < tamanho; i++) {
    acumulado += padrao[i];
    if (decorrido < acumulado) {
      return (i % 2 == 0);
    }
  }
  return false;
}

// Pisca o LED alternando a cada intervaloMs (liga/desliga em frequência fixa).
bool estadoLed(unsigned long decorrido, unsigned long intervaloMs) {
  return ((decorrido / intervaloMs) % 2) == 0;
}

// Intervalo de pisca do LED (ms) de cada modo de alerta; 0 quando não há alerta.
unsigned long intervaloLedDoModo(AlertMode modo) {
  switch (modo) {
    case ALERT_TEMP: return 500;
    case ALERT_HUM: return 250;
    case ALERT_LUX: return 125;
    default: return 0;
  }
}

// Atualiza o buzzer conforme o alertMode atual. Chamada a cada loop().
void atualizarBuzzer() {
  if (alertMode == ALERT_NONE) {
    noTone(BUZZER_PIN);
    return;
  }

  unsigned long decorrido = millis() - alertCycleStart;
  const int* padrao;
  int tamanhoPadrao;
  unsigned long duracaoCiclo;

  switch (alertMode) {
    case ALERT_TEMP:
      padrao = PADRAO_TEMP;
      tamanhoPadrao = sizeof(PADRAO_TEMP) / sizeof(int);
      duracaoCiclo = 2000;
      break;
    case ALERT_HUM:
      padrao = PADRAO_HUM;
      tamanhoPadrao = sizeof(PADRAO_HUM) / sizeof(int);
      duracaoCiclo = 3000;
      break;
    case ALERT_LUX:
      padrao = PADRAO_LUX;
      tamanhoPadrao = sizeof(PADRAO_LUX) / sizeof(int);
      duracaoCiclo = 2000;
      break;
    default:
      return;
  }

  if (estadoBuzzer(decorrido % duracaoCiclo, padrao, tamanhoPadrao)) {
    tone(BUZZER_PIN, 2000); // 2kHz fixo; timbre não importa para o alerta
  } else {
    noTone(BUZZER_PIN);
  }
}

// Atualiza o LED RGB de status: verde (ok), vermelho piscando no ritmo do
// sensor em alerta, amarelo sem conexão ou sem faixa. Chamada a cada loop().
void atualizarLed() {
  bool conectado = WiFi.status() == WL_CONNECTED && MQTT.connected();
  bool emAlerta = alertMode != ALERT_NONE;
  bool faseAcesa = true;
  if (emAlerta) {
    faseAcesa = estadoLed(millis() - alertCycleStart, intervaloLedDoModo(alertMode));
  }
  aplicarCor(escolherCor(conectado, emAlerta, configurado, faseAcesa));
}

// Tela de boot exibida uma única vez. delay() aceitável aqui: roda antes do
// loop(), não interfere no padrão não-bloqueante de LED/buzzer.
void logo() {
  if (!oledOk) return;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  centralizar("Smart", 2, 14);
  centralizar("Solutions", 2, 34);
  oled.display();
  delay(2000);
  animacaoBoot(oled);
  String pontos = "";
  for (int i = 0; i < 5; i++) {
    pontos += ".";
    telaTexto("Inicializando" + pontos, "");
    delay(300);
  }
}

void setup() {
  Serial.begin(115200);
  montarTopicos();
  iniciarLedRgb();
  aplicarCor(COR_AMARELO); // amarelo até conectar e receber o set_limits
  conectarWiFi();
  MQTT.setServer(BROKER_MQTT, BROKER_PORT);
  MQTT.setCallback(mqttCallback);
  dht.begin();
  pinMode(BUZZER_PIN, OUTPUT);

  oledOk = oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  if (!oledOk) {
    Serial.println("OLED nao encontrado no endereco 0x3C - seguindo sem display");
  }
  logo();
  iniciarRelogio();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    aplicarCor(COR_AMARELO); // conectarWiFi() bloqueia até reconectar
    conectarWiFi();
  }
  if (!MQTT.connected()) {
    reconectarMQTT();
  }
  MQTT.loop();

  unsigned long agora = millis();
  if (agora - ultimaPublicacao >= INTERVALO_PUBLICACAO_MS) {
    ultimaPublicacao = agora;
    publicarTelemetria();
  }

  if (!configurado) {
    if (agora - ultimaTela >= T_CARREGANDO) {
      ultimaTela = agora;
      telaConfigurar();
    }
  } else if (agora - ultimaTela >= (emAlertaOled() ? T_ALERTA : T_TELA)) {
    ultimaTela = agora;
    telaOLED();
  }

  atualizarBuzzer();
  atualizarLed();
}
