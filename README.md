# 0to160 Telegram Bot

## Деплой на Railway (5 минут)

### 1. Подготовка
Загрузи эти 3 файла в новый репозиторий на GitHub:
- `bot.py`
- `requirements.txt`
- `Procfile`

### 2. Railway
1. Зайди на [railway.app](https://railway.app) → войди через GitHub
2. Нажми **New Project → Deploy from GitHub repo**
3. Выбери репозиторий с ботом
4. Перейди в **Variables** и добавь две переменные:

```
TELEGRAM_TOKEN = токен от @BotFather
ANTHROPIC_API_KEY = твой ключ от console.anthropic.com
```

5. Railway сам запустит бота. Статус "Active" = бот работает.

### Где взять ключи
- **TELEGRAM_TOKEN** — напиши @BotFather, команда /newbot (или используй существующий токен)
- **ANTHROPIC_API_KEY** — console.anthropic.com → API Keys → Create Key

### Проверка
Открой бота в Telegram и напиши /start.

---

## Что умеет бот

1. **Мини-тест** — 5 вопросов по словарному запасу, грамматике и знанию формата DET. После теста — персональный анализ слабых мест и предложение купить курс.

2. **AI-консультант** — отвечает на любые вопросы про DET, органично упоминает курс.

3. **О курсе** — описание и ссылка на оплату.

## Обновление бота
Просто запушь изменения в GitHub — Railway пересоберёт автоматически.
