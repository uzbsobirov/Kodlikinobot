from aiogram.types import Message
from aiogram import Router
from aiogram.filters.command import Command

router = Router()

@router.message(Command(commands=["help"]))
async def help_command(message: Message):
    text = (
        "<b>📖 Kodlikino Bot — Foydalanish bo'yicha qo'llanma</b>\n\n"
        "🔹 <b>Kino yoki serial tomosha qilish:</b>\n"
        "Botga kinoning maxsus kodini yuboring (masalan: <code>101</code>). Agar bu serial bo'lsa, "
        "Fasl va Qismlarni tugmalar orqali tanlashingiz mumkin.\n\n"
        "🔹 <b>Majburiy obuna:</b>\n"
        "Botdan bepul foydalanish uchun rasmiy homiy kanallarga a'zo bo'lish talab etiladi.\n\n"
        "🔹 <b>⭐ PRO (Premium) Obuna:</b>\n"
        "PRO a'zolar uchun barcha homiy kanallar va cheklovlar o'chiriladi. "
        "«⭐ PRO Obuna» bo'limi orqali to'lov qilib xarid qilishingiz mumkin.\n\n"
        "🔹 <b>Buyruqlar:</b>\n"
        "/start — Botni yangilash va bosh menyu\n"
        "/help — Ushbu yordam xabari"
    )
    await message.answer(text)