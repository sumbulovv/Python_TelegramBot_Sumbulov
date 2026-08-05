#!/bin/bash
set -e

cd tg_bot_calendar/

python manage.py migrate --no-input
python manage.py collectstatic --no-input

exec gunicorn tg_bot_calendar.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}"
