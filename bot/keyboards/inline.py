from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎯 Начать собеседование", callback_data="start_interview"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats"),
        InlineKeyboardButton(text="🏆 Лидерборд", callback_data="leaderboard"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Pro-подписка", callback_data="upgrade"),
    )
    return builder.as_markup()


def interview_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤝 HR-интервью", callback_data="type_hr"),
        InlineKeyboardButton(text="💻 Техническое", callback_data="type_tech"),
    )
    builder.row(
        InlineKeyboardButton(text="🔀 Смешанное", callback_data="type_mixed"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu"),
    )
    return builder.as_markup()


def grade_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    grades = ["Junior", "Middle", "Senior", "Lead", "Staff", "Principal"]
    for grade in grades:
        builder.button(text=grade, callback_data=f"grade_{grade}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu"))
    return builder.as_markup()


def during_interview_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Следующий вопрос", callback_data="next_question"),
        InlineKeyboardButton(text="🏁 Завершить", callback_data="finish_interview"),
    )
    return builder.as_markup()


def after_answer_kb(is_pro: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="next_question"),
    )
    if not is_pro:
        builder.row(
            InlineKeyboardButton(text="💎 Детальный разбор (Pro)", callback_data="upgrade_from_session"),
        )
    builder.row(
        InlineKeyboardButton(text="🏁 Завершить сессию", callback_data="finish_interview"),
    )
    return builder.as_markup()


def upgrade_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💎 Купить Pro (280 ⭐)", callback_data="buy_pro"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu"),
    )
    return builder.as_markup()


def confirm_finish_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, завершить", callback_data="confirm_finish"),
        InlineKeyboardButton(text="❌ Продолжить", callback_data="continue_interview"),
    )
    return builder.as_markup()
