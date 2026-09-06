import asyncio
import logging
from data import config

from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram import Bot, Dispatcher

from database.base import create_tables
from database.crud import init_admins_from_env_and_db
from app import handlers
from middlewares import setup_middlewares
from app.utils.notify_admins import notify_admins
from app.utils.set_bot_commands import set_bot_commands
from app.utils.misc.logging import setup_logger
from app.utils.scheduler import start_background_scheduler

logger = logging.getLogger(__name__)

async def main():
    """
    Asosiy funksiya: botni ishga tushirish, bazani sozlash va handlerlarni ulash
    """
    setup_logger()

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN aniqlanmadi! Iltimos, .env faylida BOT_TOKEN ni ko'rsating.")
        return

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 1. Ma'lumotlar bazasi jadvallarini tekshirish va yaratish
    try:
        await create_tables()
        await init_admins_from_env_and_db()
    except Exception as e:
        logger.error(f"Ma'lumotlar bazasiga ulanishda xatolik: {e}")
        logger.warning("Bot bazasiz to'liq ishlay olmasligi mumkin. .env faylida DB_URL ni tekshiring.")

    # 2. Middlewarelarni ulash
    setup_middlewares(dp)

    # 3. Handlerlarni sozlash
    handlers.setup(dp)

    # 4. Bot komandalarini o'rnatish
    try:
        await set_bot_commands(bot)
    except Exception as e:
        logger.warning(f"Bot komandalarini o'rnatishda xatolik: {e}")

    # 5. Adminlarni xabardor qilish
    try:
        await notify_admins(bot)
    except Exception as e:
        logger.warning(f"Adminlarga xabar yuborishda xatolik: {e}")

    # 6. Orqa fonda obunalarni tekshiruvchi schedulerni ishga tushirish
    asyncio.create_task(start_background_scheduler(bot, interval_seconds=3600))

    # 7. Pollingni boshlash
    logger.info("Bot muvaffaqiyatli ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")