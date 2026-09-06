"""Menyu tugmalarining markazlashtirilgan matnlari.

Bitta joyda saqlanadi — shunda tugma matni o'zgartirilsa, uni ishlatuvchi
klaviaturalar va matnni qo'lda solishtiruvchi handlerlar (masalan,
app/handlers/users/search.py dagi ignored_buttons) avtomatik sinxron qoladi.
"""

# Asosiy menyu
PERSONAL_CABINET = "👤 Shaxsiy kabinet"
PRO_SUBSCRIPTION = "⭐ PRO Obuna"
ADMIN_PANEL = "⚙️ Admin Panel"

# Umumiy
CANCEL = "❌ Bekor qilish"
BACK_TO_MAIN_MENU = "🔙 Asosiy menyu"

# Admin menyu
ADD_MOVIE = "🎬 Kino qo'shish"
ADD_EPISODE = "📺 Serial qismi qo'shish"
DELETE_MOVIE = "🗑 Kino/Serial o'chirish"
STATISTICS = "📊 Statistika"
CARDS_MANAGEMENT = "💳 Kartalar boshqaruvi"
PRO_PRICE_SETTINGS = "💰 PRO narxini sozlash"
CHANNELS_MANAGEMENT = "📢 Majburiy kanallar"
BROADCAST = "✉️ Xabar tarqatish"
ADMINS_MANAGEMENT = "👥 Adminlar boshqaruvi"

MAIN_MENU_BUTTONS = [PERSONAL_CABINET, PRO_SUBSCRIPTION, ADMIN_PANEL]
ADMIN_MENU_BUTTONS = [
    ADD_MOVIE, ADD_EPISODE, DELETE_MOVIE, STATISTICS,
    CARDS_MANAGEMENT, PRO_PRICE_SETTINGS, CHANNELS_MANAGEMENT,
    BROADCAST, ADMINS_MANAGEMENT, BACK_TO_MAIN_MENU,
]

# Kino kodi qidiruvchi handler shu ro'yxatdagi matnlarni kod deb qabul qilmasligi kerak
ALL_MENU_BUTTONS = frozenset([CANCEL, *MAIN_MENU_BUTTONS, *ADMIN_MENU_BUTTONS])
