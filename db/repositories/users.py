from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, DailyUsage
from config import settings


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str],
    first_name: str,
) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=user_id, username=username, first_name=first_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update name/username if changed
        user.username = username
        user.first_name = first_name
        await session.commit()
    return user


async def update_streak(session: AsyncSession, user: User) -> bool:
    """Update streak. Returns True if streak increased."""
    today = date.today()
    if user.last_activity_date is None:
        user.streak_days = 1
        user.last_activity_date = today
        await session.commit()
        return True

    diff = (today - user.last_activity_date).days
    if diff == 0:
        return False  # already counted today
    elif diff == 1:
        user.streak_days += 1
    else:
        user.streak_days = 1  # streak broken

    user.last_activity_date = today
    await session.commit()
    return True


async def get_questions_used_today(session: AsyncSession, user_id: int) -> int:
    """Для free-tier: возвращает total вопросов за всё время."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user.total_questions if user else 0


async def increment_daily_usage(session: AsyncSession, user_id: int) -> int:
    """Для совместимости — просто возвращаем total_questions."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user.total_questions if user else 0


async def add_score(session: AsyncSession, user: User, score: int) -> None:
    user.total_score += score
    user.total_questions += 1
    await session.commit()


async def get_leaderboard(session: AsyncSession, limit: int = 10) -> list[User]:
    result = await session.execute(
        select(User)
        .where(User.total_questions >= 5)
        .order_by(desc(User.total_score / (User.total_questions + 1)))
        .limit(limit)
    )
    return list(result.scalars().all())


async def set_pro(session: AsyncSession, user_id: int, until: datetime) -> None:
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_pro=True, pro_until=until)
    )
    await session.commit()
