import logging
from aiogram import Router
from aiogram.types import ChatJoinRequest
from database.crud import get_telegram_channel_ids

logger = logging.getLogger(__name__)

router = Router()


@router.chat_join_request()
async def approve_join_request(request: ChatJoinRequest):
    """
    "So'rov orqali qo'shilish" (join request) yoqilgan majburiy kanallar uchun:
    foydalanuvchi so'rov yuborganda bot buni avtomatik tasdiqlaydi, shunda u
    darhol haqiqiy a'zoga aylanadi va check_user_subscriptions() oddiy
    get_chat_member tekshiruvi orqali uni "a'zo" deb topa oladi.

    Faqat botning bazasidagi (majburiy) Telegram kanallari uchun ishlaydi —
    bot boshqa joyda admin bo'lsa ham, u yerdagi so'rovlarga tegilmaydi.
    """
    telegram_channel_ids = await get_telegram_channel_ids()
    if request.chat.id not in telegram_channel_ids:
        return

    try:
        await request.approve()
    except Exception as e:
        logger.warning(f"Join request'ni tasdiqlashda xatolik (chat={request.chat.id}, user={request.from_user.id}): {e}")
