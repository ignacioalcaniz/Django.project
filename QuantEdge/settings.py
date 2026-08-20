"""
Django settings for QuantEdge project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = (
    os.getenv("DJANGO_SECRET_KEY")
    or "django-insecure-wxyz%!sqilxeg)8nx*9hcz8w2x-t37@9rq+%p_xfbg06pqj%hg"
)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "vistaprevia.apps.VistapreviaConfig",
    "usuarios.apps.UsuariosConfig",
    "core.apps.CoreConfig",
    "contacto.apps.ContactoConfig",

    "captcha",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLS / WSGI
# ============================================================

ROOT_URLCONF = "QuantEdge.urls"

WSGI_APPLICATION = "QuantEdge.wsgi.application"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.admin_metrics",
            ],
        },
    },
]


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",

        "NAME": os.getenv(
            "DB_NAME",
            "quantedge_db",
        ),

        "USER": os.getenv(
            "DB_USER",
            "quantedge_user",
        ),

        "PASSWORD": os.getenv(
            "DB_PASSWORD",
            "123456",
        ),

        "HOST": os.getenv(
            "DB_HOST",
            "localhost",
        ),

        "PORT": os.getenv(
            "DB_PORT",
            "3306",
        ),

        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "es-ar"

TIME_ZONE = "America/Argentina/Cordoba"

USE_I18N = True

USE_TZ = False


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static_dev",
]


# ============================================================
# MEDIA
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# AUTHENTICATION
# ============================================================

LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "/usuarios/dashboard/"

LOGOUT_REDIRECT_URL = "/accounts/login/"


# ============================================================
# TWELVE DATA
# ============================================================

TWELVE_DATA_API_KEY = os.getenv(
    "TWELVE_DATA_API_KEY",
    "",
)

TWELVE_DATA_BASE_URL = os.getenv(
    "TWELVE_DATA_BASE_URL",
    "https://api.twelvedata.com",
)

TWELVE_DATA_TIMEOUT = int(
    os.getenv(
        "TWELVE_DATA_TIMEOUT",
        "10",
    )
)


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

