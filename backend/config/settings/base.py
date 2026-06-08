"""
Django base settings for KubeMemory. Loads from .env via django-environ.
"""
from datetime import timedelta
from pathlib import Path

import environ

# backend/
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
env.read_env(ROOT_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me-in-production")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
    "django_extensions",
    "apps.incidents",
    "apps.memory",
    "apps.agents",
    "apps.watcher",
    "apps.mcp_server",
    "apps.chat",
    "apps.clusters",
    "apps.accounts",
    "apps.monitoring",
    "apps.ws",
]

_fernet_key = env("FERNET_KEY", default="")
FERNET_KEYS = [_fernet_key] if _fernet_key else []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.middleware.DisableCSRFForAPI",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="kubememory"),
        "USER": env("POSTGRES_USER", default="kubememory"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    env("CHANNEL_LAYERS_HOST", default="localhost"),
                    env.int("CHANNEL_LAYERS_PORT", default=6379),
                )
            ],
        },
    },
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")

CELERY_TASK_ROUTES = {
    "apps.incidents.tasks.ingest_incident_task": {"queue": "ingest"},
    "apps.incidents.tasks.update_corrective_rag_task": {"queue": "ingest"},
    "apps.incidents.tasks.run_ai_analysis_task": {"queue": "llm"},
    "apps.monitoring.tasks.check_watcher_health": {"queue": "ingest"},
    "apps.monitoring.tasks.prune_old_vectors": {"queue": "ingest"},
    "apps.monitoring.tasks.backup_databases": {"queue": "ingest"},
    "apps.monitoring.tasks.send_notification": {"queue": "ingest"},
}

CELERY_BEAT_SCHEDULE = {
    "check-watcher-health": {
        "task": "apps.monitoring.tasks.check_watcher_health",
        "schedule": 60.0,
    },
    "prune-old-vectors": {
        "task": "apps.monitoring.tasks.prune_old_vectors",
        "schedule": 86400.0,
        "options": {"expires": 3600},
    },
    "backup-databases": {
        "task": "apps.monitoring.tasks.backup_databases",
        "schedule": 86400.0,
        "options": {"expires": 3600},
    },
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://localhost:3000"],
)
# Required for POST from frontend on 5173 (Django 4+ origin check)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "config.permissions.IsAuthenticatedOrPublicPath",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_MINUTES", default=60)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_ROOT = "/app/static"
MEDIA_ROOT = "/app/media"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"

# Security headers (safe for both dev and prod)
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# Logging — structured, no sensitive data
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "apps": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "celery": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}
