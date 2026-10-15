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
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Net Bean <no-responder@netbean.local>")
# En dev.py: EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

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