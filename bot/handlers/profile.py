from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from db.models import User
from db.repositories.achievements import ACHIEVEMENTS, get_user_achievements

router = Router()


@router.message(Command("profile"))
async def show_profile(message: Message, db_user: User, db_session) -> None:
    earned = await get_user_achievements(db_session, db_user.id)
    total_ach = len(ACHIEVEMENTS)
    earned_count = len(earned)

    pro_str = "✅ Pro" if db_user.is_pro else "🆓 Free (5 вопросов/день)"

    ach_lines = []
    for key, (emoji, title, desc) in ACHIEVEMENTS.items():
        if key in earned:
            ach_lines.append(f"✅ {emoji} <b>{title}</b> — {desc}")
        else:
            ach_lines.append(f"🔒 {emoji} {title} — {desc}")

    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"Имя: {db_user.first_name}\n"
        f"Тариф: {pro_str}\n\n"
        f"<b>🏆 Достижения {earned_count}/{total_ach}:</b>\n"
        + "\n".join(ach_lines)
    )

    await message.answer(text, parse_mode="HTML")


@router.message(Command("help"))
async def show_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Команды:</b>\n\n"
        "/start — главное меню\n"
        "/profile — профиль и достижения\n"
        "/stats — твоя статистика\n"
        "/leaderboard — таблица лидеров\n"
        "/upgrade — Pro-подписка\n"
        "/help — эта справка\n\n"
        "Просто нажми <b>🎯 Начать собеседование</b> и выбери:\n"
        "• Роль (Python Backend, Fullstack и т.д.)\n"
        "• Грейд (Junior → Principal)\n"
        "• Компанию (опционально)\n"
        "• Тип: HR, тех. или смешанное\n"
        "• Описание вакансии (опционально)\n\n"
        "После каждого ответа получаешь оценку 0–100 и конкретный фидбек.",
        parse_mode="HTML",
    )
