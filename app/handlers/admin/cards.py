from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from data.config import ADMINS
from database.crud import (
    get_all_cards, add_card, toggle_card_status, delete_card, async_session
)
from database.models import Card
from app.state.states import AdminCardState
from app.keyboards.inline.admin import admin_cards_list_keyboard, admin_card_action_keyboard
from aiogram.filters import StateFilter
from app.keyboards.default.menu import cancel_keyboard, admin_menu_keyboard, main_menu_keyboard
from sqlalchemy import select

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

@router.message(StateFilter("*"), F.text.in_(["❌ Bekor qilish", "🔙 Asosiy menyu"]))
async def admin_card_cancel_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        if message.text == "🔙 Asosiy menyu":
            await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=True))
        else:
            await message.answer("❌ Jarayon bekor qilindi.", reply_markup=admin_menu_keyboard())

def format_card_number(raw: str) -> str:
    """Karta raqamini tozalab, har 4 ta belgidan bo'shliq bilan ajratadi"""
    clean = "".join(filter(str.isdigit, raw or ""))
    if not clean:
        return (raw or "").strip()
    return " ".join(clean[i:i+4] for i in range(0, len(clean), 4))

async def send_cards_list(user_id: int, bot):
    cards = await get_all_cards()
    text = (
        "💳 <b>To'lov kartalari boshqaruvi</b>\n\n"
        "Yashil (🟢) - Faol karta (foydalanuvchilarga ko'rinadi)\n"
        "Qizil (🔴) - Nofaol karta\n\n"
        "Boshqarish uchun kartani tanlang yoki yangi qo'shing:"
    )
    await bot.send_message(chat_id=user_id, text=text, reply_markup=admin_cards_list_keyboard(cards))

@router.message(F.text == "💳 Kartalar boshqaruvi")
async def cards_list_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_cards_list(message.from_user.id, message.bot)

@router.callback_query(F.data == "admin_cards")
async def cards_list_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    cards = await get_all_cards()
    text = (
        "💳 <b>To'lov kartalari boshqaruvi</b>\n\n"
        "Yashil (🟢) - Faol karta (foydalanuvchilarga ko'rinadi)\n"
        "Qizil (🔴) - Nofaol karta\n\n"
        "Boshqarish uchun kartani tanlang yoki yangi qo'shing:"
    )
    await call.message.edit_text(text=text, reply_markup=admin_cards_list_keyboard(cards))
    await call.answer()

@router.callback_query(F.data.startswith("card_info:"))
async def card_info_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    card_id = int(call.data.split(":")[1])
    async with async_session() as session:
        res = await session.execute(select(Card).where(Card.id == card_id))
        card = res.scalar_one_or_none()

    if not card:
        await call.answer("Karta topilmadi.", show_alert=True)
        return

    status_str = "Faol 🟢" if card.is_active else "Nofaol 🔴"
    formatted_num = format_card_number(card.card_number)
    text = (
        f"💳 <b>Karta ma'lumotlari:</b>\n\n"
        f"🏦 <b>Bank / Turi:</b> {card.bank_name}\n"
        f"🔢 <b>Raqami:</b> <code>{formatted_num}</code>\n"
        f"👤 <b>Egasi:</b> {card.card_holder or 'Kiritilmagan'}\n"
        f"📌 <b>Holati:</b> {status_str}\n\n"
        f"<i>💡 Nusxalash uchun karta raqami ustiga bosing</i>"
    )
    await call.message.edit_text(text=text, reply_markup=admin_card_action_keyboard(card.id, card.is_active))
    await call.answer()

@router.callback_query(F.data.startswith("card_toggle:"))
async def card_toggle_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    card_id = int(call.data.split(":")[1])
    updated_card = await toggle_card_status(card_id)
    if not updated_card:
        await call.answer("Karta topilmadi.", show_alert=True)
        return

    cards = await get_all_cards()
    await call.message.edit_text(
        text="✅ Karta holati yangilandi!\n\n💳 <b>To'lov kartalari:</b>",
        reply_markup=admin_cards_list_keyboard(cards)
    )
    await call.answer("Karta holati o'zgartirildi.")

@router.callback_query(F.data.startswith("card_delete:"))
async def card_delete_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    card_id = int(call.data.split(":")[1])
    await delete_card(card_id)

    cards = await get_all_cards()
    await call.message.edit_text(
        text="🗑 Karta o'chirildi!\n\n💳 <b>To'lov kartalari:</b>",
        reply_markup=admin_cards_list_keyboard(cards)
    )
    await call.answer("Karta o'chirildi.")

# Yangi karta qo'shish jarayoni
@router.callback_query(F.data == "card_add")
async def start_add_card(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminCardState.waiting_for_card_number)
    await call.message.delete()
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="💳 <b>Karta raqamini kiriting:</b>\n<i>(Masalan: 8600123456789012 yoki bo'shliq bilan)</i>",
        reply_markup=cancel_keyboard()
    )
    await call.answer()

@router.message(AdminCardState.waiting_for_card_number, F.text)
async def process_card_number(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    raw_text = message.text.strip()
    clean_digits = "".join(filter(str.isdigit, raw_text))
    if len(clean_digits) < 8:
        await message.answer("⚠️ Iltimos, to'g'ri karta raqamini kiriting (kamida 8-16 ta raqam):")
        return

    formatted_card = format_card_number(raw_text)
    await state.update_data(card_number=formatted_card)
    await state.set_state(AdminCardState.waiting_for_bank_name)
    await message.answer(
        f"💳 Karta raqami: <code>{formatted_card}</code>\n\n"
        "🏦 <b>Bank yoki karta turini kiriting:</b>\n<i>(Masalan: Uzcard, Humo, Kapitalbank)</i>"
    )

@router.message(AdminCardState.waiting_for_bank_name, F.text)
async def process_bank_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    bank_name = message.text.strip()
    await state.update_data(bank_name=bank_name)
    await state.set_state(AdminCardState.waiting_for_card_holder)
    await message.answer("👤 <b>Karta egasining ismini kiriting</b> (agar kerak bo'lmasa '-' yuboring):")

@router.message(AdminCardState.waiting_for_card_holder, F.text)
async def process_card_holder(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    holder = message.text.strip()
    if holder == "-":
        holder = None

    data = await state.get_data()
    card_number = data.get("card_number")
    bank_name = data.get("bank_name")

    await add_card(card_number=card_number, bank_name=bank_name, card_holder=holder)
    await state.clear()

    await message.answer(
        text=f"✅ <b>Karta muvaffaqiyatli qo'shildi!</b>\n\n"
             f"💳 <b>Raqam:</b> <code>{card_number}</code>\n"
             f"🏦 <b>Bank:</b> {bank_name}\n"
             f"👤 <b>Egasi:</b> {holder or 'Ko`rsatilmadi'}\n\n"
             f"<i>(💡 Karta raqami ustiga bossangiz, nusxalanadi)</i>",
        reply_markup=admin_menu_keyboard()
    )
