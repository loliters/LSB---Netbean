# Cambios visuales y modo repaso

## 1. Copiar archivos
Copia el contenido de esta carpeta sobre tu proyecto (respeta las rutas) y **borra** estos dos archivos:

```powershell
Remove-Item templates\components\ugg.html
Remove-Item static\js\ugg.js
```

## 2. Actualizar datos
```powershell
python manage.py cargar_logros     # «Amigo de Ugg» pasa a llamarse «Diez prácticas»
pytest
```
No hay migraciones nuevas.

## 3. Si sigues viendo la página «sin estilos»
`base.html` ahora carga `estilos.css?v=4` para saltarse la copia vieja del navegador.
Aun así presiona Ctrl + F5. Si usas `collectstatic`, ejecútalo otra vez.

## Qué cambió
| Pedido | Dónde |
|---|---|
| Ugg eliminado | `base.html`, `practica.html`, `panel_estudiante.html`, `captura-camara.js`, `estilos.css` |
| Checklist eliminado | `practica.html`, `captura-camara.js`, `estilos.css` |
| Logros rediseñados | `logros.html`, `components/insignia.html`, `gamificacion/views.py` |
| Perfil rediseñado | `perfil.html` |
| Dashboard rediseñado | `panel_estudiante.html` |
| Seña dominada: aviso y sin XP | `gamificacion/services.py`, `reconocimiento/views.py`, `practica.html`, `captura-camara.js` |

## Regla nueva
Una seña ya dominada se puede volver a practicar, pero el intento no suma XP.
El servidor lo decide (no se puede evitar desde el navegador). El intento sí queda
registrado como práctica y como acierto, y se ve como «Repaso» en la actividad del perfil.

## Commits sugeridos
```powershell
git switch -c feature/HU-11-rediseno-logros-perfil
git add templates/ static/ apps/*/templates/
git commit -m "feat(front): rediseñar dashboard, perfil y logros; quitar Ugg y checklist [HU-11]"
git add apps/gamificacion/ apps/reconocimiento/ apps/usuarios/
git commit -m "feat(gamificacion): repaso de señas dominadas sin XP con aviso previo [HU-07]"
```
