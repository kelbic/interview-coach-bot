from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import main_menu_kb
from db.models import User

router = Router()

WELCOME_TEXT = """👋 Привет, {name}!

Я — <b>AI Interview Coach</b> 🤖

Симулирую реальные собеседования на позиции Backend/Fullstack разработчика.

<b>Что я умею:</b>
🎯 Задаю вопросы под твою роль и грейд
📊 Оцениваю каждый ответ (0–100 баллов)
💬 Даю конкретный фидбек
🔥 Отслеживаю стрик и прогресс

<b>Бесплатно:</b> 5 вопросов в день
<b>Pro:</b> безлимит + детальные разборы

Выбери действие:"""

STATS_PREVIEW = """
📈 <b>Твой прогресс:</b>
• Вопросов отвечено: {total_q}
• Средний балл: {avg_score}
• Стрик: {streak} 🔥
• Готовность к собесу: {readiness}%"""


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, state: FSMContext) -> None:
    await state.clear()
    stats = ""
    if db_user.total_questions > 0:
        stats = STATS_PREVIEW.format(
            total_q=db_user.total_questions,
            avg_score=db_user.average_score,
            streak=db_user.streak_days,
            readiness=db_user.readiness_pct,
        )

    await message.answer(
        WELCOME_TEXT.format(name=db_user.first_name) + stats,
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, db_user: User, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        f"Главное меню, {db_user.first_name}:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        f"Главное меню, {db_user.first_name}:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
