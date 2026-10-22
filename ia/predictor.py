"""Predicción de la seña a partir de un fotograma en Base64."""
from dataclasses import dataclass

import numpy as np
from django.conf import settings

from .cargador import CargadorModelo, DetectorManos
from .preprocesador import (
    caja_desde_landmarks,
    decodificar_base64,
    espejar,
    landmarks_a_tensor,
    preparar_imagen,
    recortar_roi,
)


@dataclass(frozen=True)
class Prediccion:
    """Resultado tipado de la inferencia."""

    letra: str | None
    confianza: float
    mano_detectada: bool
    caja: tuple[float, float, float, float] | None = None

    def a_dict(self) -> dict:
        return {
            "letra": self.letra,
            "confianza": self.confianza,
            "mano_detectada": self.mano_detectada,
            "caja": list(self.caja) if self.caja else None,
        }


SIN_MANO = Prediccion(letra=None, confianza=0.0, mano_detectada=False)


def predecir_desde_base64(frame_b64: str) -> Prediccion:
    """Decodifica, ubica la mano con MediaPipe y clasifica con el modelo TFLite.

    Raises:
        ModeloNoDisponibleError: Si faltan el modelo o sus dependencias.
    """
    imagen = decodificar_base64(frame_b64)
    if imagen is None:
        return SIN_MANO
    if getattr(settings, "IA_ESPEJAR_FRAME", False):
        imagen = espejar(imagen)
    puntos = DetectorManos.obtener().detectar(imagen)
    if puntos is None:
        return SIN_MANO
    modelo = CargadorModelo.obtener()
    margen = getattr(settings, "IA_MARGEN_ROI", 0.15)
    probabilidades = _a_probabilidades(modelo.inferir(_construir_tensor(imagen, puntos, modelo, margen)))
    indice = int(np.argmax(probabilidades))
    return Prediccion(
        letra=modelo.etiqueta(indice),
        confianza=round(float(probabilidades[indice]), 4),
        mano_detectada=True,
        caja=caja_desde_landmarks(puntos, margen),
    )


def _construir_tensor(imagen, puntos, modelo: CargadorModelo, margen: float) -> np.ndarray:
    if modelo.modo == "imagen":
        roi = recortar_roi(imagen, puntos, margen)
        return preparar_imagen(roi, modelo.forma_entrada, getattr(settings, "IA_NORMALIZACION", "ninguna"))
    return landmarks_a_tensor(puntos, modelo.forma_entrada)


def _a_probabilidades(salida: np.ndarray) -> np.ndarray:
    """Aplica softmax si la salida no es ya una distribución de probabilidad."""
    valores = np.asarray(salida, dtype=np.float64).ravel()
    if valores.min() < 0 or not np.isclose(valores.sum(), 1.0, atol=1e-2):
        exponenciales = np.exp(valores - valores.max())
        valores = exponenciales / exponenciales.sum()
    return valores