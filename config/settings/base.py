import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.usuarios',
    'apps.contenido',
    'apps.core',
    'apps.progreso',
    "apps.gamificacion.apps.GamificacionConfig",
    'apps.reportes',
    'apps.reconocimiento',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Autenticación
#AUTH_USER_MODEL = 'usuarios.Usuario'
#AUTHENTICATION_BACKENDS = [
#    'apps.usuarios.backends.CorreoBackend',
#    'django.contrib.auth.backends.ModelBackend',
#]
#LOGIN_URL = 'usuarios:login'
#LOGIN_REDIRECT_URL = 'usuarios:panel_estudiante'

# Inteligencia Artificial
#RUTA_MODELO_TFLITE = BASE_DIR / 'ia' / 'modelos' / 'modelo_v1.tflite'
#RUTA_ETIQUETAS = BASE_DIR / 'ia' / 'modelos' / 'etiquetas_v1.txt'
#UMBRAL_CONFIANZA = 0.70
#TAMANO_ENTRADA_MODELO = (224, 224)

# Gamificación
#XP_POR_ACIERTO = 30
from .netbean import *  # noqa: E402,F401,F403