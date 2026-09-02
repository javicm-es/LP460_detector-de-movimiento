#!/usr/bin/env python3

import time
import requests
import subprocess

CONFIG_FILE = "/etc/telegram-webcam.conf"
DETECTOR = "/home/javier/detector_movimiento.py"

def cargar_configuracion():
    config = {}

    with open(CONFIG_FILE) as f:
        for linea in f:
            linea = linea.strip()

            if not linea or linea.startswith("#"):
                continue

            clave, valor = linea.split("=", 1)
            config[clave.strip()] = valor.strip()

    return config["BOT_TOKEN"], config["CHAT_ID"]


TOKEN, CHAT_ID = cargar_configuracion()

API = f"https://api.telegram.org/bot{TOKEN}"


def enviar_mensaje(texto):
    requests.post(
        API + "/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": texto
        },
        timeout=10
    )


def obtener_updates(offset=None):

    parametros = {
        "timeout": 30
    }

    if offset is not None:
        parametros["offset"] = offset

    respuesta = requests.get(
        API + "/getUpdates",
        params=parametros,
        timeout=35
    )

    respuesta.raise_for_status()

    return respuesta.json()["result"]


def detector_activo():

    resultado = subprocess.run(
        ["pgrep", "-f", DETECTOR],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return resultado.returncode == 0


def arrancar_detector():

    if detector_activo():
        return False

    subprocess.Popen(
        ["python3", DETECTOR],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return True


def parar_detector():

    subprocess.run(
        ["pkill", "-f", DETECTOR],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def main():

    print("Controlador de Telegram iniciado")

    offset = None

    while True:

        try:

            updates = obtener_updates(offset)

            for update in updates:

                offset = update["update_id"] + 1

                mensaje = update.get("message")

                if not mensaje:
                    continue

                chat_id = str(
                    mensaje["chat"]["id"]
                )

                # Seguridad: solamente nuestro chat
                if chat_id != CHAT_ID:
                    continue

                texto = mensaje.get("text", "").strip()

                if texto == "/start":

                    if arrancar_detector():

                        enviar_mensaje(
                            "🟢 Detector de movimiento ACTIVADO"
                        )

                    else:

                        enviar_mensaje(
                            "ℹ️ El detector ya estaba activo"
                        )


                elif texto == "/stop":

                    if detector_activo():

                        parar_detector()

                        enviar_mensaje(
                            "🔴 Detector de movimiento DETENIDO"
                        )

                    else:

                        enviar_mensaje(
                            "ℹ️ El detector ya estaba detenido"
                        )


                elif texto == "/status":

                    if detector_activo():

                        enviar_mensaje(
                            "🟢 Detector de movimiento ACTIVO"
                        )

                    else:

                        enviar_mensaje(
                            "🔴 Detector de movimiento PARADO"
                        )

        except Exception as e:

            print(f"Error: {e}")

            time.sleep(5)


if __name__ == "__main__":
    main()
