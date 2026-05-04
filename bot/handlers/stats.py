from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from bot.keyboards.inline import main_menu_kb
from db.models import User
from db.repositories.users import get_leaderboard
from db.repositories.achievements import ACHIEVEMENTS, get_user_achievements
from db.session import AsyncSessionLocal

router = Router()

MEDALS = ["🥇", "🥈", "🥉"] + ["🏅"] * 7


def _progress_bar(pct: int, length: int = 10) -> str:
    filled = round(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)


@router.message(Command("stats"))
@router.callback_query(F.data == "my_stats")
async def show_stats(event, db_user: User, db_session, **kwargs) -> None:
    is_msg = isinstance(event, Message)

    earned = await get_user_achievements(db_session, db_user.id)
    ach_text = ""
    if earned:
        lines = []
        for key in earned:
            if key in ACHIEVEMENTS:
                e, t, d = ACHIEVEMENTS[key]
                lines.append(f"  {e} {t}")
        ach_text = "\n<b>🏆 Достижения:</b>\n" + "\n".join(lines)

    progress = _progress_bar(db_user.readiness_pct)

    text = (
        f"📊 <b>Статистика {db_user.first_name}</b>\n\n"
        f"📝 Вопросов отвечено: <b>{db_user.total_questions}</b>\n"
        f"⭐ Средний балл: <b>{db_user.average_score}/100</b>\n"
        f"🔥 Стрик: <b>{db_user.streak_days} дней</b>\n"
        f"💎 Тариф: <b>{'Pro' if db_user.is_pro else 'Free'}</b>\n\n"
        f"<b>🎯 Готовность к собесу:</b>\n"
        f"{progress} <b>{db_user.readiness_pct}%</b>"
        f"{ach_text}"
    )

    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(text="🏆 Лидерборд", callback_data="leaderboard"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu"),
    )

    if is_msg:
        await event.answer(text, parse_mode="HTML", reply_markup=kb_builder.as_markup())
    else:
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb_builder.as_markup())
        await event.answer()


@router.callback_query(F.data == "leaderboard")
@router.message(Command("leaderboard"))
async def show_leaderboard(event, db_user: User, db_session, **kwargs) -> None:
    is_msg = isinstance(event, Message)

    async with AsyncSessionLocal() as s:
        top = await get_leaderboard(s, limit=10)

    if not top:
        text = "🏆 Лидерборд пока пуст.\nСтань первым — начни тренировку!"
    else:
        lines = ["🏆 <b>Топ-10 (анонимно)</b>\n"]
        for i, u in enumerate(top):
            medal = MEDALS[i] if i < len(MEDALS) else "🏅"
            name = u.username or u.first_name or "Аноним"
            # Anonymize: show only first 2 chars
            anon = name[:2] + "***"
            mark = " ← ты" if u.id == db_user.id else ""
            lines.append(
                f"{medal} {anon} — {u.average_score:.0f}/100 "
                f"({u.total_questions} вопр.){mark}"
            )
        text = "\n".join(lines)

    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu"),
    )

    if is_msg:
        await event.answer(text, parse_mode="HTML", reply_markup=kb_builder.as_markup())
    else:
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb_builder.as_markup())
        await event.answer()
