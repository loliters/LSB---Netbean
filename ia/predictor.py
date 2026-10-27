"""Predicción de la seña a partir de un fotograma en Base64.

Modo "letra": clasifica con la CNN (EfficientNetB2 TFLite).
Modo "numero": cuenta los dedos extendidos con los puntos de MediaPipe (1 a 5).
En ambos modos devuelve los 21 puntos y el estado de cada dedo para la guía visual.
"""
from dataclasses import dataclass, field

import numpy as np
from django.conf import settings

from .cargador import CargadorModelo, DetectorManos
from .contador_dedos import contar_dedos, estado_dedos
from .preprocesador import (
    caja_desde_landmarks,
    decodificar_base64,
    espejar,
    landmarks_a_tensor,
    preparar_imagen,
    recortar_roi,
)

MODOS = ("letra", "numero")


@dataclass(frozen=True)
class Prediccion:
    """Resultado tipado de la inferencia."""

    letra: str | None
    confianza: float
    mano_detectada: bool
    caja: tuple[float, float, float, float] | None = None
    puntos: tuple = ()
    dedos: dict = field(default_factory=dict)
    modo: str = "letra"

    def a_dict(self) -> dict:
        return {
            "letra": self.letra,
            "confianza": self.confianza,
            "mano_detectada": self.mano_detectada,
            "caja": list(self.caja) if self.caja else None,
            "puntos": [[round(p[0], 4), round(p[1], 4)] for p in self.puntos],
            "dedos": self.dedos,
            "modo": self.modo,
        }


def predecir_desde_base64(frame_b64: str, modo: str = "letra") -> Prediccion:
    """Decodifica, ubica la mano con MediaPipe y predice según el modo.

    Raises:
        ModeloNoDisponibleError: Si faltan el modelo o sus dependencias.
    """
    modo = modo if modo in MODOS else "letra"
    sin_mano = Prediccion(letra=None, confianza=0.0, mano_detectada=False, modo=modo)
    imagen = decodificar_base64(frame_b64)
    if imagen is None:
        return sin_mano
    if getattr(settings, "IA_ESPEJAR_FRAME", False):
        imagen = espejar(imagen)
    puntos = DetectorManos.obtener().detectar(imagen)
    if puntos is None:
        return sin_mano
    margen = getattr(settings, "IA_MARGEN_ROI", 0.15)
    comunes = {
        "mano_detectada": True,
        "caja": caja_desde_landmarks(puntos, margen),
        "puntos": tuple((p[0], p[1]) for p in puntos),
        "dedos": estado_dedos(puntos),
        "modo": modo,
    }
    if modo == "numero":
        cantidad, confianza = contar_dedos(puntos)
        letra = str(cantidad) if 1 <= cantidad <= 5 else None
        return Prediccion(letra=letra, confianza=confianza, **comunes)
    modelo = CargadorModelo.obtener()
    probabilidades = _a_probabilidades(modelo.inferir(_construir_tensor(imagen, puntos, modelo, margen)))
    indice = int(np.argmax(probabilidades))
    return Prediccion(letra=modelo.etiqueta(indice), confianza=round(float(probabilidades[indice]), 4), **comunes)


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
