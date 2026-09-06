from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import CallbackQuery
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


async def ensure_subscribed_or_prompt(call: CallbackQuery) -> bool:
    """
    Callback query orqali (masalan, fasl/qism tanlash tugmalari bosilganda)
    foydalanuvchining majburiy kanallarga hali ham a'zoligini tekshiradi.

    Foydalanuvchi kanaldan chiqib ketgan bo'lsa, eski xabardagi tugmalar orqali
    video/qismlarni yuklab olishning oldini olish uchun ishlatiladi — obunani
    faqat matn bilan qidiruvda emas, callbacklarda ham tekshirish kerak.

    Qaytaradi: True — foydalanuvchi a'zo (davom etish mumkin),
               False — a'zo emas (ogohlantirib, qayta obuna klaviaturasi yuborildi).
    """
    # Import shu yerda qilinadi — aylanma import (circular import)ning oldini olish uchun
    from app.keyboards.inline.channels import channels_check_keyboard

    is_sub, unsub_channels = await check_user_subscriptions(call.bot, call.from_user.id)
    if is_sub:
        return True

    await call.answer(
        "⚠️ Botdan foydalanish uchun avval homiy kanallarga a'zo bo'lishingiz kerak!",
        show_alert=True
    )
    prompt_text = "⚠️ <b>Botdan foydalanish uchun homiy kanallarga qayta a'zo bo'ling:</b>"
    try:
        await call.message.edit_text(text=prompt_text, reply_markup=channels_check_keyboard(unsub_channels))
    except Exception:
        await call.message.answer(text=prompt_text, reply_markup=channels_check_keyboard(unsub_channels))
    return False
