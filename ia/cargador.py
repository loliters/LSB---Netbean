"""Carga única (Singleton) del intérprete TFLite y del detector de manos."""
import threading
from pathlib import Path

import numpy as np
from django.conf import settings


class ModeloNoDisponibleError(RuntimeError):
    """El modelo o sus dependencias no están disponibles."""


def _clase_interprete():
    """Devuelve la clase Interpreter disponible (LiteRT, tflite_runtime o TF)."""
    try:
        from ai_edge_litert.interpreter import Interpreter

        return Interpreter
    except ImportError:
        pass
    try:
        from tflite_runtime.interpreter import Interpreter

        return Interpreter
    except ImportError:
        pass
    try:
        import tensorflow as tf

        return tf.lite.Interpreter
    except ImportError as error:
        raise ModeloNoDisponibleError(
            "Instala 'tensorflow' o 'ai-edge-litert' para ejecutar el modelo."
        ) from error


def _leer_etiquetas(ruta: Path) -> list[str]:
    if not ruta.exists():
        return []
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return [linea.strip() for linea in lineas if linea.strip()]


class CargadorModelo:
    """Mantiene un único intérprete TFLite por proceso, seguro entre hilos."""

    _instancia = None
    _candado_creacion = threading.Lock()

    def __init__(self) -> None:
        ruta = Path(settings.RUTA_MODELO_TFLITE)
        if not ruta.exists():
            raise ModeloNoDisponibleError(f"No se encontró el modelo en {ruta}.")
        self.interprete = _clase_interprete()(model_path=str(ruta))
        self.interprete.allocate_tensors()
        self._entrada = self.interprete.get_input_details()[0]
        self._salida = self.interprete.get_output_details()[0]
        self.etiquetas = _leer_etiquetas(Path(settings.RUTA_ETIQUETAS))
        self._candado_inferencia = threading.Lock()

    @classmethod
    def obtener(cls) -> "CargadorModelo":
        if cls._instancia is None:
            with cls._candado_creacion:
                if cls._instancia is None:  # doble verificación
                    cls._instancia = cls()
        return cls._instancia

    @classmethod
    def reiniciar(cls) -> None:
        """Descarta la instancia (útil al cambiar de modelo o en pruebas)."""
        with cls._candado_creacion:
            cls._instancia = None

    @property
    def forma_entrada(self) -> tuple[int, ...]:
        return tuple(int(d) if int(d) > 0 else 1 for d in self._entrada["shape"])

    @property
    def modo(self) -> str:
        """'imagen' si espera (1, alto, ancho, canales); si no, 'landmarks'."""
        return "imagen" if len(self.forma_entrada) == 4 else "landmarks"

    def etiqueta(self, indice: int) -> str:
        return self.etiquetas[indice] if indice < len(self.etiquetas) else str(indice)

    def inferir(self, tensor: np.ndarray) -> np.ndarray:
        """Ejecuta el modelo y devuelve la salida en float."""
        entrada = self._cuantizar(tensor)
        with self._candado_inferencia:
            self.interprete.set_tensor(self._entrada["index"], entrada)
            self.interprete.invoke()
            salida = self.interprete.get_tensor(self._salida["index"]).copy()
        return self._decuantizar(salida)

    def _cuantizar(self, tensor: np.ndarray) -> np.ndarray:
        tipo = self._entrada["dtype"]
        if tipo == np.float32:
            return tensor.astype(np.float32)
        escala, cero = self._entrada["quantization"]
        valores = np.round(tensor / escala + cero) if escala else tensor
        limites = np.iinfo(tipo)
        return np.clip(valores, limites.min, limites.max).astype(tipo)

    def _decuantizar(self, salida: np.ndarray) -> np.ndarray:
        escala, cero = self._salida["quantization"]
        if self._salida["dtype"] != np.float32 and escala:
            return (salida.astype(np.float32) - cero) * escala
        return salida.astype(np.float32)


class DetectorManos:
    """Singleton de MediaPipe HandLandmarker (API Tasks) para ubicar la mano.

    Usa el archivo ``hand_landmarker.task`` (el mismo del repositorio
    dactilologiaMexicana) indicado en ``settings.RUTA_HAND_LANDMARKER``.
    """

    _instancia = None
    _candado_creacion = threading.Lock()

    def __init__(self) -> None:
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
        except ImportError as error:
            raise ModeloNoDisponibleError("Instala 'mediapipe' para detectar la mano.") from error
        ruta = Path(settings.RUTA_HAND_LANDMARKER)
        if not ruta.exists():
            raise ModeloNoDisponibleError(f"No se encontró el detector de manos en {ruta}.")
        opciones = vision.HandLandmarkerOptions(
            # Se pasa el contenido en bytes: evita fallos de rutas en Windows.
            base_options=mp_python.BaseOptions(model_asset_buffer=ruta.read_bytes()),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.5,
        )
        self._cv2 = cv2
        self._mp = mp
        self._detector = vision.HandLandmarker.create_from_options(opciones)
        self._candado = threading.Lock()

    @classmethod
    def obtener(cls) -> "DetectorManos":
        if cls._instancia is None:
            with cls._candado_creacion:
                if cls._instancia is None:
                    cls._instancia = cls()
        return cls._instancia

    def detectar(self, imagen_bgr: np.ndarray) -> list[tuple[float, float, float]] | None:
        """Devuelve 21 puntos (x, y, z) normalizados o None si no hay mano."""
        rgb = np.ascontiguousarray(self._cv2.cvtColor(imagen_bgr, self._cv2.COLOR_BGR2RGB))
        imagen_mp = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        with self._candado:
            resultado = self._detector.detect(imagen_mp)
        if not resultado.hand_landmarks:
            return None
        return [(p.x, p.y, p.z) for p in resultado.hand_landmarks[0]]