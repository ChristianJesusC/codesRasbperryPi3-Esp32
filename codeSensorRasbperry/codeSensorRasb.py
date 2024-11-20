import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import json
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración fija de los pines GPIO
TRIG_PIN = 23
ECHO_PIN = 24
TOUCH_PIN = 18

# Configuración de MQTT desde el archivo .env
BROKER = os.getenv("BROKER", "localhost")  # Valor por defecto: localhost
PORT = int(os.getenv("PORT", 1883))  # Valor por defecto: 1883
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "default_user")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "default_password")
TOPIC_DISTANCIA = os.getenv("TOPIC_DISTANCIA", "sensor/distancia")
TOPIC_TOQUE = os.getenv("TOPIC_TOQUE", "sensor/toque")

# Configuración de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(TOUCH_PIN, GPIO.IN)

# Configuración del cliente MQTT
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(BROKER, PORT, 60)

# Función para medir distancia
def medir_distancia():
    GPIO.output(TRIG_PIN, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        inicio = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        fin = time.time()
    tiempo_transcurrido = fin - inicio
    distancia = (tiempo_transcurrido * 34300) / 2
    return distancia

# Función para manejar eventos táctiles
def toque_detectado(channel):
    print("¡Toque detectado en el botón táctil!")
    mensaje_toque = json.dumps({"Llamada": True})
    client.publish(TOPIC_TOQUE, mensaje_toque)

GPIO.add_event_detect(TOUCH_PIN, GPIO.RISING, callback=toque_detectado)
estado_distancia = None

# Función para verificar sensores
def verificar_sensores():
    global estado_distancia
    if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
        mensaje_toque = json.dumps({"estado": True})
        client.publish(TOPIC_TOQUE, mensaje_toque)
    try:
        distancia = medir_distancia()
        print(distancia)
        if distancia > 0:
            if distancia < 20:
                if estado_distancia != True:
                    mensaje_distancia = json.dumps({"Movimiento": True})
                    client.publish(TOPIC_DISTANCIA, mensaje_distancia)
                    estado_distancia = True
            elif distancia > 20:
                if estado_distancia != False:
                    mensaje_distancia = json.dumps({"Movimiento": False})
                    client.publish(TOPIC_DISTANCIA, mensaje_distancia)
                    estado_distancia = False
    except Exception as e:
        print(f"Error: {e}")

# Ejecución principal
print("Esperando detección de distancia o toque...")
try:
    while True:
        verificar_sensores()
        time.sleep(1)

except KeyboardInterrupt:
    print("Programa terminado")

finally:
    GPIO.cleanup()
    client.disconnect()
