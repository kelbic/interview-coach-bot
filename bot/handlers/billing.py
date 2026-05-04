"""Pro subscription via Telegram Stars — same approach as twidgest-bot."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, Message, LabeledPrice,
    PreCheckoutQuery, SuccessfulPayment,
)

from bot.keyboards.inline import upgrade_kb, main_menu_kb
from config import settings
from db.models import User
from db.repositories.users import set_pro
from db.repositories.achievements import grant_achievement
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = Router()

PRO_FEATURES = """💎 <b>Interview Coach Pro</b>

✅ Безлимитные вопросы (Free: 5/день)
✅ Детальный разбор каждого ответа
✅ Эталонный ответ после каждого вопроса
✅ Умная модель (Claude Sonnet vs Haiku)
✅ Полная история всех сессий
✅ Приоритетная очередь генерации

<b>Цена: 280 ⭐ / месяц</b> (~$5)

Telegram Stars покупаются прямо в Telegram.
Никаких карт, никакого KYC."""


@router.message(Command("upgrade"))
@router.callback_query(F.data == "upgrade")
async def show_upgrade(event, db_user: User, **kwargs) -> None:
    is_msg = isinstance(event, Message)

    if db_user.is_pro:
        until_str = ""
        if db_user.pro_until:
            until_str = f"\n\nПодписка активна до: <b>{db_user.pro_until.strftime('%d.%m.%Y')}</b>"
        text = f"✅ У тебя уже есть <b>Pro</b>!{until_str}"
        kb = main_menu_kb()
    else:
        text = PRO_FEATURES
        kb = upgrade_kb()

    if is_msg:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()


@router.callback_query(F.data == "buy_pro")
async def send_invoice(callback: CallbackQuery, db_user: User) -> None:
    if db_user.is_pro:
        await callback.answer("У тебя уже есть Pro! 💎", show_alert=True)
        return

    await callback.message.answer_invoice(
        title="Interview Coach Pro",
        description="Безлимитная практика + детальные разборы на 30 дней",
        payload="pro_subscription_30d",
        currency="XTR",
        prices=[LabeledPrice(label="Pro на 30 дней", amount=settings.PRO_MONTHLY_PRICE_STARS)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message,
    db_user: User,
) -> None:
    payment: SuccessfulPayment = message.successful_payment

    if payment.invoice_payload == "pro_subscription_30d":
        until = datetime.utcnow() + timedelta(days=30)
        async with AsyncSessionLocal() as session:
            await set_pro(session, db_user.id, until)
            await grant_achievement(session, db_user, "pro_user")

        await message.answer(
            "🎉 <b>Добро пожаловать в Pro!</b>\n\n"
            "✅ Безлимитные вопросы\n"
            "✅ Детальные разборы\n"
            "✅ Эталонные ответы\n\n"
            f"Подписка активна до: <b>{until.strftime('%d.%m.%Y')}</b>",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        logger.info("User %d upgraded to Pro until %s", db_user.id, until)
    else:
        await message.answer("Платёж получен, но payload неизвестен. Напишите в поддержку.")
