"""Bayonnoma Telegram boti — ishga tushirish nuqtasi."""
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import db
from config import BASE_DIR, settings
from handlers import routers
from handlers.common import on_error


def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    log_dir = BASE_DIR / "data"
    log_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(log_dir / "bot.log", maxBytes=5_000_000,
                                       backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


async def main() -> None:
    setup_logging()
    log = logging.getLogger("bot")
    if not settings.bot_token:
        log.error("BOT_TOKEN .env faylda ko'rsatilmagan")
        sys.exit(1)
    if not settings.ai_enabled:
        log.warning("ANTHROPIC_API_KEY yo'q — AI matn yozish o'chiq, faqat qo'lda yoziladi")

    await db.init_db()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(*routers)
    dp.errors.register(on_error)

    await bot.set_my_commands([
        BotCommand(command="start", description="Asosiy menyu"),
        BotCommand(command="cancel", description="Bekor qilish"),
        BotCommand(command="help", description="Yordam"),
    ])
    log.info("Bot ishga tushdi")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
