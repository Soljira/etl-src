import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(os.path.join(BASE_DIR.parent, ".env"))

# Add parent directory to sys.path so we can import src modules
import sys
sys.path.insert(0, str(BASE_DIR.parent))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-etl-open-data-ph-gui-key-2026")

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
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

ROOT_URLCONF = "gui.urls"

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

WSGI_APPLICATION = "gui.wsgi.application"

# Parse DATABASE_URL if available
db_url = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/opendata_ph")
# Strip SQLAlchemy driver prefix if present (+pg8000)
if "+pg8000" in db_url:
    db_url = db_url.replace("+pg8000", "")

parsed_url = urlparse(db_url)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed_url.path.lstrip("/") or "opendata_ph",
        "USER": parsed_url.username or "user",
        "PASSWORD": parsed_url.password or "password",
        "HOST": parsed_url.hostname or "localhost",
        "PORT": parsed_url.port or 5432,
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging — ensure src.* pipeline loggers are always visible at INFO level
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # keep src.* loggers alive after Django configures logging
    "formatters": {
        "pipeline": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "pipeline",
        },
    },
    "loggers": {
        # Route all src.* pipeline logs to console at INFO
        "src": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
