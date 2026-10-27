"""Configuración específica de Net Bean.

Importar al FINAL de config/settings/base.py:

    from .netbean import *  # noqa: E402,F401,F403
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Autenticación (HU-01, HU-02, HU-12) ---
AUTH_USER_MODEL = "usuarios.Usuario"
AUTHENTICATION_BACKENDS = ["apps.usuarios.backends.CorreoBackend"]
LOGIN_URL = "usuarios:login"
LOGIN_REDIRECT_URL = "usuarios:panel"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "apps.usuarios.validators.LetrasYNumerosValidator"},
]

TOKEN_RECUPERACION_MINUTOS = 30

# --- Correo (HU-12: recuperar contraseña) ---
# Sin configurar nada, el correo se IMPRIME en la terminal (modo consola).
# Para enviarlo de verdad, pon EMAIL_BACKEND y las credenciales en el archivo .env (ver LEEME_CORREO.md).
# IMPORTANTE: dev.py no debe definir EMAIL_BACKEND, porque se ejecuta después y lo pisaría.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"   # puerto 587
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"  # puerto 465 (usar con EMAIL_USE_TLS=False)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").replace(" ", "")  # la clave de Gmail se copia con espacios
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL") or (
    f"Net Bean <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "Net Bean <no-responder@netbean.local>"
)
SITE_URL = os.getenv("SITE_URL", "")  # p. ej. http://192.168.1.20:8000 para abrir el enlace desde el celular

# --- Inteligencia artificial (HU-04, HU-05) ---
RUTA_MODELO_TFLITE = BASE_DIR / "ia" / "modelos" / "modelo_v1.tflite"
RUTA_ETIQUETAS = BASE_DIR / "ia" / "modelos" / "etiquetas_v1.txt"
RUTA_HAND_LANDMARKER = BASE_DIR / "ia" / "modelos" / "hand_landmarker.task"
IA_NORMALIZACION = os.getenv("IA_NORMALIZACION", "ninguna")  # EfficientNetB2 normaliza internamente
IA_MARGEN_ROI = 0.15  # lado del recorte = 1.3 x mano (igual que el repo)
IA_ESPEJAR_FRAME = os.getenv("IA_ESPEJAR_FRAME", "False") == "True"

# --- Gamificación (HU-06, HU-07) ---
XP_POR_ACIERTO = 30
XP_ENFRIAMIENTO_SEGUNDOS = 10  # evita sumar XP repetido por la misma seña en ráfaga

# Práctica: aceptación automática (precisión mínima mantenida durante N segundos)
PRACTICA_UMBRAL_AUTO = 70      # % mínimo de precisión para aprobar una seña
PRACTICA_SEGUNDOS_AUTO = 2     # segundos continuos por encima del umbral
