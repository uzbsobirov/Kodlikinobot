import logging
from aiogram import Router
from aiogram.types import ChatJoinRequest, ChatMemberUpdated
from database.crud import get_telegram_channel_ids, upsert_channel_membership

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


@router.chat_member()
async def track_chat_member_status(update: ChatMemberUpdated):
    """
    Foydalanuvchining majburiy kanaldagi a'zolik holati o'zgarganda (qo'shildi,
    chiqdi, chiqarildi) buni bazada kuzatib boradi. Katta (ko'p obunachili)
    kanallarda Telegram get_chat_member() orqali ixtiyoriy foydalanuvchini
    tekshirishni rad etadi ("member list is inaccessible"), shuning uchun
    check_user_subscriptions() shu yerda saqlangan holatga tayanadi.
    """
    telegram_channel_ids = await get_telegram_channel_ids()
    if update.chat.id not in telegram_channel_ids:
        return

    await upsert_channel_membership(
        channel_id=update.chat.id,
        user_id=update.new_chat_member.user.id,
        status=update.new_chat_member.status
    )
