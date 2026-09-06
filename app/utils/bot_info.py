from aiogram import Bot

_cached_bot_username: str | None = None


async def get_bot_username(bot: Bot) -> str:
    """
    Botning @username'ini bir marta olib keshda saqlaydi (har video yuborishda
    qo'shimcha get_me() so'rovi yubormaslik uchun).

    Username aniqlanmasa bo'sh satr qaytaradi — chalkashtiruvchi begona bot
    nomi (masalan, boshqa loyihadan qolgan fallback) ko'rsatilmaydi.
    """
    global _cached_bot_username
    if _cached_bot_username is None:
        me = await bot.get_me()
        _cached_bot_username = f"@{me.username}" if me.username else ""
    return _cached_bot_username
