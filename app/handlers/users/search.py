from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from database.crud import (
    get_movie_by_code, get_movie_by_id, get_seasons_for_movie,
    get_episodes_by_season, get_episode_by_code, async_session
)
from database.models import Episode
from app.state.states import MovieSearchState
from app.utils.subscription import check_user_subscriptions
from app.keyboards.inline.channels import channels_check_keyboard
from app.keyboards.inline.series import seasons_keyboard, episodes_keyboard
from app.keyboards.default.menu import cancel_keyboard, main_menu_keyboard, admin_menu_keyboard
from data.config import ADMINS
from sqlalchemy import select

router = Router()

@router.message(F.text == "🔍 Kino qidirish")
async def search_button_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    is_sub, unsub_channels = await check_user_subscriptions(message.bot, user_id)
    if not is_sub:
        await message.answer(
            text="⚠️ Botdan foydalanish uchun rasmiy kanallarga a'zo bo'ling:",
            reply_markup=channels_check_keyboard(unsub_channels)
        )
        return

    await state.set_state(MovieSearchState.waiting_for_code)
    await message.answer(
        text="🔢 <b>Kino yoki serial kodini kiriting:</b>\n<i>(Masalan: 12, 105, serial nomi kodi)</i>",
        reply_markup=cancel_keyboard()
    )

