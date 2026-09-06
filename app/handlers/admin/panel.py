from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from data.config import ADMINS
from database.crud import (
    get_users_count, get_premium_users_count, get_movies_count,
    get_pro_price, set_pro_price,
    get_total_revenue, get_approved_payments_count, get_approved_payments_history
)
from aiogram.filters import StateFilter
from app.keyboards.default.menu import cancel_keyboard, main_menu_keyboard, admin_menu_keyboard
from app.state.states import AdminPriceState

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

@router.message(StateFilter("*"), F.text.in_(["❌ Bekor qilish", "🔙 Asosiy menyu"]))
async def admin_panel_cancel_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        if message.text == "🔙 Asosiy menyu":
            await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=True))
        else:
            await message.answer("❌ Jarayon bekor qilindi.", reply_markup=admin_menu_keyboard())

@router.message(F.text == "⚙️ Admin Panel")
@router.message(F.text == "/admin")
async def open_admin_panel(message: Message, state: FSMContext = None):
    if not is_admin(message.from_user.id):
        return

    if state:
        await state.clear()

    text = (
        "<b>⚙️ Admin Boshqaruv Paneli</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:"
    )
    await message.answer(text=text, reply_markup=admin_menu_keyboard())

@router.message(F.text == "🔙 Asosiy menyu")
async def back_to_main_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        text="🏠 <b>Asosiy menyuga qaytdingiz.</b>",
        reply_markup=main_menu_keyboard(is_admin=True)
    )

@router.callback_query(F.data == "admin_back")
async def admin_back_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.clear()
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="<b>⚙️ Admin Boshqaruv Paneli</b>\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_menu_keyboard()
    )
    await call.answer()

# Statistika
async def send_admin_stats(user_id: int, bot):
    total_users = await get_users_count()
    pro_users = await get_premium_users_count()
    total_movies = await get_movies_count()
    current_price = await get_pro_price()
    total_revenue = await get_total_revenue()
    approved_count = await get_approved_payments_count()

    stats_text = (
        "📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users:,} ta\n"
        f"⭐ <b>Hozirgi faol PRO a'zolar:</b> {pro_users:,} ta\n"
        f"🎬 <b>Jami kinolar/seriallar:</b> {total_movies:,} ta\n"
        f"💰 <b>PRO joriy narxi:</b> {current_price:,} so'm/oy\n\n"
        "💳 <b>Moliya / Tushum statistikasi:</b>\n"
        f"💵 <b>Jami tushum (Total summa):</b> <code>{total_revenue:,} so'm</code>\n"
        f"📦 <b>Jami sotilgan PRO obunalar:</b> {approved_count:,} ta"
    )
    await bot.send_message(chat_id=user_id, text=stats_text, reply_markup=admin_menu_keyboard())

@router.message(F.text == "📊 Statistika")
async def admin_stats_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_admin_stats(message.from_user.id, message.bot)

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await send_admin_stats(call.from_user.id, call.bot)
    await call.answer()

# Narxni sozlash
async def start_set_price(user_id: int, bot, state: FSMContext):
    current_price = await get_pro_price()
    await state.set_state(AdminPriceState.waiting_for_price)
    await bot.send_message(
        chat_id=user_id,
        text=f"💰 <b>Joriy PRO obuna narxi:</b> {current_price:,} so'm.\n\n"
             "Yangi narxni so'mda faqat raqamlar bilan kiriting (masalan: 20000):",
        reply_markup=cancel_keyboard()
    )

@router.message(F.text == "💰 PRO narxini sozlash")
async def admin_price_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await start_set_price(message.from_user.id, message.bot, state)

@router.callback_query(F.data == "admin_price")
async def admin_price_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await start_set_price(call.from_user.id, call.bot, state)
    await call.answer()

@router.message(AdminPriceState.waiting_for_price, F.text)
async def process_new_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip().replace(" ", "").replace(",", "")
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Iltimos, faqat noldan katta musbat raqam kiriting:")
        return

    new_price = int(text)
    await set_pro_price(new_price)
    await state.clear()

    await message.answer(
        text=f"✅ <b>PRO obuna oylik narxi {new_price:,} so'm qilib belgilandi!</b>",
        reply_markup=admin_menu_keyboard()
    )
