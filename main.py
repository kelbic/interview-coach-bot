import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db.session import init_db
from bot.handlers import start, interview, stats, billing, profile
from bot.middlewares.user_check import UserMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middlewares
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # Routers
    dp.include_router(start.router)
    dp.include_router(interview.router)
    dp.include_router(stats.router)
    dp.include_router(billing.router)
    dp.include_router(profile.router)

    logger.info("Starting Interview Coach Bot...")
    await bot.set_my_commands([
        BotCommand(command="start",       description="Главное меню"),
        BotCommand(command="stop",        description="Остановить текущую сессию"),
        BotCommand(command="stats",       description="Моя статистика"),
        BotCommand(command="profile",     description="Профиль и достижения"),
        BotCommand(command="leaderboard", description="Таблица лидеров"),
        BotCommand(command="upgrade",     description="Pro-подписка"),
        BotCommand(command="help",        description="Помощь"),
    ])
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
