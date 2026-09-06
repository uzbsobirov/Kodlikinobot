from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from database.models import Card, Channel, Admin

def admin_main_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Kino qo'shish", callback_data="admin_add_movie"),
                InlineKeyboardButton(text="📺 Serial qismi qo'shish", callback_data="admin_add_episode")
            ],
            [
                InlineKeyboardButton(text="🗑 Kino/Serial o'chirish", callback_data="admin_delete_movie"),
                InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton(text="💳 Kartalar boshqaruvi", callback_data="admin_cards"),
                InlineKeyboardButton(text="💰 PRO narxini sozlash", callback_data="admin_price")
            ],
            [
                InlineKeyboardButton(text="📢 Majburiy kanallar", callback_data="admin_channels"),
                InlineKeyboardButton(text="✉️ Xabar tarqatish", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton(text="👥 Adminlar boshqaruvi", callback_data="admin_manage_admins")
            ]
        ]
    )

def admin_cards_list_keyboard(cards: List[Card]) -> InlineKeyboardMarkup:
    buttons = []
    for c in cards:
        status_emoji = "🟢" if c.is_active else "🔴"
        holder_info = f" ({c.card_holder})" if c.card_holder else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {c.bank_name} - {c.card_number}{holder_info}",
                callback_data=f"card_info:{c.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Yangi karta qo'shish", callback_data="card_add")])
    buttons.append([InlineKeyboardButton(text="⬅️ Admin panelga qaytish", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_card_action_keyboard(card_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 O'chirish (Nofaol qilish)" if is_active else "🟢 Yoqish (Faollashtirish)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data=f"card_toggle:{card_id}")],
            [InlineKeyboardButton(text="🗑 Kartani butunlay o'chirish", callback_data=f"card_delete:{card_id}")],
            [InlineKeyboardButton(text="⬅️ Kartalar ro'yxatiga qaytish", callback_data="admin_cards")]
        ]
    )

def admin_channels_list_keyboard(channels: List[Channel]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(text=f"📢 {ch.name}", url=ch.invite_link),
            InlineKeyboardButton(text="❌ O'chirish", callback_data=f"channel_del:{ch.channel_id}")
        ])
    buttons.append([InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="channel_add")])
    buttons.append([InlineKeyboardButton(text="⬅️ Admin panelga qaytish", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborishni boshlash", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
            ]
        ]
    )

def admin_admins_list_keyboard(admins: List[Admin], current_user_id: int, env_admins: List[int]) -> InlineKeyboardMarkup:
    keyboard = []
    keyboard.append([InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="admin_add_admin")])
    
    # O'chirilishi mumkin bo'lgan adminlar mavjudligini tekshirish (o'zini va asosiy .env adminlarni o'chirib bo'lmaydi)
    can_delete_any = any(a.telegram_id not in env_admins and a.telegram_id != current_user_id for a in admins)
    if can_delete_any:
        keyboard.append([InlineKeyboardButton(text="🗑 Adminni o'chirish", callback_data="admin_del_menu")])
        
    keyboard.append([InlineKeyboardButton(text="⬅️ Admin panelga qaytish", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_delete_select_keyboard(admins: List[Admin], current_user_id: int, env_admins: List[int]) -> InlineKeyboardMarkup:
    keyboard = []
    for a in admins:
        if a.telegram_id in env_admins or a.telegram_id == current_user_id:
            continue
        name_str = a.full_name or f"ID: {a.telegram_id}"
        keyboard.append([
            InlineKeyboardButton(text=f"❌ {name_str} ({a.telegram_id})", callback_data=f"admin_del_confirm:{a.telegram_id}")
        ])
    keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_manage_admins")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_delete_confirm_keyboard(admin_tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"admin_del_yes:{admin_tg_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_manage_admins")
            ]
        ]
    )