@router.message(F.text == "❌ Bekor qilish")
async def cancel_search_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    await state.clear()
    is_admin = message.from_user.id in ADMINS
    if is_admin and current_state and any(prefix in current_state for prefix in ["Admin", "Add", "Delete"]):
        await message.answer("❌ Jarayon bekor qilindi.", reply_markup=admin_menu_keyboard())
    else:
        await message.answer("Bosh menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=is_admin))

# Kod orqali qidiruv (ham FSM holatida, ham to'g'ridan-to'g'ri xabar yuborilganda)
@router.message(F.text, ~F.text.startswith("/"))
async def handle_movie_code_input(message: Message, state: FSMContext):
    text = message.text.strip()
    
    # Asosiy va admin tugmalar bosilgan bo'lsa bu handler ishlamaydi
    ignored_buttons = [
        "🔍 Kino qidirish", "👤 Shaxsiy kabinet", "⭐ PRO Obuna", "⚙️ Admin Panel", "❌ Bekor qilish",
        "🎬 Kino qo'shish", "📺 Serial qismi qo'shish", "🗑 Kino/Serial o'chirish", "📊 Statistika",
        "💳 Kartalar boshqaruvi", "💰 PRO narxini sozlash", "📢 Majburiy kanallar", "✉️ Xabar tarqatish",
        "👥 Adminlar boshqaruvi", "🔙 Asosiy menyu"
    ]
    if text in ignored_buttons:
        return

    user_id = message.from_user.id
    is_sub, unsub_channels = await check_user_subscriptions(message.bot, user_id)
    if not is_sub:
        await message.answer(
            text="⚠️ <b>Botdan foydalanish uchun homiy kanallarga a'zo bo'ling:</b>\n\n"
                 "<i>Yoki kanallarga obuna bo'lmasdan ko'rish uchun <b>«⭐ PRO Obuna»</b> sotib oling:</i>",
            reply_markup=channels_check_keyboard(unsub_channels)
        )
        return

    # 1. Kinoni kod bo'yicha tekshiramiz
    movie = await get_movie_by_code(text)
    if movie:
        await state.clear()
        is_admin = user_id in ADMINS
        if movie.media_type == "movie" and movie.file_id:
            bot_info = await message.bot.get_me()
            bot_username = f"@{bot_info.username}" if bot_info.username else "@siuuu7bot"
            caption = f"🎬 <b>{movie.title}</b>\n🔑 Kod: <code>{movie.code}</code>"
            if movie.description:
                caption += f"\n\n📝 {movie.description}"
            caption += f"\n\n🤖 <b>Bizning bot:</b> {bot_username}"
            await message.answer_video(
                video=movie.file_id,
                caption=caption,
                reply_markup=main_menu_keyboard(is_admin=is_admin)
            )
            return
        elif movie.media_type == "series":
            seasons = await get_seasons_for_movie(movie.id)
            if not seasons:
                await message.answer(
                    f"📺 <b>{movie.title}</b> (Serial)\n<i>Hozircha bu serial uchun qismlar yuklanmagan.</i>",
                    reply_markup=main_menu_keyboard(is_admin=is_admin)
                )
                return
            caption = f"📺 <b>{movie.title}</b> (Serial)\n🔑 Kod: <code>{movie.code}</code>"
            if movie.description:
                caption += f"\n\n📝 {movie.description}"
            caption += "\n\n<i>Kerakli faslni tanlang:</i>"
            await message.answer(
                caption,
                reply_markup=seasons_keyboard(movie.id, seasons)
            )
            return

    # 2. To'g'ridan-to'g'ri qism kodi bo'yicha tekshiramiz
    episode = await get_episode_by_code(text)
    if episode:
        await state.clear()
        is_admin = user_id in ADMINS
        bot_info = await message.bot.get_me()
        bot_username = f"@{bot_info.username}" if bot_info.username else "@siuuu7bot"
        caption = f"📺 <b>{episode.movie.title}</b>\n" \
                  f"📁 {episode.season}-Fasl, ▶️ {episode.episode}-qism"
        caption += f"\n\n🤖 <b>Bizning bot:</b> {bot_username}"
        await message.answer_video(
            video=episode.file_id,
            caption=caption,
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return

    # Agar topilmasa
    await message.answer(
        text=f"❌ <b>'{text}'</b> kodli kino yoki serial topilmadi.\n"
             "Kodni to'g'ri kiritganingizga ishonch hosil qiling."
    )

# Serial faslini tanlash callback handler
@router.callback_query(F.data.startswith("season:"))
async def season_select_callback(call: CallbackQuery):
    _, movie_id_str, season_str = call.data.split(":")
    movie_id = int(movie_id_str)
    season = int(season_str)

    movie = await get_movie_by_id(movie_id)
    if not movie:
        await call.answer("Serial topilmadi.", show_alert=True)
        return

    episodes = await get_episodes_by_season(movie_id, season)
    if not episodes:
        await call.answer(f"{season}-Fasl uchun qismlar hali qo'shilmagan.", show_alert=True)
        return

    await call.message.edit_text(
        text=f"📺 <b>{movie.title}</b>\n"
             f"📁 <b>{season}-Fasl</b> qismlari:\n\n<i>Kerakli qismni tanlang:</i>",
        reply_markup=episodes_keyboard(movie_id, season, episodes)
    )
    await call.answer()

# Qismni tanlash va videoni yuborish callback handler
@router.callback_query(F.data.startswith("episode:"))
async def episode_select_callback(call: CallbackQuery):
    _, episode_id_str = call.data.split(":")
    episode_id = int(episode_id_str)

    async with async_session() as session:
        result = await session.execute(
            select(Episode).where(Episode.id == episode_id)
        )
        episode = result.scalar_one_or_none()

    if not episode:
        await call.answer("Qism topilmadi.", show_alert=True)
        return

    movie = await get_movie_by_id(episode.movie_id)
    title = movie.title if movie else "Serial"

    bot_info = await call.bot.get_me()
    bot_username = f"@{bot_info.username}" if bot_info.username else "@siuuu7bot"
    caption = f"📺 <b>{title}</b>\n" \
              f"📁 {episode.season}-Fasl, ▶️ {episode.episode}-qism"
    caption += f"\n\n🤖 <b>Bizning bot:</b> {bot_username}"
    
    await call.answer()
    await call.bot.send_video(
        chat_id=call.from_user.id,
        video=episode.file_id,
        caption=caption
    )

# Fasllar ro'yxatiga qaytish callback handler
@router.callback_query(F.data.startswith("back_to_seasons:"))
async def back_to_seasons_callback(call: CallbackQuery):
    _, movie_id_str = call.data.split(":")
    movie_id = int(movie_id_str)

    movie = await get_movie_by_id(movie_id)
    if not movie:
        await call.answer("Serial topilmadi.", show_alert=True)
        return

    seasons = await get_seasons_for_movie(movie.id)
    caption = f"📺 <b>{movie.title}</b> (Serial)\n🔑 Kod: <code>{movie.code}</code>"
    if movie.description:
        caption += f"\n\n📝 {movie.description}"
    caption += "\n\n<i>Kerakli faslni tanlang:</i>"

    await call.message.edit_text(
        text=caption,
        reply_markup=seasons_keyboard(movie.id, seasons)
    )
    await call.answer()
