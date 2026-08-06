import os

from config.settings.base import *  # noqa: F403


DEBUG = False

ALLOWED_HOSTS = [*ALLOWED_HOSTS, "healthcheck.railway.app"]  # noqa: F405

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_HSTS_SECONDS = int(
    os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.environ.get("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower()
    == "true"
)
SECURE_HSTS_PRELOAD = (
    os.environ.get("DJANGO_SECURE_HSTS_PRELOAD", "true").lower() == "true"
)

DEFAULT_FROM_EMAIL = os.environ["DJANGO_DEFAULT_FROM_EMAIL"]

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": os.environ["DJANGO_EMAIL_HOST"],
            "port": int(os.environ.get("DJANGO_EMAIL_PORT", "587")),
            "username": os.environ.get("DJANGO_EMAIL_USERNAME", ""),
            "password": os.environ.get("DJANGO_EMAIL_PASSWORD", ""),
            "use_tls": os.environ.get("DJANGO_EMAIL_USE_TLS", "true").lower()
            == "true",
            "use_ssl": os.environ.get("DJANGO_EMAIL_USE_SSL", "false").lower()
            == "true",
            "timeout": int(os.environ.get("DJANGO_EMAIL_TIMEOUT", "10")),
        },
    },
}
