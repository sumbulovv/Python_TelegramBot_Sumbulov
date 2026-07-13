import os
import sys
from pathlib import Path

import django
from django.apps import apps


def setup_django():
    django_project_dir = Path(__file__).resolve().parent / "tg_bot_calendar"
    django_project_path = str(django_project_dir)

    if django_project_path not in sys.path:
        sys.path.insert(0, django_project_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tg_bot_calendar.settings")

    if not apps.ready:
        django.setup()
