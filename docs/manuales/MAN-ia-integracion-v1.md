# MAN-ia-integracion-v1 · Integración del modelo dactilologiaMexicana

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-10-15 | Programadora / Tester | Primera versión |

## 1. Qué es el repositorio

`M0ndares/dactilologiaMexicana` es una aplicación web que clasifica las 27 letras del alfabeto de la Lengua de Señas Mexicana (LSM) más 2 señas adicionales, en tiempo real desde la webcam.

Net Bean usa **solo el modelo entrenado y sus etiquetas**. No se copia su servidor, su frontend ni su dataset.

> Advertencia académica: el modelo es de LSM, no de LSB. Úsalo como prototipo de la Iteración 2 y declara esta limitación en la ficha del modelo. Las letras con movimiento (J, K, Ñ, Q, X, Z, entre otras) no se clasifican bien con un solo fotograma.

## 2. Clonar fuera del proyecto

Clona en una carpeta hermana, **no dentro de `LSBWebb/`**, para no versionar código ajeno:

```bash
cd ..
git clone https://github.com/M0ndares/dactilologiaMexicana.git
cd dactilologiaMexicana
git log -1 --format=%H      # anota el commit en ficha_modelo_v1.md
```

## 3. Revisar la licencia

```bash
ls LICENSE* README*
```

- Con licencia abierta (MIT, Apache-2.0, etc.): puedes reutilizar el modelo citando al autor.
- Sin archivo LICENSE: el código no es libre por defecto. Pide permiso al autor por GitHub antes de entregar el proyecto y cítalo en la ficha.

## 4. Ubicar el modelo y las etiquetas

```bash
# Modelos entrenados
find . -iname "*.tflite" -o -iname "*.h5" -o -iname "*.keras" -o -iname "*.pb"

# Lista de clases y su orden
grep -rniE "labels|clases|classes|letras|alphabet|abecedario" --include=*.py --include=*.js --include=*.json --include=*.txt .

# Preprocesamiento que usaron al entrenar
grep -rniE "resize|/ ?255|127\.5|mediapipe|Hands\(|landmark|flip" --include=*.py --include=*.js --include=*.ipynb .
```

En Windows (PowerShell) usa `Get-ChildItem -Recurse -Include *.tflite,*.h5,*.keras` y `Select-String`.

Anota tres datos:

1. Orden exacto de las clases (índice 0, 1, 2…).
2. Si el modelo recibe **imagen** (por ejemplo 1×224×224×3) o **landmarks** de MediaPipe (42 u 63 valores).
3. Normalización: `/255` → `0_1`; `/127.5 - 1` → `-1_1`; sin división → `ninguna`. Si invierten la imagen con `flip`, activa `IA_ESPEJAR_FRAME`.

## 5. Copiar a Net Bean

| Del repositorio clonado | A LSBWebb |
|---|---|
| `*.tflite` | `ia/modelos/modelo_v1.tflite` |
| Lista de clases | `ia/modelos/etiquetas_v1.txt` (una por línea, mismo orden) |
| Notebook o script de entrenamiento (opcional, solo referencia) | `ia/entrenamiento/` con nota de autoría |

Si solo hay `.h5` o `.keras`:

```bash
python scripts/convertir_a_tflite.py ../dactilologiaMexicana/<ruta>/modelo.h5 ia/modelos/modelo_v1.tflite
```

Ejemplo de `etiquetas_v1.txt` (verifícalo contra el repositorio, el orden real manda):

```
A
B
C
...
```

Los nombres de `etiquetas_v1.txt` deben coincidir con `sena.nombre` en la BD (por ejemplo `A`, `B`). La comparación ignora mayúsculas y espacios.

## 6. Instalar dependencias

```bash
pip install -r requirements/base.txt   # tras agregar requirements/base_agregar.txt
```

`mediapipe==0.10.14` se fija porque mantiene la API `mp.solutions.hands` usada en `ia/cargador.py`.

## 7. Inspeccionar y configurar

```bash
python scripts/inspeccionar_modelo.py ia/modelos/modelo_v1.tflite
```

Copia el resultado en `ficha_modelo_v1.md` y ajusta `config/settings/netbean.py`:

```python
IA_NORMALIZACION = "0_1"     # según el paso 4
IA_ESPEJAR_FRAME = False
IA_MARGEN_ROI = 0.25
```

`ia/predictor.py` elige solo el modo (`imagen` o `landmarks`) según la forma de entrada del modelo.

## 8. Verificar

```bash
python manage.py shell -c "from ia.cargador import CargadorModelo as C; m=C.obtener(); print(m.modo, m.forma_entrada, len(m.etiquetas))"
python manage.py test apps.reconocimiento apps.gamificacion apps.usuarios tests
python manage.py runserver
```

Abre `/contenido/modulos/`, elige una seña y pulsa **Activar cámara**.

## 9. Git

- Si `modelo_v1.tflite` pesa más de 50 MB: `git lfs track "ia/modelos/*.tflite"`.
- Commit sugerido: `feat(ia): integrar modelo TFLite y cargador singleton [HU-05]`.
