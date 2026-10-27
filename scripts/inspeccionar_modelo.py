"""Muestra la forma de entrada/salida de un .tflite para configurar Net Bean.

Uso:
    python scripts/inspeccionar_modelo.py ia/modelos/modelo_v1.tflite
"""
import sys


def clase_interprete():
    try:
        from ai_edge_litert.interpreter import Interpreter
        return Interpreter
    except ImportError:
        pass
    try:
        from tflite_runtime.interpreter import Interpreter
        return Interpreter
    except ImportError:
        import tensorflow as tf
        return tf.lite.Interpreter


def main(ruta: str) -> None:
    interprete = clase_interprete()(model_path=ruta)
    interprete.allocate_tensors()
    entrada = interprete.get_input_details()[0]
    salida = interprete.get_output_details()[0]
    forma = list(entrada["shape"])
    modo = "imagen" if len(forma) == 4 else "landmarks"
    print(f"Entrada : forma={forma} tipo={entrada['dtype'].__name__} cuantizacion={entrada['quantization']}")
    print(f"Salida  : forma={list(salida['shape'])} tipo={salida['dtype'].__name__}")
    print(f"Modo detectado por Net Bean: {modo}")
    print(f"Clases de salida: {int(salida['shape'][-1])} (etiquetas_v1.txt debe tener esa cantidad de líneas)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/inspeccionar_modelo.py <ruta.tflite>")
    main(sys.argv[1])
