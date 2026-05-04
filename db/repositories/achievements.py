from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Achievement, User

# Achievement definitions: key -> (emoji, title, description, condition_hint)
ACHIEVEMENTS: dict[str, tuple[str, str, str]] = {
    "first_answer":     ("🎯", "Первый шаг", "Ответил на первый вопрос"),
    "first_ten":        ("🔟", "Разгон", "Ответил на 10 вопросов"),
    "fifty_questions":  ("🏆", "Марафонец", "Ответил на 50 вопросов"),
    "perfect_score":    ("💯", "Перфекционист", "Получил 100 баллов за ответ"),
    "high_avg":         ("⭐", "Эксперт", "Средний балл выше 80"),
    "hr_master":        ("🤝", "HR-магнит", "Прошёл 20 HR-вопросов"),
    "tech_master":      ("💻", "Tech Lead", "Прошёл 20 технических вопросов"),
    "streak_3":         ("🔥", "На волне", "3 дня подряд"),
    "streak_7":         ("🌟", "Огонь", "7 дней подряд"),
    "streak_30":        ("🚀", "Легенда", "30 дней подряд"),
    "pro_user":         ("💎", "Pro-игрок", "Подключил Pro-подписку"),
}


async def get_user_achievements(session: AsyncSession, user_id: int) -> set[str]:
    result = await session.execute(
        select(Achievement.key).where(Achievement.user_id == user_id)
    )
    return set(result.scalars().all())


async def grant_achievement(
    session: AsyncSession, user: User, key: str
) -> bool:
    """Grant achievement if not already earned. Returns True if newly earned."""
    existing = await get_user_achievements(session, user.id)
    if key in existing:
        return False
    a = Achievement(user_id=user.id, key=key)
    session.add(a)
    await session.commit()
    return True


async def check_and_grant(
    session: AsyncSession, user: User
) -> list[tuple[str, str, str]]:
    """Check all achievement conditions and grant newly earned ones.
    Returns list of (emoji, title, description) for newly earned."""
    earned = []
    existing = await get_user_achievements(session, user.id)

    checks = {
        "first_answer":    user.total_questions >= 1,
        "first_ten":       user.total_questions >= 10,
        "fifty_questions": user.total_questions >= 50,
        "perfect_score":   False,  # checked inline in evaluator
        "high_avg":        user.total_questions >= 5 and user.average_score >= 80,
        "streak_3":        user.streak_days >= 3,
        "streak_7":        user.streak_days >= 7,
        "streak_30":       user.streak_days >= 30,
        "pro_user":        user.is_pro,
    }

    for key, condition in checks.items():
        if condition and key not in existing:
            new = await grant_achievement(session, user, key)
            if new:
                emoji, title, desc = ACHIEVEMENTS[key]
                earned.append((emoji, title, desc))

    return earned
