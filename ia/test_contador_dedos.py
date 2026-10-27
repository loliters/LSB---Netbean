"""Pruebas del contador de dedos (funciones puras, sin Django)."""
import math
import unittest

from ia.contador_dedos import contar_dedos, estado_dedos


def mano(extendidos: set[str]) -> list[tuple[float, float, float]]:
    """Mano sintética vertical: muñeca abajo; dedos extendidos llegan más arriba."""
    puntos = [(0.5, 0.9, 0.0)] * 21
    puntos = list(puntos)
    puntos[0] = (0.5, 0.9, 0.0)
    puntos[9] = (0.5, 0.7, 0.0)        # base del medio
    puntos[5] = (0.44, 0.71, 0.0)      # base del índice
    columnas = {"indice": (0.44, 8, 6), "medio": (0.5, 12, 10), "anular": (0.56, 16, 14), "menique": (0.62, 20, 18)}
    for nombre, (x, punta, pip) in columnas.items():
        puntos[pip] = (x, 0.62, 0.0)
        puntos[punta] = (x, 0.45, 0.0) if nombre in extendidos else (x, 0.68, 0.0)
    puntos[3] = (0.40, 0.78, 0.0)
    puntos[4] = (0.30, 0.72, 0.0) if "pulgar" in extendidos else (0.45, 0.74, 0.0)
    return puntos


class ContadorDedosTests(unittest.TestCase):
    def test_puno_cerrado_cero_dedos(self):
        self.assertEqual(contar_dedos(mano(set()))[0], 0)

    def test_uno_solo_indice(self):
        self.assertEqual(contar_dedos(mano({"indice"}))[0], 1)
        self.assertTrue(estado_dedos(mano({"indice"}))["indice"])

    def test_tres_dedos(self):
        self.assertEqual(contar_dedos(mano({"pulgar", "indice", "medio"}))[0], 3)

    def test_cinco_dedos_y_confianza_en_rango(self):
        cantidad, confianza = contar_dedos(mano({"pulgar", "indice", "medio", "anular", "menique"}))
        self.assertEqual(cantidad, 5)
        self.assertTrue(0.55 <= confianza <= 1.0)

    def test_independiente_de_la_rotacion(self):
        puntos = mano({"indice", "medio"})
        angulo = math.radians(35)
        cx, cy = 0.5, 0.9
        rotados = [(cx + (x - cx) * math.cos(angulo) - (y - cy) * math.sin(angulo),
                    cy + (x - cx) * math.sin(angulo) + (y - cy) * math.cos(angulo), z) for x, y, z in puntos]
        self.assertEqual(contar_dedos(rotados)[0], 2)


if __name__ == "__main__":
    unittest.main()
