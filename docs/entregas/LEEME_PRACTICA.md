# Bloque 1: Práctica (fix/practica-evaluar-camara)

## 1. Copiar archivos
Copia el contenido de esta carpeta sobre tu proyecto (respeta las rutas).
Borra los restos de Ugg si aún existen:

```powershell
Remove-Item templates\components\ugg.html -ErrorAction SilentlyContinue
Remove-Item static\js\ugg.js -ErrorAction SilentlyContinue
```

No hay migraciones nuevas ni comandos de carga.
Presiona Ctrl + F5 (estilos.css ahora carga con ?v=5).

## 2. Qué cambió
| Pedido | Dónde |
|---|---|
| «Evaluar ahora» se quedaba tieso | `captura-camara.js` (`evaluar`: estado «Evaluando…», aviso si no hay frame, reactivación en `finally`, error de conexión visible) |
| Acepta sola con más del 70 % durante 2 s | `captura-camara.js` (tiempo con `performance.now()`, se reinicia si baja o cambia la letra), `netbean.py` (`PRACTICA_UMBRAL_AUTO=70`, `PRACTICA_SEGUNDOS_AUTO=2`), `gamificacion/services.py` (`umbral_efectivo`), `reconocimiento/views.py`, `practica.html` |
| Botón apagar/encender cámara | `practica.html` (`btn-apagar`), `captura-camara.js`, `estilos.css` |
| Pruebas | `gamificacion/tests.py` |

## 3. Regla del umbral
El servidor usa `min(puntos_minimos de la seña, 70)`. Si una seña tiene 80 en la base de datos, igual se aprueba con 70.
Para cambiarlo, edita `PRACTICA_UMBRAL_AUTO` en `config/settings/netbean.py`.
El servidor sigue re-prediciendo al evaluar y es el único que da XP; el repaso sigue sin XP.

## 4. Probar
```powershell
pytest
python manage.py runserver
```
Práctica → activa la cámara → mantén la seña 2 s (aparece la barra «Mantén la seña»).
Botón «Apagar cámara»: detiene la cámara sin perder el progreso; «Encender cámara» la reanuda.

## 5. Commits sugeridos
```powershell
git switch -c fix/practica-evaluar-camara
git add static/js/captura-camara.js templates/base.html static/css/estilos.css
git commit -m "fix(practica): estado Evaluando y manejo de errores en Evaluar ahora [HU-05]"
git add apps/reconocimiento config/settings/netbean.py apps/gamificacion
git commit -m "feat(practica): aceptación automática con más de 70 % durante 2 segundos [HU-05]"
git commit --allow-empty -m "feat(practica): botón para apagar y encender la cámara [HU-05]"
```
