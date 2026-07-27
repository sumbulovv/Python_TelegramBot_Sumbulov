import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SECRET_KEY", "django-insecure-test-key")
os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("POSTGRES_DB", "calendar")
os.environ.setdefault("POSTGRES_USER", "calendar")
os.environ.setdefault("POSTGRES_PASSWORD", "calendar")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("CALENDAR_EXPORT_BASE_URL", "http://testserver")

from .settings import *  # noqa: F401,F403


PROJECT_ROOT = Path(BASE_DIR).parent  # noqa: F405
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(BASE_DIR) / "test.sqlite3",  # noqa: F405
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
