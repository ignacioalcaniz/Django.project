"""
Django settings for QuantEdge project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# SECURITY
# ============================================================

DEBUG = os.getenv("DJANGO_DEBUG", "False").strip().lower() == "true"

SECRET_KEY = (
    os.getenv("DJANGO_SECRET_KEY")
    or "django-insecure-wxyz%!sqilxeg)8nx*9hcz8w2x-t37@9rq+%p_xfbg06pqj%hg"
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]


if not DEBUG:
    for variable in ("DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DB_PASSWORD"):
        value = os.getenv(variable, "").strip()
        if not value or value.startswith("REEMPLAZAR_"):
            raise ImproperlyConfigured(f"{variable} must be configured when DJANGO_DEBUG=False.")
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Configure explicit DJANGO_ALLOWED_HOSTS for production.")


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
    "django.contrib.sitemaps",

    # Third-party
    "rest_framework",
    "captcha",

    # QuantEdge
    "vistaprevia.apps.VistapreviaConfig",
    "usuarios.apps.UsuariosConfig",
    "pagos.apps.PagosConfig",
    "core.apps.CoreConfig",
    "contacto.apps.ContactoConfig",
    "api.apps.ApiConfig",
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
                "core.context_processors.seo",
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
            "123456" if DEBUG else "",
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
            **({"init_command": "SET SESSION sql_mode = CONCAT_WS(',', @@sql_mode, 'STRICT_TRANS_TABLES')"}
               if os.getenv("DB_STRICT_MODE", "True").lower() == "true" else {}),
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

STATIC_ROOT = BASE_DIR / "staticfiles"

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
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        (
            "rest_framework.authentication."
            "SessionAuthentication"
        ),
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],

    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),

    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {"quantitative": "120/min"},
    # Never trust client-supplied X-Forwarded-For for rate-limit identity.
    # Behind the local proxy anonymous requests share its budget; authenticated
    # requests are scoped by user. LocMem counters remain per worker.
    "NUM_PROXIES": 0,

    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}


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


# Checkout Pro demo: disabled until explicitly configured, production forbidden.
MERCADOPAGO_ENABLED = os.getenv("MERCADOPAGO_ENABLED", "False").lower() == "true"
MERCADOPAGO_ENVIRONMENT = os.getenv("MERCADOPAGO_ENVIRONMENT", "test")
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")
MERCADOPAGO_PUBLIC_BASE_URL = os.getenv("MERCADOPAGO_PUBLIC_BASE_URL", "")
MERCADOPAGO_DEMO_AMOUNT_ARS = os.getenv("MERCADOPAGO_DEMO_AMOUNT_ARS", "")
