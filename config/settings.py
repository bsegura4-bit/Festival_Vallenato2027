"""Configuración del proyecto festival_votaciones."""
import os
from pathlib import Path

from django.contrib.messages import constants as mensajes

BASE_DIR = Path(__file__).resolve().parent.parent


def cargar_env(ruta):
    """Carga las variables del archivo .env."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


cargar_env(BASE_DIR / ".env")


def env(clave, defecto=None):
    return os.environ.get(clave, defecto)


# Seguridad
SECRET_KEY = env("DJANGO_SECRET_KEY", "solo-para-desarrollo-cambiar-en-.env")
DEBUG = env("DJANGO_DEBUG", "True").lower() in ("1", "true", "si", "yes")
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Aplicaciones
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "festival.apps.FestivalConfig",
    "cuentas.apps.CuentasConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "festival.context_processors.edicion_actual",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Base de datos: MySQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", "festival_votaciones"),
        "USER": env("DB_USER", "festival"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {
            "NAME": "test_" + env("DB_NAME", "festival_votaciones"),
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}

# Autenticación
AUTHENTICATION_BACKENDS = [
    "cuentas.backends.CorreoOUsuarioBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "cuentas:login"
LOGIN_REDIRECT_URL = "festival:inicio"
LOGOUT_REDIRECT_URL = "festival:inicio"

# Idioma y zona horaria
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Mensajes con las clases de Bootstrap
MESSAGE_TAGS = {
    mensajes.DEBUG: "secondary",
    mensajes.INFO: "info",
    mensajes.SUCCESS: "success",
    mensajes.WARNING: "warning",
    mensajes.ERROR: "danger",
}
