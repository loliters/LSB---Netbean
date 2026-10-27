# Ficha del modelo v1

| Campo | Valor |
|---|---|
| Archivo | `modelo_v1.tflite` |
| Etiquetas | `etiquetas_v1.txt` (una por línea, en el orden de salida del modelo) |
| Origen | https://github.com/M0ndares/dactilologiaMexicana (commit: `________`) |
| Licencia del origen | `________` (revisar archivo LICENSE del repositorio) |
| Lengua de señas | LSM (Lengua de Señas Mexicana), 27 letras + 2 señas |
| Entrada | forma `________` / tipo `________` (salida de `scripts/inspeccionar_modelo.py`) |
| Modo | `imagen` o `landmarks` |
| Normalización | `IA_NORMALIZACION = "________"` |
| Espejado | `IA_ESPEJAR_FRAME = ________` |
| Exactitud reportada | `________` |
| Fecha de integración | `________` |

## Limitaciones conocidas

- Modelo entrenado con LSM, no con LSB. Letras con movimiento (por ejemplo J, K, Ñ, Q, X, Z) no se reconocen bien con un solo fotograma.
- Usar solo como prototipo hasta entrenar `modelo_v2` con un dataset de LSB.
