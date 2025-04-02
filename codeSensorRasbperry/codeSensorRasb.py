import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import json
import threading
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de los pines GPIO
TRIG_PIN = 23
ECHO_PIN = 24
TOUCH_PIN = 18

# Configuración de MQTT desde .env
BROKER = os.getenv("BROKER", "localhost")
PORT = int(os.getenv("PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "default_user")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "default_password")
TOPIC_DISTANCIA = os.getenv("TOPIC_DISTANCIA", "sensor/distancia")
TOPIC_TOQUE = os.getenv("TOPIC_TOQUE", "sensor/toque")

# Configuración de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Configuración del cliente MQTT
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(BROKER, PORT, 60)
client.loop_start()  # Importante para mantener la conexión activa

lock = threading.Lock()
sensor_event = threading.Event()
sensor_event.set()

def mqtt_reconnect_loop():
    while True:
        time.sleep(30)
        try:
            if not client.is_connected():
                print("Reconectando a MQTT...")
                client.reconnect()
                print("Reconectado con éxito")
        except Exception as e:
            print(f"Error al reconectar MQTT: {e}")

def medir_distancia():
    with lock:
        GPIO.output(TRIG_PIN, GPIO.LOW)
        time.sleep(0.5)
        GPIO.output(TRIG_PIN, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(TRIG_PIN, GPIO.LOW)
        
        inicio = time.time()
        while GPIO.input(ECHO_PIN) == GPIO.LOW:
            inicio = time.time()
        while GPIO.input(ECHO_PIN) == GPIO.HIGH:
            fin = time.time()

        tiempo_transcurrido = fin - inicio
        distancia = (tiempo_transcurrido * 34300) / 2
        
        if distancia < 0 or distancia > 400:
            return None  
        return distancia

# Función para manejar eventos táctiles
def toque_detectado(channel):
    print("¡Toque detectado!")
    mensaje_toque = json.dumps({"Llamada": True})
    client.publish(TOPIC_TOQUE, mensaje_toque)

GPIO.add_event_detect(TOUCH_PIN, GPIO.FALLING, callback=toque_detectado, bouncetime=300)

# Hilo para monitorear sensores
def sensor_loop():
    estado_distancia = None
    while sensor_event.is_set():
        try:
            distancia = medir_distancia()
            if distancia is not None:
                print(f"Distancia: {distancia:.2f} cm")
                
                if distancia < 20 and estado_distancia != True:
                    client.publish(TOPIC_DISTANCIA, json.dumps({"Movimiento": True}))
                    estado_distancia = True
                elif distancia >= 20 and estado_distancia != False:
                    client.publish(TOPIC_DISTANCIA, json.dumps({"Movimiento": False}))
                    estado_distancia = False
        except Exception as e:
            print(f"Error en sensor: {e}")
        
        time.sleep(1)

sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
mqtt_thread = threading.Thread(target=mqtt_reconnect_loop, daemon=True)

sensor_thread.start()
mqtt_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Terminando programa...")
    sensor_event.clear()
    sensor_thread.join()
finally:
    GPIO.cleanup()
    client.disconnect()
