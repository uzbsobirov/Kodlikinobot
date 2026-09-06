from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="👤 Shaxsiy kabinet"), KeyboardButton(text="⭐ PRO Obuna")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Kino qo'shish"), KeyboardButton(text="📺 Serial qismi qo'shish")],
            [KeyboardButton(text="🗑 Kino/Serial o'chirish"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="💳 Kartalar boshqaruvi"), KeyboardButton(text="💰 PRO narxini sozlash")],
            [KeyboardButton(text="📢 Majburiy kanallar"), KeyboardButton(text="✉️ Xabar tarqatish")],
            [KeyboardButton(text="👥 Adminlar boshqaruvi"), KeyboardButton(text="🔙 Asosiy menyu")]
        ],
        resize_keyboard=True
    )
