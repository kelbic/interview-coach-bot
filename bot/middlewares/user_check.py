from typing import Any, Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from db.session import AsyncSessionLocal
from db.repositories.users import get_or_create_user


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            async with AsyncSessionLocal() as session:
                db_user = await get_or_create_user(
                    session,
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name or "",
                )
                data["db_user"] = db_user
                data["db_session"] = session
                return await handler(event, data)

        return await handler(event, data)
