import os

from config.settings.base import *  # noqa: F403


DEBUG = False

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
