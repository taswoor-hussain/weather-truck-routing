"""
Django settings for the Weather-Aware Truck Routing API.

All environment-specific values are read from environment variables (or a local
``.env`` file). See ``.env.example`` for the full list.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# --- Core ---------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-secret-key")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "trips",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Data ---------------------------------------------------------------------

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "truck-routing",
        "OPTIONS": {"MAX_ENTRIES": 20_000},
    }
}

# --- I18N / time --------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static files -------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# The built SPA: hashed assets are served from the site root by WhiteNoise.
FRONTEND_DIST_DIR = Path(env("FRONTEND_DIST_DIR", default=str(REPO_DIR / "frontend" / "dist")))
WHITENOISE_ROOT = FRONTEND_DIST_DIR if FRONTEND_DIST_DIR.exists() else None
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# --- API ----------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "core.api.exception_handler",
    # Protect the free upstream providers from bursts.
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "places": env("THROTTLE_PLACES", default="60/min"),
        "plan": env("THROTTLE_PLAN", default="12/min"),
    },
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# --- Production hardening -----------------------------------------------------

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_REDIRECT_EXEMPT = [r"^api/health$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# --- External providers -------------------------------------------------------

PROVIDERS = {
    "GEOCODING_URL": env("GEOCODING_URL", default="https://photon.komoot.io/api/"),
    # "valhalla" (truck costing, default) or "osrm" (car profile).
    "ROUTING_PROVIDER": env("ROUTING_PROVIDER", default="valhalla"),
    "ROUTING_URL": env("ROUTING_URL", default="https://valhalla1.openstreetmap.de"),
    "WEATHER_URL": env("WEATHER_URL", default="https://api.open-meteo.com/v1/forecast"),
    "HTTP_TIMEOUT_S": env.float("HTTP_TIMEOUT_S", default=20.0),
    "USER_AGENT": env("HTTP_USER_AGENT", default="weather-truck-routing/1.0"),
}

# --- Planning parameters ------------------------------------------------------

PLANNING = {
    "TRUCK_MAX_SPEED_MPH": env.float("TRUCK_MAX_SPEED_MPH", default=65.0),
    # Empty tractor-trailer weight; gross weight = tare + load (used for truck routing).
    "TRUCK_TARE_WEIGHT_LB": env.float("TRUCK_TARE_WEIGHT_LB", default=35_000),
    "ROUTE_OPTIONS": 3,
    "WEATHER_CACHE_TTL_S": env.int("WEATHER_CACHE_TTL_S", default=30 * 60),
    "HEATMAP_HOURS": 48,
}

# --- Logging ------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
