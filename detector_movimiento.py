#!/usr/bin/env python3

import time
import requests
from PIL import Image, ImageChops
from io import BytesIO

# Webcam / ustreamer
SNAPSHOT_URL = "http://10.10.20.6:8080/snapshot"

# Telegram
CONFIG_FILE = "/etc/telegram-webcam.conf"

# Detección
INTERVALO = 1
PIXEL_UMBRAL = 25
PORCENTAJE_UMBRAL = 2.0

# Tiempo mínimo entre alertas
COOLDOWN = 30


def cargar_configuracion():
    config = {}

    with open(CONFIG_FILE, "r") as f:
        for linea in f:
            linea = linea.strip()

            if not linea or linea.startswith("#"):
                continue

            clave, valor = linea.split("=", 1)
            config[clave.strip()] = valor.strip()

    return config["BOT_TOKEN"], config["CHAT_ID"]


def obtener_imagen():
    respuesta = requests.get(SNAPSHOT_URL, timeout=5)
    respuesta.raise_for_status()

    return Image.open(
        BytesIO(respuesta.content)
    ).convert("L")


def enviar_telegram(token, chat_id, imagen):
    # Convertimos la imagen a JPEG directamente en memoria
    buffer = BytesIO()
    imagen.convert("RGB").save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    archivos = {
        "photo": ("movimiento.jpg", buffer, "image/jpeg")
    }

    datos = {
        "chat_id": chat_id,
        "caption": "🚨 Movimiento detectado en LP460"
    }

    respuesta = requests.post(
        url,
        data=datos,
        files=archivos,
        timeout=15
    )

    respuesta.raise_for_status()


def calcular_cambio(anterior, actual):
    diferencia = ImageChops.difference(anterior, actual)

    histograma = diferencia.histogram()

    pixeles_cambiados = sum(
        histograma[PIXEL_UMBRAL + 1:]
    )

    total_pixeles = actual.width * actual.height

    return (pixeles_cambiados / total_pixeles) * 100


def main():

    token, chat_id = cargar_configuracion()

    print("Detector de movimiento iniciado")
    print(f"Intervalo: {INTERVALO} segundo(s)")
    print(f"Umbral: {PORCENTAJE_UMBRAL}%")
    print(f"Cooldown: {COOLDOWN} segundos")
    print("Las fotografías se mantienen únicamente en RAM.")
    print("Pulsa Ctrl+C para salir")

    anterior = obtener_imagen()

    ultima_alerta = 0

    while True:

        time.sleep(INTERVALO)

        try:

            actual = obtener_imagen()

            cambio = calcular_cambio(anterior, actual)

            ahora = time.time()

            if cambio >= PORCENTAJE_UMBRAL:

                if ahora - ultima_alerta >= COOLDOWN:

                    print(
                        f"🚨 MOVIMIENTO — "
                        f"{cambio:.2f}% — enviando Telegram"
                    )

                    try:
                        enviar_telegram(
                            token,
                            chat_id,
                            actual
                        )

                        print("✅ Foto enviada a Telegram")

                        ultima_alerta = ahora

                    except Exception as e:

                        print(
                            f"❌ Error enviando Telegram: {e}"
                        )

                else:

                    restante = int(
                        COOLDOWN - (ahora - ultima_alerta)
                    )

                    print(
                        f"Movimiento ({cambio:.2f}%) "
                        f"— cooldown: {restante}s"
                    )

            else:

                print(
                    f"Sin movimiento — "
                    f"{cambio:.2f}%"
                )

            anterior = actual

        except Exception as e:

            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
