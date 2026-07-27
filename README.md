Проект: Telegram-бот с функцией календаря
Иван Сумбулов 
sumbulovv
machalka245@gmail.com

## Запуск через Docker Compose

1. Создайте `.env` на основе `.env.example` и укажите `TELEGRAM_TOKEN`.
2. Запустите все сервисы:

```bash
docker compose up --build
```

Админка Django будет доступна на `http://localhost:8000/admin/`.

## Автоматические тесты

Критические узлы покрыты тестами Django `unittest`: логика календаря, встречи,
публичные события, экспорт, REST API и парсинг команд Telegram-бота.

```bash
.venv/bin/python tg_bot_calendar/manage.py test calendar_bot --settings=tg_bot_calendar.test_settings
```

Тесты используют отдельные SQLite-настройки и не требуют запущенного PostgreSQL
или Docker Compose.
