"""Funciones puras de preprocesamiento (OpenCV + NumPy)."""
import base64
import binascii

import cv2
import numpy as np

Puntos = list[tuple[float, float, float]]


def decodificar_base64(cadena: str | None) -> np.ndarray | None:
    """Convierte un data URL o Base64 en imagen BGR. None si no se puede leer."""
    if not cadena:
        return None
    if "," in cadena[:100]:
        cadena = cadena.split(",", 1)[1]
    try:
        datos = base64.b64decode(cadena)
    except (binascii.Error, ValueError):
        return None
    buffer = np.frombuffer(datos, dtype=np.uint8)
    if buffer.size == 0:
        return None
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def espejar(imagen: np.ndarray) -> np.ndarray:
    return cv2.flip(imagen, 1)


def caja_desde_landmarks(puntos: Puntos, margen: float = 0.25) -> tuple[float, float, float, float]:
    """Caja (x, y, ancho, alto) normalizada 0-1 alrededor de la mano."""
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    ancho, alto = max(xs) - min(xs), max(ys) - min(ys)
    x0 = max(0.0, min(xs) - ancho * margen)
    y0 = max(0.0, min(ys) - alto * margen)
    x1 = min(1.0, max(xs) + ancho * margen)
    y1 = min(1.0, max(ys) + alto * margen)
    return (round(x0, 4), round(y0, 4), round(x1 - x0, 4), round(y1 - y0, 4))


def recortar_roi(imagen: np.ndarray, puntos: Puntos, margen: float = 0.15) -> np.ndarray:
    """Recorte cuadrado de la mano, idéntico al de dactilologiaMexicana (lado x1.3).

    Con margen=0.15 el lado del cuadrado es 1 + 2 * 0.15 = 1.3 veces la mano.
    """
    alto, ancho = imagen.shape[:2]
    xs = [int(p[0] * ancho) for p in puntos]
    ys = [int(p[1] * alto) for p in puntos]
    factor = round(1 + 2 * margen, 6)
    lado = int(max(max(xs) - min(xs), max(ys) - min(ys)) * factor)
    centro_x, centro_y = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
    x0, y0 = max(0, centro_x - lado // 2), max(0, centro_y - lado // 2)
    x1, y1 = min(ancho, x0 + lado), min(alto, y0 + lado)
    roi = imagen[y0:y1, x0:x1]
    return roi if roi.size else imagen


def preparar_imagen(roi_bgr: np.ndarray, forma: tuple[int, ...], normalizacion: str = "0_1") -> np.ndarray:
    """Redimensiona y normaliza al tensor (1, alto, ancho, canales)."""
    _, alto, ancho, canales = forma
    codigo = cv2.COLOR_BGR2GRAY if canales == 1 else cv2.COLOR_BGR2RGB
    imagen = cv2.resize(cv2.cvtColor(roi_bgr, codigo), (ancho, alto), interpolation=cv2.INTER_LINEAR)
    imagen = imagen.astype(np.float32)
    if normalizacion == "0_1":
        imagen /= 255.0
    elif normalizacion == "-1_1":
        imagen = imagen / 127.5 - 1.0
    if canales == 1:
        imagen = imagen[..., np.newaxis]
    return imagen[np.newaxis, ...]


def landmarks_a_tensor(puntos: Puntos, forma: tuple[int, ...]) -> np.ndarray:
    """Vector de 42 (x, y) o 63 (x, y, z) relativo a la muñeca y escalado."""
    total = int(np.prod(forma[1:]))
    if total not in (42, 63):
        raise ValueError(f"Forma de entrada no soportada para landmarks: {forma}")
    datos = np.asarray(puntos, dtype=np.float32)[:, : 2 if total == 42 else 3]
    datos = datos - datos[0]
    escala = float(np.abs(datos).max())
    if escala > 0:
        datos /= escala
    return datos.reshape((1, *forma[1:]))