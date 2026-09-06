import asyncio
import logging
from aiogram import Bot
from database.crud import expire_old_premiums

logger = logging.getLogger(__name__)

async def check_expired_premiums_job(bot: Bot):
    """
    Muddati o'tgan PRO obunalarni avtomatik tarzda bekor qilish va
    foydalanuvchiga xabar berish.
    """
    try:
        expired_user_ids = await expire_old_premiums()
        for uid in expired_user_ids:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text="⚠️ <b>Diqqat:</b> Sizning PRO obunangiz muddati tugadi.\n"
                         "Imkoniyatlardan to'liq foydalanish uchun obunani yangilashingiz mumkin."
                )
            except Exception as e:
                logger.debug(f"Foydalanuvchiga xabar yuborib bo'lmadi ({uid}): {e}")
        if expired_user_ids:
            logger.info(f"{len(expired_user_ids)} ta foydalanuvchining PRO obunasi muddati tugadi va bekor qilindi.")
    except Exception as e:
        logger.error(f"check_expired_premiums_job da xatolik: {e}")

async def start_background_scheduler(bot: Bot, interval_seconds: int = 3600):
    """
    Fon vazifasi sifatida har 1 soatda obunalarni tekshiradi.
    """
    while True:
        await check_expired_premiums_job(bot)
        await asyncio.sleep(interval_seconds)
