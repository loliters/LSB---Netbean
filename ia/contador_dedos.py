"""Estado de cada dedo y conteo para números 1-5 a partir de los 21 puntos de MediaPipe.

Funciones puras: reciben los puntos (x, y, z) normalizados y devuelven datos.
Se usan distancias a la muñeca, así el resultado no depende de la rotación de la mano.
"""
import math

Puntos = list[tuple[float, float, float]]
ORDEN_DEDOS = ("pulgar", "indice", "medio", "anular", "menique")
# punta, articulación media (PIP) de cada dedo largo
ARTICULACIONES = {"indice": (8, 6), "medio": (12, 10), "anular": (16, 14), "menique": (20, 18)}
UMBRAL_EXTENSION = 1.12  # la punta debe estar 12 % más lejos de la muñeca que la PIP


def _distancia(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def proporciones_dedos(puntos: Puntos) -> dict[str, float]:
    """Cuánto se aleja cada punta respecto de su articulación (1.0 = doblado)."""
    muneca = puntos[0]
    resultado = {}
    for nombre, (punta, pip) in ARTICULACIONES.items():
        resultado[nombre] = _distancia(puntos[punta], muneca) / max(_distancia(puntos[pip], muneca), 1e-6)
    escala_palma = max(_distancia(puntos[0], puntos[9]), 1e-6)
    resultado["pulgar"] = _distancia(puntos[4], puntos[5]) / escala_palma / 0.5
    return resultado


def estado_dedos(puntos: Puntos) -> dict[str, bool]:
    """True si el dedo está extendido."""
    proporciones = proporciones_dedos(puntos)
    estados = {nombre: proporciones[nombre] > UMBRAL_EXTENSION for nombre in ARTICULACIONES}
    estados["pulgar"] = proporciones["pulgar"] > UMBRAL_EXTENSION
    return {nombre: estados[nombre] for nombre in ORDEN_DEDOS}


def contar_dedos(puntos: Puntos) -> tuple[int, float]:
    """Número de dedos extendidos y una confianza 0-1 según qué tan claros están."""
    proporciones = proporciones_dedos(puntos)
    margenes = [min(abs(valor - UMBRAL_EXTENSION) / 0.35, 1.0) for valor in proporciones.values()]
    confianza = round(0.55 + 0.45 * (sum(margenes) / len(margenes)), 4)
    cantidad = sum(estado_dedos(puntos).values())
    return cantidad, confianza
