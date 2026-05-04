# 🎯 Interview Coach Bot

Telegram-бот для симуляции реальных IT-собеседований с AI-оценкой ответов, геймификацией и Pro-подпиской.

## Stack

- **Python 3.12+** · **aiogram 3.x** · **SQLite + SQLAlchemy 2 async** · **OpenRouter (Claude)**  
- **Telegram Stars** billing · **systemd** deployment  
- Тот же stack, что у [twidgest-bot](https://github.com/kelbic/twidgest-bot)

## Фичи

| Фича | Free | Pro |
|------|------|-----|
| HR-вопросы | ✅ 5/день | ✅ Безлимит |
| Технические вопросы | ✅ 5/день | ✅ Безлимит |
| Оценка ответа (0–100) | ✅ | ✅ |
| Краткий фидбек | ✅ | ✅ |
| Детальный разбор | ❌ | ✅ |
| Эталонный ответ | ❌ | ✅ |
| Умная модель (Sonnet) | ❌ | ✅ |
| Стрик и достижения | ✅ | ✅ |
| Лидерборд | ✅ | ✅ |

## Геймификация

- **Score 0–100** за каждый ответ
- **Прогресс-бар** «Готовность к собесу» (0–100%)
- **Стрик** — дней подряд с практикой
- **11 достижений**: марафонец, перфекционист, огонь и др.
- **Анонимный лидерборд** по среднему баллу

## Быстрый запуск

```bash
git clone <repo> && cd interview-coach-bot
cp .env.example .env
# Заполни .env: TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, ADMIN_USER_ID

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python main.py
```

## Деплой (systemd, как twidgest-bot)

```bash
# 1. Скопируй проект
sudo cp -r . /opt/interview-coach-bot
sudo cp .env /opt/interview-coach-bot/.env

# 2. Создай venv на сервере
cd /opt/interview-coach-bot
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 3. Systemd
sudo cp deploy/interview-coach-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now interview-coach-bot
sudo journalctl -u interview-coach-bot -f
```

## Структура

```
interview-coach-bot/
├── main.py                  # Entry point
├── config.py                # Env config
├── requirements.txt
│
├── bot/
│   ├── handlers/
│   │   ├── start.py         # /start, меню
│   │   ├── interview.py     # Главный флоу собеседования (FSM)
│   │   ├── stats.py         # /stats, лидерборд
│   │   ├── billing.py       # /upgrade, Telegram Stars
│   │   └── profile.py       # /profile, достижения
│   ├── keyboards/inline.py  # Все inline-кнопки
│   └── middlewares/
│       └── user_check.py    # Авто-создание юзера
│
├── core/
│   ├── llm_client.py        # OpenRouter HTTP клиент
│   └── question_gen.py      # Генерация вопросов + оценка ответов
│
├── db/
│   ├── models.py            # SQLAlchemy модели
│   ├── session.py           # Async engine
│   └── repositories/
│       ├── users.py         # Стрик, лимиты, скор
│       ├── sessions.py      # Interview sessions, вопросы
│       └── achievements.py  # Достижения
│
└── deploy/
    └── interview-coach-bot.service
```

## User Flow

```
/start
  → 🎯 Начать собеседование
    → Ввод роли ("Senior Python Backend")
    → Выбор грейда (Junior/Middle/Senior/Lead/...)
    → Ввод компании (или /skip)
    → Тип: HR / Техническое / Смешанное
    → Описание вакансии (или /skip)
    → [Генерация вопроса AI]
    → Ответ пользователя
    → [Оценка AI: 0-100 + фидбек + эталон(Pro)]
    → → Следующий вопрос | Завершить
```

## Монетизация

280 Telegram Stars (~$5) за 30 дней Pro.  
Потенциал: $2,000–15,000 MRR при 400–3,000 активных подписчиков.

## Модели

| Тариф | Модель | Скорость | Качество |
|-------|--------|----------|----------|
| Free  | claude-haiku-4-5 | ~2s | Хорошая |
| Pro   | claude-sonnet-4-5 | ~5s | Отличная |

Обе модели через OpenRouter. Можно переключить в `config.py`.
