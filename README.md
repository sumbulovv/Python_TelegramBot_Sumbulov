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
