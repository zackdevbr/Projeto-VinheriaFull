/*
 * Smart Solutions — monitoramento de vinherias (firmware ESP32)
 *
 * Lê temperatura, umidade (DHT) e luminosidade (LDR), publica no FIWARE por
 * MQTT em UltraLight 2.0, executa comandos de alerta (LED azul e buzzer) e
 * mostra os dados num LCD 16x2. O ID da vinheria e a rede ficam no bloco
 * "CONFIGURAÇÃO DESTA INSTÂNCIA" abaixo.
 *
 * Nasce sem faixa ideal: mostra "Configure o dispositivo" e recusa alertas
 * até o backend mandar o set_limits.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <time.h>
#include "boot_animacao.h"
#include "limites.h"

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

// --- LED azul e buzzer de alerta ---
#define LED_PIN 2
#define BUZZER_PIN 5

// --- Display LCD 16x2 I2C (herdado do CP2, endereco 0x27) ---
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Caracteres customizados do CP2: taça (2 metades), gota, sol.
byte CHAR_TACA_ESQ[8] = {B00111, B01000, B01000, B11111, B11111, B11111, B11111, B01111};
byte CHAR_TACA_DIR[8] = {B11100, B00010, B00010, B11111, B11111, B11111, B11111, B11110};
byte CHAR_GOTA[8] = {B00100, B00100, B01010, B01010, B10001, B10001, B10001, B01110};
byte CHAR_SOL[8] = {B00100, B10101, B01110, B11111, B01110, B10101, B00100, B00000};

// --- Faixa ideal recebida do backend (comando set_limits) ---
// O ESP32 nasce SEM faixa: até o backend mandar o set_limits, o LCD mostra
// "Configure o dispositivo" e os comandos de alerta são recusados, para
// nenhum alerta disparar com parâmetros que não foram cadastrados. A faixa
// é só informativa no LCD (quem decide o alerta é o backend). `configurado`
// vai na telemetria (c|0 ou c|1): é por ele que o backend percebe que o
// ESP32 reiniciou e reenvia a faixa na hora.
Faixa faixa;
bool configurado = false;

// Flags por atributo: o LCD precisa saber se cada atributo está em alerta
// mesmo quando o alertMode (que só governa o padrão de LED/buzzer) está
// ocupado com outro atributo — duas anomalias podem estar ativas ao mesmo
// tempo. alert_off limpa as três de uma vez; quando uma anomalia normaliza
// e outra continua, o backend manda alert_off e em seguida o blink da que restou.
bool alertTemp = false;
bool alertHum = false;
bool alertLux = false;

// Últimas leituras válidas — usadas pelo publish MQTT e pelas telas do LCD.
// Começam em 0 porque o LCD só as exibe depois da primeira leitura válida.
float ultimaTemperatura = 0;
float ultimaUmidade = 0;
int ultimaLuminosidade = 0;

// Estado da máquina de alerta: qual anomalia está ativa agora (ou nenhuma).
enum AlertMode { ALERT_NONE, ALERT_TEMP, ALERT_HUM, ALERT_LUX };
AlertMode alertMode = ALERT_NONE;
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

// Preenche p2 (2 dígitos com zero à esquerda) no LCD, igual ao CP2.
void imprimirDoisDigitos(int valor) {
  if (valor < 10) lcd.print("0");
  lcd.print(valor);
}

// Tela 0: data e hora obtidas por NTP. Se ainda não sincronizou, avisa.
void telaData() {
  struct tm dt;
  if (!getLocalTime(&dt)) {
    lcd.setCursor(0, 0);
    lcd.print("Sincronizando");
    lcd.setCursor(0, 1);
    lcd.print("relogio (NTP)...");
    return;
  }

  lcd.setCursor(0, 0);
  lcd.print("Data: ");
  imprimirDoisDigitos(dt.tm_mday);
  lcd.print("/");
  imprimirDoisDigitos(dt.tm_mon + 1);
  lcd.print("/");
  lcd.print(dt.tm_year + 1900);

  lcd.setCursor(0, 1);
  lcd.print("Hora: ");
  imprimirDoisDigitos(dt.tm_hour);
  lcd.print(":");
  imprimirDoisDigitos(dt.tm_min);
  lcd.print(":");
  imprimirDoisDigitos(dt.tm_sec);
}

// Tela 1: temperatura atual. Linha 2 mostra a faixa configurada (set_limits)
// quando normal, ou aviso de fora da faixa quando o backend mandou alerta.
void telaTemp() {
  lcd.setCursor(0, 0);
  lcd.print("Temp: ");
  lcd.print(ultimaTemperatura, 1);
  lcd.print((char)223); // símbolo de grau
  lcd.print("C");

  lcd.setCursor(0, 1);
  if (alertTemp) {
    lcd.print("TEMP FORA FAIXA");
  } else {
    lcd.print("Ideal ");
    imprimirLimite(lcd, faixa.tempMin);
    lcd.print("-");
    imprimirLimite(lcd, faixa.tempMax);
    lcd.print("C");
  }
}

// Tela 2: umidade atual, com o caractere de gota.
void telaUmidade() {
  lcd.setCursor(0, 0);
  lcd.print("Umidade: ");
  lcd.print(ultimaUmidade, 0);
  lcd.print("% ");
  lcd.write(byte(2));

  lcd.setCursor(0, 1);
  if (alertHum) {
    lcd.print("UMID FORA FAIXA");
  } else {
    lcd.print("Ideal ");
    imprimirLimite(lcd, faixa.humMin);
    lcd.print("-");
    imprimirLimite(lcd, faixa.humMax);
    lcd.print("%");
  }
}

// Tela 3: luminosidade atual, com o caractere de sol.
void telaLuz() {
  lcd.setCursor(0, 0);
  lcd.print("Luz: ");
  lcd.print(ultimaLuminosidade);
  lcd.print("% ");
  lcd.write(byte(3));

  lcd.setCursor(0, 1);
  if (alertLux) {
    lcd.print("LUZ FORA FAIXA");
  } else {
    lcd.print("Ideal ate ");
    imprimirLimite(lcd, faixa.luxMax);
    lcd.print("%");
  }
}

// Tela 4: status geral da adega, com o caractere de taça (2 metades).
// "Sem conexao" tem prioridade: se a EC2 caiu, é isso que importa mostrar.
void telaStatus() {
  lcd.setCursor(0, 0);
  lcd.print("Status Adega ");
  lcd.write(byte(0));
  lcd.write(byte(1));

  lcd.setCursor(0, 1);
  if (!MQTT.connected()) {
    lcd.print("Sem conexao");
  } else if (alertTemp || alertHum || alertLux) {
    lcd.print("Atencao");
  } else {
    lcd.print("Cond. Premium");
  }
}

// Tela de espera enquanto o backend não mandou a faixa. Os pontos animados
// mostram que o dispositivo está vivo; sem MQTT, avisa que está conectando.
int pontosCarregando = 0;

void telaConfigurar() {
  lcd.clear();
  lcd.setCursor(0, 0);
  if (MQTT.connected()) {
    lcd.print("Configure o");
    lcd.setCursor(0, 1);
    lcd.print("dispositivo");
  } else {
    lcd.print("Conectando");
    lcd.setCursor(0, 1);
    lcd.print(ID_DEVICE);
  }
  for (int i = 0; i < pontosCarregando; i++) {
    lcd.print(".");
  }
  pontosCarregando = (pontosCarregando + 1) % 4;
}

// Despacha a tela atual (0-4) e limpa o LCD antes de desenhar — evita
// sobrepor texto de tamanhos diferentes entre uma tela e outra.
int telaAtual = 0;

// Intervalo de troca das telas do LCD e ritmo dos pontos da tela de espera.
const unsigned long T_TELA = 3000;
const unsigned long T_CARREGANDO = 500;
unsigned long ultimaTela = 0;

void telaLCD() {
  lcd.clear();
  switch (telaAtual) {
    case 0: telaData(); break;
    case 1: telaTemp(); break;
    case 2: telaUmidade(); break;
    case 3: telaLuz(); break;
    case 4: telaStatus(); break;
  }
  telaAtual = (telaAtual + 1) % 5;
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
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Configurado!");
      lcd.setCursor(0, 1);
      lcd.print(ID_DEVICE);
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
// o LCD, o LED e o buzzer continuam funcionando mesmo com a EC2 fora do ar.
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

// Atualiza LED azul e buzzer conforme o alertMode atual. Chamada every loop().
void atualizarAlerta() {
  if (alertMode == ALERT_NONE) {
    digitalWrite(LED_PIN, LOW);
    noTone(BUZZER_PIN);
    return;
  }

  unsigned long decorrido = millis() - alertCycleStart;
  unsigned long intervaloLed;
  const int* padrao;
  int tamanhoPadrao;
  unsigned long duracaoCiclo;

  switch (alertMode) {
    case ALERT_TEMP:
      intervaloLed = 500;
      padrao = PADRAO_TEMP;
      tamanhoPadrao = sizeof(PADRAO_TEMP) / sizeof(int);
      duracaoCiclo = 2000;
      break;
    case ALERT_HUM:
      intervaloLed = 250;
      padrao = PADRAO_HUM;
      tamanhoPadrao = sizeof(PADRAO_HUM) / sizeof(int);
      duracaoCiclo = 3000;
      break;
    case ALERT_LUX:
      intervaloLed = 125;
      padrao = PADRAO_LUX;
      tamanhoPadrao = sizeof(PADRAO_LUX) / sizeof(int);
      duracaoCiclo = 2000;
      break;
    default:
      return;
  }

  digitalWrite(LED_PIN, estadoLed(decorrido, intervaloLed) ? HIGH : LOW);

  if (estadoBuzzer(decorrido % duracaoCiclo, padrao, tamanhoPadrao)) {
    tone(BUZZER_PIN, 2000); // 2kHz fixo; timbre não importa para o alerta
  } else {
    noTone(BUZZER_PIN);
  }
}

// Tela de boot exibida uma única vez. delay() aceitável aqui: roda antes do
// loop(), não interfere no padrão não-bloqueante de LED/buzzer.
void logo() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Smart Solutions"); // 15 colunas de 16; a linha 2 fica vazia
  delay(2000);
  animacaoBoot(lcd);
  lcd.clear();
  lcd.print("Inicializando");
  for (int i = 0; i < 5; i++) {
    lcd.print(".");
    delay(300);
  }
  lcd.clear();
}

void setup() {
  Serial.begin(115200);
  montarTopicos();
  conectarWiFi();
  MQTT.setServer(BROKER_MQTT, BROKER_PORT);
  MQTT.setCallback(mqttCallback);
  dht.begin();
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  lcd.init();
  lcd.backlight();
  logo();

  // Os ícones do carrossel ocupam os slots 0 a 3, que a animação de boot
  // sobrescreve. Por isso só são carregados depois do logo().
  lcd.createChar(0, CHAR_TACA_ESQ);
  lcd.createChar(1, CHAR_TACA_DIR);
  lcd.createChar(2, CHAR_GOTA);
  lcd.createChar(3, CHAR_SOL);
  iniciarRelogio();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
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
  } else if (agora - ultimaTela >= T_TELA) {
    ultimaTela = agora;
    telaLCD();
  }

  atualizarAlerta();
}
