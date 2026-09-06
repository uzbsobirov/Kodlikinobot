from aiogram.types import Message
from aiogram import Router, F
from database.crud import get_user

router = Router()

@router.message(F.text == "👤 Shaxsiy kabinet")
async def profile_handler(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.answer("Foydalanuvchi ma'lumotlari topilmadi. Qaytadan /start bosing.")
        return

    full_name = user.full_name
    username = f"@{user.username}" if user.username else "Mavjud emas"
    joined_date_str = user.joined_date.strftime("%d.%m.%Y %H:%M") if user.joined_date else "Noma'lum"

    if user.is_premium and user.premium_expire_date:
        expire_str = user.premium_expire_date.strftime("%d.%m.%Y %H:%M")
        status_text = f"🌟 <b>PRO (Faol)</b>\n⏳ <b>Amal qilish muddati:</b> {expire_str} gacha"
    else:
        status_text = "👤 <b>Oddiy foydalanuvchi</b> (PRO obuna mavjud emas)"

    profile_text = (
        f"<b>👤 Shaxsiy kabinet</b>\n\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"👤 <b>Ism:</b> {full_name}\n"
        f"🏷 <b>Username:</b> {username}\n"
        f"📅 <b>Ro'yxatdan o'tgan sana:</b> {joined_date_str}\n\n"
        f"💎 <b>Obuna holati:</b>\n{status_text}\n\n"
        f"<i>💡 PRO obuna bilan botdan cheklovlarsiz va qulay foydalanishingiz mumkin!</i>"
    )

    await message.answer(text=profile_text)
