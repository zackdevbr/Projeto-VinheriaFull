/*
 * Vinheria Full — firmware ESP32
 * Task 1 / Passo 1: base de conexão Wi-Fi + MQTT com os tópicos UltraLight 2.0
 * do device "vinheria001". Sensores, LED e buzzer entram nos próximos passos.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <time.h>

// --- Credenciais de rede (Wokwi usa rede aberta "Wokwi-GUEST") ---
const char* SSID = "Wokwi-GUEST";
const char* PASSWORD = "";

// --- Broker MQTT (Mosquitto do FIWARE na EC2) ---
// A EC2 usa IP elástico (fixo entre liga e desliga), então o IP pode ficar aqui.
const char* BROKER_MQTT = "3.215.3.216";
const int BROKER_PORT = 1883;

// --- Identificação do device (nomes canônicos do plano FIWARE) ---
const char* ID_DEVICE = "vinheria001";

// --- Sensor de temperatura/umidade ---
// Simulação no Wokwi usa DHT22 (não tem DHT11 no simulador); hardware real da
// vinheria usa DHT11. Para trocar: mudar DHTTYPE para DHT11, pinagem não muda.
#define DHTPIN 4
#define DHTTYPE DHT22
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

// --- Limites de alerta configuráveis pelo backend (comando set_limits) ---
// Defaults herdados do CP2 (faixa recomendada para vinheria), usados até o
// backend mandar o primeiro set_limits. O ESP32 não decide alerta com eles
// (quem decide é o backend); servem só para o texto exibido no LCD.
int limTempMin = 10, limTempMax = 16;
int limHumMin = 60, limHumMax = 80;
int limLuxMin = 0, limLuxMax = 30;

// Flags por atributo: o LCD precisa saber se cada atributo está em alerta
// mesmo quando o alertMode (que só governa o padrão de LED/buzzer) está
// ocupado com outro atributo — duas anomalias podem estar ativas ao mesmo
// tempo. alert_off vindo do backend só é mandado quando nenhum atributo
// mais está em alerta, então ele limpa as três de uma vez.
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
    lcd.print(limTempMin);
    lcd.print("-");
    lcd.print(limTempMax);
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
    lcd.print(limHumMin);
    lcd.print("-");
    lcd.print(limHumMax);
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
    lcd.print(limLuxMax);
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

// Despacha a tela atual (0-4) e limpa o LCD antes de desenhar — evita
// sobrepor texto de tamanhos diferentes entre uma tela e outra.
int telaAtual = 0;

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

// Converte uma String em int, rejeitando qualquer coisa não-numérica
// (aceita sinal de menos). Vazio também é rejeitado.
bool parseInteiro(String s, int &out) {
  s.trim();
  if (s.length() == 0) return false;
  int i = (s[0] == '-') ? 1 : 0;
  if (i >= (int)s.length()) return false;
  for (; i < (int)s.length(); i++) {
    if (!isDigit(s[i])) return false;
  }
  out = s.toInt();
  return true;
}

// Faz o parsing de "temp_min|temp_max|hum_min|hum_max|lux_min|lux_max"
// (ordem canônica do comando set_limits). Só retorna true se vierem
// exatamente 6 campos numéricos — nem mais, nem menos. Validação atômica:
// quem chama só aplica os valores se o retorno for true.
bool parseLimites(String args, int valores[6]) {
  int inicio = 0;
  int count = 0;
  while (count < 6) {
    int fim = args.indexOf('|', inicio);
    String campo = (fim >= 0) ? args.substring(inicio, fim) : args.substring(inicio);
    if (!parseInteiro(campo, valores[count])) return false;
    count++;
    if (fim < 0) {
      inicio = args.length();
      break;
    }
    inicio = fim + 1;
  }
  if (count != 6) return false;
  if (inicio < (int)args.length()) return false; // sobrou campo extra (7º valor)
  return true;
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
    int valores[6];
    if (!parseLimites(args, valores)) {
      Serial.print("set_limits invalido, comando ignorado: ");
      Serial.println(args);
      char ackErro[50];
      snprintf(ackErro, sizeof(ackErro), "%s@%s|erro", ID_DEVICE, cmd.c_str());
      MQTT.publish(topicCmdExe, ackErro);
      return;
    }
    limTempMin = valores[0];
    limTempMax = valores[1];
    limHumMin = valores[2];
    limHumMax = valores[3];
    limLuxMin = valores[4];
    limLuxMax = valores[5];
  } else {
    Serial.print("Comando desconhecido: ");
    Serial.println(cmd);
    return;
  }

  char ack[50];
  snprintf(ack, sizeof(ack), "%s@%s|ok", ID_DEVICE, cmd.c_str());
  MQTT.publish(topicCmdExe, ack);
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

// Lê DHT+LDR e publica "t|<temp>|h|<umid>|l|<lux>" em topicAttrs.
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
  snprintf(payload, sizeof(payload), "t|%.1f|h|%.1f|l|%d", temperatura, umidade, luminosidade);

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
  lcd.print("Smart Solutions");
  lcd.setCursor(0, 1);
  lcd.print("Vinheria Agn.");
  delay(2000);
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
  lcd.createChar(0, CHAR_TACA_ESQ);
  lcd.createChar(1, CHAR_TACA_DIR);
  lcd.createChar(2, CHAR_GOTA);
  lcd.createChar(3, CHAR_SOL);
  logo();
  iniciarRelogio();
}

// Intervalo de troca das telas do LCD (passo 8 vai expandir para 5 telas).
const unsigned long T_TELA = 3000;
unsigned long ultimaTela = 0;

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

  if (agora - ultimaTela >= T_TELA) {
    ultimaTela = agora;
    telaLCD();
  }

  atualizarAlerta();
}
