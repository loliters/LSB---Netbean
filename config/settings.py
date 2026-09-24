from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-clave-local-desarrollo'
)

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.usuarios',     
    'apps.contenido', 
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


WSGI_APPLICATION = 'config.wsgi.application'


# =========================
# DATABASE - POSTGRESQL
# =========================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


# =========================
# USUARIO PERSONALIZADO
# =========================

AUTH_USER_MODEL = 'usuarios.Usuario'

AUTHENTICATION_BACKENDS = [
    'apps.usuarios.backends.CorreoBackend',
]

# =========================
# PASSWORD
# =========================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =========================
# INTERNATIONALIZATION
# =========================

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/La_Paz'

USE_I18N = True
USE_TZ = True


# =========================
# STATIC
# =========================

# =========================
# STATIC
# =========================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']    # ← ESTA LÍNEA FALTA
STATIC_ROOT = BASE_DIR / 'staticfiles'


# =========================
# MEDIA
# =========================

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =========================
# TEMPLATES
# =========================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =========================
# EMAIL
# =========================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =========================
# AUTENTICACIÓN
# =========================

LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/contenido/modulos/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'

# Seguridad de sesión
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 8   # 8 horas

CSRF_COOKIE_HTTPONLY = False  # necesario para el token en forms AJAX