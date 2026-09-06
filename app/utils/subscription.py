from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from database.crud import get_all_channels, get_user
from data.config import ADMINS
import logging

logger = logging.getLogger(__name__)

async def check_user_subscriptions(bot: Bot, user_id: int) -> tuple[bool, list]:
    """
    Foydalanuvchining majburiy kanallarga a'zoligini tekshiradi.
    Qaytaradi: (barcha_kanallarga_azo: bool, a_zo_bolmagan_kanallar: list)
    """
    # Adminlar va PRO foydalanuvchilar tekshirilmaydi
    if user_id in ADMINS:
        return True, []
    
    user = await get_user(user_id)
    if user and user.is_premium:
        return True, []

    channels = await get_all_channels()
    if not channels:
        return True, []

    unsubscribed_channels = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                unsubscribed_channels.append(channel)
        except Exception as e:
            logger.warning(f"Kanal a'zoligini tekshirishda xatolik ({channel.channel_id}): {e}")
            # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa, foydalanuvchini bloklamaslik
            continue

    if unsubscribed_channels:
        return False, unsubscribed_channels
    return True, []
