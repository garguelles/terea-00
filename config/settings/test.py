from config.settings.base import *  # noqa: F403


DEBUG = False

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    },
}
