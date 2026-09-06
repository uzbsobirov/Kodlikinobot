from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from database.models import Channel

def channels_check_keyboard(channels: List[Channel]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch.name}", url=ch.invite_link)])
    
    # Kanallarga a'zo bo'lmasdan PRO orqali foydalanish tugmasi
    buttons.append([InlineKeyboardButton(text="⭐ PRO Obuna (Kanallarsiz ko'rish)", callback_data="buy_pro_from_sub")])
    buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
