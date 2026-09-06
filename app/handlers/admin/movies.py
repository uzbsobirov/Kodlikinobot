from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from data.config import ADMINS
from database.crud import (
    add_movie, get_movie_by_code, delete_movie,
    add_episode
)
from aiogram.filters import StateFilter
from app.state.states import AddMovieState, AddEpisodeState, DeleteMovieState
from app.keyboards.default.menu import cancel_keyboard, admin_menu_keyboard, main_menu_keyboard

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS



# Kino yoki Serial qo'shish
async def send_add_movie_menu(user_id: int, bot):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Oddiy Kino", callback_data="addtype:movie"),
                InlineKeyboardButton(text="📺 Serial", callback_data="addtype:series")
            ],
            [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="admin_back")]
        ]
    )
    await bot.send_message(chat_id=user_id, text="Nima qo'shmoqchisiz? Tanlang:", reply_markup=keyboard)

@router.message(F.text == "🎬 Kino qo'shish")
async def start_add_movie_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_add_movie_menu(message.from_user.id, message.bot)

@router.callback_query(F.data == "admin_add_movie")
async def start_add_movie_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await send_add_movie_menu(call.from_user.id, call.bot)
    await call.answer()

@router.callback_query(F.data.startswith("addtype:"))
async def process_movie_type(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    media_type = call.data.split(":")[1]
    await state.update_data(media_type=media_type)

    if media_type == "movie":
        await state.set_state(AddMovieState.waiting_for_video)
        await call.message.delete()
        await call.bot.send_message(
            chat_id=call.from_user.id,
            text="🎥 <b>Kino videosini yuboring</b> (yoki Baza kanaldan forward qiling):",
            reply_markup=cancel_keyboard()
        )
    else:
        await state.set_state(AddMovieState.waiting_for_code)
        await call.message.delete()
        await call.bot.send_message(
            chat_id=call.from_user.id,
            text="📺 <b>Serial uchun unikal kod kiriting:</b>\n<i>(Masalan: 501 yoki kurtlar)</i>",
            reply_markup=cancel_keyboard()
        )
    await call.answer()

# Kino videosini qabul qilish
@router.message(AddMovieState.waiting_for_video, F.video)
async def process_movie_video(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    file_id = message.video.file_id
    await state.update_data(file_id=file_id)
    await state.set_state(AddMovieState.waiting_for_code)
    await message.answer("🔑 <b>Kino uchun unikal kod kiriting:</b>\n<i>(Masalan: 101, avatar2)</i>")

# Kodni qabul qilish (Kino yoki Serial uchun)
@router.message(AddMovieState.waiting_for_code, F.text)
async def process_movie_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    code = message.text.strip().lower()
    existing = await get_movie_by_code(code)
    if existing:
        await message.answer("⚠️ Bu kod band! Iltimos, boshqa kod kiriting:")
        return

    await state.update_data(code=code)
    await state.set_state(AddMovieState.waiting_for_title)
    await message.answer("📝 <b>Kino/Serial nomini kiriting:</b>")

# Nomni qabul qilish
@router.message(AddMovieState.waiting_for_title, F.text)
async def process_movie_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AddMovieState.waiting_for_description)
    await message.answer("📄 <b>Kino/Serial haqida qisqacha tavsif yoki janrini kiriting</b> (agar kerak bo'lmasa '-' yuboring):")

# Tavsifni qabul qilish va saqlash
@router.message(AddMovieState.waiting_for_description, F.text)
async def process_movie_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    description = message.text.strip()
    if description == "-":
        description = None

    data = await state.get_data()
    media_type = data.get("media_type", "movie")
    code = data.get("code")
    title = data.get("title")
    file_id = data.get("file_id")

    movie = await add_movie(
        code=code,
        title=title,
        media_type=media_type,
        file_id=file_id,
        description=description
    )

    await state.clear()
    msg_type = "Kino" if media_type == "movie" else "Serial"
    await message.answer(
        text=f"✅ <b>{msg_type} muvaffaqiyatli saqlandi!</b>\n\n"
             f"🎬 <b>Nomi:</b> {movie.title}\n"
             f"🔑 <b>Kodi:</b> <code>{movie.code}</code>\n"
             f"📂 <b>Turi:</b> {msg_type}",
        reply_markup=admin_menu_keyboard()
    )


# ================= SERIAL QISMI QO'SHISH =================

async def start_add_episode_flow(user_id: int, bot, state: FSMContext):
    await state.set_state(AddEpisodeState.waiting_for_movie_code)
    await bot.send_message(
        chat_id=user_id,
        text="📺 <b>Qaysi serialga qism qo'shmoqchisiz?</b>\nSerial kodini kiriting:",
        reply_markup=cancel_keyboard()
    )

@router.message(F.text == "📺 Serial qismi qo'shish")
async def start_add_episode_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await start_add_episode_flow(message.from_user.id, message.bot, state)

@router.callback_query(F.data == "admin_add_episode")
async def start_add_episode_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await start_add_episode_flow(call.from_user.id, call.bot, state)
    await call.answer()

@router.message(AddEpisodeState.waiting_for_movie_code, F.text)
async def process_ep_serial_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    code = message.text.strip().lower()
    movie = await get_movie_by_code(code)
    if not movie:
        await message.answer("⚠️ Bunday kodli serial topilmadi. Qaytadan kod kiriting:")
        return

    if movie.media_type != "series":
        await message.answer(
            f"⚠️ <b>'{movie.title}'</b> ({code}) oddiy kino sifatida saqlangan, serial emas!\n"
            "Qism faqat seriallarga qo'shiladi. Qaytadan serial kodini kiriting:"
        )
        return

    await state.update_data(movie_id=movie.id, movie_title=movie.title, movie_code=movie.code)
    await state.set_state(AddEpisodeState.waiting_for_season)
    await message.answer(f"📁 <b>'{movie.title}'</b> seriali uchun fasl raqamini kiriting (masalan: 1):")

@router.message(AddEpisodeState.waiting_for_season, F.text)
async def process_ep_season(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, fasl raqamini kiriting (masalan: 1):")
        return

    season = int(message.text.strip())
    await state.update_data(season=season)
    await state.set_state(AddEpisodeState.waiting_for_episode)
    await message.answer("▶️ <b>Qism raqamini kiriting</b> (masalan: 1):")

@router.message(AddEpisodeState.waiting_for_episode, F.text)
async def process_ep_number(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, qism raqamini kiriting (masalan: 1):")
        return

    episode = int(message.text.strip())
    await state.update_data(episode=episode)
    await state.set_state(AddEpisodeState.waiting_for_video)
    await message.answer("🎥 <b>Qism videosini yuboring</b> (yoki Baza kanaldan forward qiling):")

@router.message(AddEpisodeState.waiting_for_video, F.video)
async def process_ep_video(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    file_id = message.video.file_id
    await state.update_data(file_id=file_id)
    await state.set_state(AddEpisodeState.waiting_for_episode_code)
    await message.answer(
        "🔑 <b>Bu qism uchun maxsus kod belgilaysizmi?</b>\n"
        "(To'g'ridan-to'g'ri kod orqali yuklash uchun. Kerak bo'lmasa '-' yuboring):"
    )

@router.message(AddEpisodeState.waiting_for_episode_code, F.text)
async def process_ep_code_and_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    ep_code = message.text.strip().lower()
    if ep_code == "-":
        ep_code = None

    data = await state.get_data()
    movie_id = data.get("movie_id")
    movie_title = data.get("movie_title")
    season = data.get("season")
    episode_num = data.get("episode")
    file_id = data.get("file_id")

    ep = await add_episode(
        movie_id=movie_id,
        season=season,
        episode=episode_num,
        file_id=file_id,
        episode_code=ep_code
    )

    await state.clear()
    await message.answer(
        text=f"✅ <b>Qism muvaffaqiyatli qo'shildi!</b>\n\n"
             f"📺 <b>Serial:</b> {movie_title}\n"
             f"📁 <b>Fasl:</b> {season}\n"
             f"▶️ <b>Qism:</b> {episode_num}\n"
             f"🔑 <b>Qism kodi:</b> {ep.episode_code or 'Mavjud emas'}",
        reply_markup=admin_menu_keyboard()
    )


# ================= KINO / SERIAL O'CHIRISH =================

async def start_delete_movie_flow(user_id: int, bot, state: FSMContext):
    await state.set_state(DeleteMovieState.waiting_for_code)
    await bot.send_message(
        chat_id=user_id,
        text="🗑 <b>O'chirmoqchi bo'lgan kino yoki serial kodini kiriting:</b>",
        reply_markup=cancel_keyboard()
    )

@router.message(F.text == "🗑 Kino/Serial o'chirish")
async def start_delete_movie_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await start_delete_movie_flow(message.from_user.id, message.bot, state)

@router.callback_query(F.data == "admin_delete_movie")
async def start_delete_movie_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await start_delete_movie_flow(call.from_user.id, call.bot, state)
    await call.answer()

@router.message(DeleteMovieState.waiting_for_code, F.text)
async def process_delete_movie(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    code = message.text.strip().lower()
    success = await delete_movie(code)
    await state.clear()

    if success:
        await message.answer(
            text=f"✅ <b>'{code}' kodli kino/serial va uning barcha qismlari bazadan o'chirildi.</b>",
            reply_markup=admin_menu_keyboard()
        )
    else:
        await message.answer(
            text=f"❌ <b>'{code}' kodli kino yoki serial topilmadi.</b>",
            reply_markup=admin_menu_keyboard()
        )
