/*
 * Vinheria Full — firmware ESP32
 * Task 1 / Passo 1: base de conexão Wi-Fi + MQTT com os tópicos UltraLight 2.0
 * do device "vinheria001". Sensores, LED e buzzer entram nos próximos passos.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// --- Credenciais de rede (Wokwi usa rede aberta "Wokwi-GUEST") ---
const char* SSID = "Wokwi-GUEST";
const char* PASSWORD = "";

// --- Broker MQTT (Mosquitto do FIWARE na EC2) ---
// IP/porta fixos aqui só para simulação local; em produção isso viria de config.
const char* BROKER_MQTT = "0.0.0.0"; // TODO: IP público da EC2 (digitado antes de cada sessão)
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

// Troca o modo de alerta e reinicia o ciclo do buzzer (evita salto de fase).
void setAlertMode(AlertMode modo) {
  if (alertMode != modo) {
    alertMode = modo;
    alertCycleStart = millis();
  }
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
    setAlertMode(ALERT_TEMP);
  } else if (cmd == "blink_hum") {
    setAlertMode(ALERT_HUM);
  } else if (cmd == "blink_lux") {
    setAlertMode(ALERT_LUX);
  } else if (cmd == "alert_off") {
    setAlertMode(ALERT_NONE);
  } else {
    Serial.print("Comando desconhecido: ");
    Serial.println(cmd);
    return;
  }

  char ack[50];
  snprintf(ack, sizeof(ack), "%s@%s|ok", ID_DEVICE, cmd.c_str());
  MQTT.publish(topicCmdExe, ack);
}

void reconectarMQTT() {
  while (!MQTT.connected()) {
    Serial.print("Conectando ao broker MQTT...");
    if (MQTT.connect(ID_DEVICE)) {
      Serial.println("conectado");
      MQTT.subscribe(topicCmd);
    } else {
      Serial.println("falhou, tentando novamente em 2s");
      delay(2000);
    }
  }
}

// Lê o LDR e converte para percentual de luminosidade (0-100%).
int lerLuminosidade() {
  int leituraAdc = analogRead(LDRPIN);
  return map(leituraAdc, 0, 4095, 0, 100);
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

void setup() {
  Serial.begin(115200);
  montarTopicos();
  conectarWiFi();
  MQTT.setServer(BROKER_MQTT, BROKER_PORT);
  MQTT.setCallback(mqttCallback);
  dht.begin();
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
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

  atualizarAlerta();
}
