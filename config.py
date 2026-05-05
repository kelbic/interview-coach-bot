import os
from dataclasses import dataclass


@dataclass
class Settings:
    TELEGRAM_BOT_TOKEN: str
    OPENROUTER_API_KEY: str
    ADMIN_USER_ID: int

    FREE_QUESTIONS_TOTAL: int = 20
    PRO_MONTHLY_PRICE_STARS: int = 280  # ~$5 at ~$0.018/star

    DB_PATH: str = "interview_coach.db"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Free tier uses fast/cheap model, Pro gets smarter model
    FREE_MODEL: str = "anthropic/claude-haiku-4-5"
    PRO_MODEL: str = "anthropic/claude-sonnet-4-5"


def _load() -> Settings:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    admin_id = int(os.environ.get("ADMIN_USER_ID", "0"))

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")

    return Settings(
        TELEGRAM_BOT_TOKEN=token,
        OPENROUTER_API_KEY=api_key,
        ADMIN_USER_ID=admin_id,
        FREE_QUESTIONS_PER_DAY=int(os.environ.get("FREE_QUESTIONS_PER_DAY", "5")),
        DB_PATH=os.environ.get("DB_PATH", "interview_coach.db"),
    )


settings = _load()
