from aiogram.types import Message
from aiogram import Router
from aiogram.filters.command import CommandStart, CommandObject
from database.crud import get_or_create_user, get_movie_by_code, get_episode_by_code, get_seasons_for_movie
from app.utils.subscription import check_user_subscriptions
from app.keyboards.inline.channels import channels_check_keyboard
from app.keyboards.default.menu import main_menu_keyboard
from app.keyboards.inline.series import seasons_keyboard
from data.config import ADMINS

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    user_id = message.from_user.id
    full_name = message.from_user.full_name or ""
    username = message.from_user.username

    # Foydalanuvchini bazada yaratish yoki yangilash
    await get_or_create_user(telegram_id=user_id, full_name=full_name, username=username)

    # Majburiy obunani tekshirish
    is_subscribed, unsub_channels = await check_user_subscriptions(message.bot, user_id)
    if not is_subscribed:
        await message.answer(
            text="👋 <b>Assalomu alaykum!</b>\n\n"
                 "Botdan foydalanish uchun quyidagi homiy kanallarga a'zo bo'ling va "
                 "<b>«✅ Obunani tekshirish»</b> tugmasini bosing:\n\n"
                 "<i>Yoki kanallarga obuna bo'lmasdan darhol ko'rish uchun <b>«⭐ PRO Obuna»</b> sotib oling:</i>",
            reply_markup=channels_check_keyboard(unsub_channels)
        )
        return

    is_admin = user_id in ADMINS

    # Deep linking orqali kino kodi kelsa (masalan: /start 105)
    code = command.args
    if code:
        code = code.strip()
        bot_info = await message.bot.get_me()
        bot_username = f"@{bot_info.username}" if bot_info.username else "@siuuu7bot"
        movie = await get_movie_by_code(code)
        if movie:
            if movie.media_type == "movie" and movie.file_id:
                caption = f"🎬 <b>{movie.title}</b>\n🔑 Kod: <code>{movie.code}</code>"
                if movie.description:
                    caption += f"\n\n📝 {movie.description}"
                caption += f"\n\n🤖 <b>Bizning bot:</b> {bot_username}"
                await message.answer_video(video=movie.file_id, caption=caption)
                return
            elif movie.media_type == "series":
                seasons = await get_seasons_for_movie(movie.id)
                caption = f"📺 <b>{movie.title}</b> (Serial)\n🔑 Kod: <code>{movie.code}</code>"
                if movie.description:
                    caption += f"\n\n📝 {movie.description}"
                caption += "\n\n<i>Kerakli faslni tanlang:</i>"
                await message.answer(caption, reply_markup=seasons_keyboard(movie.id, seasons))
                return
        
        # Agar to'g'ridan-to'g'ri qism kodi bo'lsa
        episode = await get_episode_by_code(code)
        if episode:
            caption = f"📺 <b>{episode.movie.title}</b>\n" \
                      f"📁 {episode.season}-Fasl, ▶️ {episode.episode}-qism"
            caption += f"\n\n🤖 <b>Bizning bot:</b> {bot_username}"
            await message.answer_video(video=episode.file_id, caption=caption)
            return

    # Asosiy menyu
    await message.answer(
        text=f"👋 <b>Assalomu alaykum, {full_name}!</b>\n\n"
             "🎬 <b>Kodlikino botiga xush kelibsiz.</b>\n"
             "Kino yoki serialni tomosha qilish uchun uning <b>kodini yuboring</b> (masalan: 1, 105):",
        reply_markup=main_menu_keyboard(is_admin=is_admin)
    )
