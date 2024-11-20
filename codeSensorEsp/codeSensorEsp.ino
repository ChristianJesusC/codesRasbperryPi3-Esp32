#include <WiFi.h>
#include <WiFiManager.h> 
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_MLX90614.h>
#include "config.h"

// Definir el nombre de la red AP del ESP32
const char* ssidAP = "ESP32_Config";      // Nombre de la red del ESP32 (punto de acceso)
const char* passwordAP = "123456789";     // Contraseña de la red del ESP32

const char* mqtt_topic_bpm = "sensor/bpm";
const char* mqtt_topic_temp = "sensor/temperatura";

WiFiClient espClient;
PubSubClient client(espClient);

// Pines y variables para el sensor de ritmo cardíaco
const int pulsePin = 34;  // Pin donde se conecta el sensor de pulso
const int LED_PIN = 2;    // LED integrado para indicar un pulso

volatile int BPM;                   // Almacena los BPM actuales
volatile int Signal;                // Almacena la señal del sensor
volatile int IBI = 600;             // Intervalo entre latidos
volatile boolean Pulse = false;     // Indica si se detecta un latido
volatile boolean QS = false;        // Se activa cuando se detecta un latido

unsigned long lastBeat = 0;    // Tiempo del último latido
const int TIMEOUT = 2000;      // Timeout para reiniciar si no se detecta pulso
float myBPM = 0;              // BPM promedio

// Sensor de temperatura
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

void setup() {
  // Iniciar el monitor serie para depuración
  Serial.begin(115200);

  pinMode(LED_PIN, OUTPUT);

  // Crear instancia de WiFiManager
  WiFiManager wifiManager;

  // Intentar conectar a una red Wi-Fi preconfigurada, o crear un AP con el nombre `ESP32_Config`
  wifiManager.autoConnect(ssidAP, passwordAP);

  // Comprobar si la conexión Wi-Fi es exitosa
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Conexión Wi-Fi exitosa!");
    Serial.print("Dirección IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("No se pudo conectar a la red Wi-Fi.");
  }

  // Configurar cliente MQTT
  client.setServer(mqtt_server, mqtt_port);

  // Inicializar sensor MLX90614
  if (!mlx.begin()) {
    Serial.println("Error: No se pudo inicializar el sensor MLX90614. Verifica las conexiones.");
    while (true);
  }
  Serial.println("Sensor MLX90614 inicializado correctamente.");
}

void loop() {
  // Reconectar a MQTT si es necesario
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  // Leer datos del sensor de ritmo cardíaco
  Signal = analogRead(pulsePin);
  processBPM();

  // Leer temperatura del sensor MLX90614
  float temperaturaObjeto = mlx.readObjectTempC();

  // Publicar BPM si es mayor a 60
  if (myBPM > 60) {
    String payload_bpm = "{\"Event\":\"BPM Update\",\"valor\":" + String(myBPM) + "}";
    client.publish(mqtt_topic_bpm, payload_bpm.c_str());
    Serial.print("Enviado a MQTT - BPM: ");
    Serial.println(payload_bpm);
  }

  // Publicar temperatura
  String payload_temp = "{\"Event\":\"Temperatura\",\"valor\":" + String(temperaturaObjeto) + "}";
  client.publish(mqtt_topic_temp, payload_temp.c_str());
  Serial.print("Enviado a MQTT - Temperatura: ");
  Serial.println(payload_temp);

  // Esperar antes de la siguiente iteración
  delay(1000);
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.println("Intentando conectar a MQTT...");
    if (client.connect("ESP32Client", mqtt_username, mqtt_password)) {
      Serial.println("Conectado a MQTT");
    } else {
      Serial.print("Fallo de conexión MQTT. Código: ");
      Serial.print(client.state());
      Serial.println(" Intentando de nuevo en 5 segundos...");
      delay(5000);
    }
  }
}

void processBPM() {
  unsigned long currentTime = millis();
  int threshold = 2000;

  if (Signal > threshold && !Pulse && (currentTime - lastBeat) > IBI / 2) {
    digitalWrite(LED_PIN, HIGH);
    Pulse = true;

    IBI = currentTime - lastBeat;
    lastBeat = currentTime;

    if (IBI < 2000 && IBI > 300) {
      myBPM = 60000.0 / IBI;
    }
  }

  if (Signal < threshold && Pulse) {
    digitalWrite(LED_PIN, LOW);
    Pulse = false;
  }

  if (currentTime - lastBeat > TIMEOUT) {
    myBPM = 0;
    Serial.println("No se detecta pulso...");
  }
}
