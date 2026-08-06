import os

from config.settings.base import *  # noqa: F403


DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
