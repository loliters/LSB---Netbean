"""Convierte un modelo Keras (.h5 / .keras) a .tflite.

Uso:
    python scripts/convertir_a_tflite.py ruta/modelo.h5 ia/modelos/modelo_v1.tflite
"""
import sys
from pathlib import Path

import tensorflow as tf


def main(origen: str, destino: str) -> None:
    modelo = tf.keras.models.load_model(origen, compile=False)
    convertidor = tf.lite.TFLiteConverter.from_keras_model(modelo)
    convertidor.optimizations = [tf.lite.Optimize.DEFAULT]
    Path(destino).write_bytes(convertidor.convert())
    print(f"Modelo guardado en {destino}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Uso: python scripts/convertir_a_tflite.py <origen.h5|.keras> <destino.tflite>")
    main(sys.argv[1], sys.argv[2])
