from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from database.crud import (
    get_pro_price, get_active_cards, create_payment,
    get_payment, update_payment_status, set_premium
)
from app.state.states import PaymentState
from app.keyboards.inline.payment import buy_pro_keyboard, admin_payment_action_keyboard
from app.keyboards.default.menu import cancel_keyboard, main_menu_keyboard
from data.config import ADMINS
from datetime import datetime

from app.utils.subscription import check_user_subscriptions
from app.keyboards.inline.channels import channels_check_keyboard

router = Router()

def format_card_number(raw: str) -> str:
    """Karta raqamini tozalab, har 4 ta belgidan bo'shliq bilan ajratadi"""
    clean = "".join(filter(str.isdigit, raw or ""))
    if not clean:
        return (raw or "").strip()
    return " ".join(clean[i:i+4] for i in range(0, len(clean), 4))

async def get_pro_text_content(is_from_sub: bool = False) -> str:
    price = await get_pro_price()
    cards = await get_active_cards()

    if not cards:
        cards_text = "<i>⚠️ To'lov qabul qilish uchun kartalar vaqtincha mavjud emas. Tez orada qo'shiladi.</i>"
    else:
        cards_list = []
        for c in cards:
            formatted_num = format_card_number(c.card_number)
            holder = f" ({c.card_holder})" if c.card_holder else ""
            cards_list.append(f"💳 <b>{c.bank_name}:</b> <code>{formatted_num}</code>{holder}")
        cards_text = "\n".join(cards_list)
        cards_text += "\n\n<i>💡 Nusxalash uchun karta raqami ustiga bosing!</i>"

    extra_notice = ""
    if is_from_sub:
        extra_notice = "✨ <b>PRO obunani xarid qilib, kanallarga a'zo bo'lmasdan barcha kinolarni tomosha qilishingiz mumkin!</b>\n\n"

    return (
        "⭐ <b>PRO (Premium) Obuna</b>\n\n"
        f"{extra_notice}"
        "PRO obuna afzalliklari:\n"
        "• <b>Majburiy kanallarga a'zo bo'lish shart emas!</b>\n"
        "• Barcha kinolarni yuqori tezlikda yuklab olish\n"
        "• Reklamasiz va cheklovlarsiz tomosha qilish\n\n"
        f"💰 <b>Oylik obuna narxi:</b> <code>{price:,} so'm</code>\n\n"
        f"<b>To'lov uchun karta raqamlari:</b>\n{cards_text}\n\n"
        "To'lovni amalga oshirgach, pastdagi tugmani bosing va to'lov cheki (skrinshot)ni yuboring:"
    )

@router.message(F.text == "⭐ PRO Obuna")
async def pro_info_handler(message: Message):
    text = await get_pro_text_content(is_from_sub=False)
    await message.answer(text=text, reply_markup=buy_pro_keyboard(from_sub=False))

@router.callback_query(F.data == "buy_pro_from_sub")
async def buy_pro_from_sub_callback(call: CallbackQuery):
    text = await get_pro_text_content(is_from_sub=True)
    try:
        await call.message.edit_text(text=text, reply_markup=buy_pro_keyboard(from_sub=True))
    except Exception:
        await call.message.answer(text=text, reply_markup=buy_pro_keyboard(from_sub=True))
    await call.answer()

@router.callback_query(F.data == "back_to_sub_channels")
async def back_to_sub_channels_callback(call: CallbackQuery):
    is_sub, unsub_channels = await check_user_subscriptions(call.bot, call.from_user.id)
    if is_sub:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.bot.send_message(
            chat_id=call.from_user.id,
            text="🎬 Botdan to'liq foydalanishingiz mumkin!\nKino yoki serial kodini yuboring:",
            reply_markup=main_menu_keyboard(is_admin=call.from_user.id in ADMINS)
        )
        return

    text = (
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "Botdan foydalanish uchun quyidagi homiy kanallarga a'zo bo'ling va "
        "<b>«✅ Obunani tekshirish»</b> tugmasini bosing:\n\n"
        "<i>Yoki kanallarga obuna bo'lmasdan darhol ko'rish uchun <b>«⭐ PRO Obuna»</b> sotib oling:</i>"
    )
    try:
        await call.message.edit_text(text=text, reply_markup=channels_check_keyboard(unsub_channels))
    except Exception:
        await call.message.answer(text=text, reply_markup=channels_check_keyboard(unsub_channels))
    await call.answer()

@router.callback_query(F.data == "send_receipt")
async def prompt_receipt_callback(call: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_receipt)
    await call.message.delete()
    await call.message.answer(
        text="📸 Iltimos, to'lov chekining aniq skrinshotini (rasmini) yuboring:",
        reply_markup=cancel_keyboard()
    )
    await call.answer()

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_callback(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer("To'lov bekor qilindi.")

@router.message(PaymentState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    screenshot_file_id = photo.file_id
    user = message.from_user
    user_id = user.id
    price = await get_pro_price()

    # Bazaga to'lovni yozamiz
    payment = await create_payment(
        user_id=user_id,
        amount=price,
        screenshot_file_id=screenshot_file_id
    )

    await state.clear()
    is_admin = user_id in ADMINS
    await message.answer(
        text="✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
             "Adminlar tomonidan tekshirilgandan so'ng, sizga avtomatik ravishda PRO status beriladi.",
        reply_markup=main_menu_keyboard(is_admin=is_admin)
    )

    # Adminlarga xabar yuborish
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    username_str = f"@{user.username}" if user.username else "mavjud emas"
    admin_caption = (
        f"🔔 <b>Yangi to'lov cheki!</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {user.full_name}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"🏷 <b>Username:</b> {username_str}\n"
        f"💰 <b>Summa:</b> {price:,} so'm\n"
        f"🕒 <b>Vaqt:</b> {now_str}\n\n"
        f"To'lov holatini tanlang:"
    )

    for admin_id in ADMINS:
        try:
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=screenshot_file_id,
                caption=admin_caption,
                reply_markup=admin_payment_action_keyboard(payment.id, user_id)
            )
        except Exception as e:
            pass

@router.message(PaymentState.waiting_for_receipt)
async def invalid_receipt_message(message: Message):
    await message.answer("⚠️ Iltimos, faqat to'lov cheki skrinshotini (rasm ko'rinishida) yuboring!")

# Admin tomonidan tasdiqlash yoki bekor qilish callbacklari
@router.callback_query(F.data.startswith("approve_pay:"))
async def approve_payment_callback(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        await call.answer("Siz admin emassiz!", show_alert=True)
        return

    _, payment_id_str, user_id_str = call.data.split(":")
    payment_id = int(payment_id_str)
    target_user_id = int(user_id_str)

    payment = await get_payment(payment_id)
    if not payment:
        await call.answer("To'lov topilmadi.", show_alert=True)
        return

    # Atomik yangilash: agar boshqa admin buni allaqachon ko'rib chiqqan bo'lsa
    # (race condition), rowcount 0 qaytaradi va foydalanuvchiga ikki marta PRO berilmaydi
    locked = await update_payment_status(payment_id, "tasdiqlandi")
    if not locked:
        await call.answer("Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    # Foydalanuvchiga 30 kun PRO status berish
    user = await set_premium(telegram_id=target_user_id, days=30)

    expire_str = user.premium_expire_date.strftime("%d.%m.%Y") if user and user.premium_expire_date else "30 kun"

    # Admindagi xabarni yangilash
    await call.message.edit_caption(
        caption=call.message.caption + f"\n\n✅ <b>Admin tomonidan TASDIQLANDI ({call.from_user.first_name})</b>",
        reply_markup=None
    )
    await call.answer("To'lov muvaffaqiyatli tasdiqlandi!")

    # Foydalanuvchiga xabar berish
    try:
        await call.bot.send_message(
            chat_id=target_user_id,
            text=f"🎉 <b>Tabriklaymiz!</b> Sizning to'lovingiz tasdiqlandi.\n\n"
                 f"⭐ <b>PRO status faollashtirildi!</b>\n"
                 f"⏳ <b>Amal qilish muddati:</b> {expire_str} gacha.\n"
                 f"Endi botdan cheklovlarsiz foydalanishingiz mumkin!"
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("reject_pay:"))
async def reject_payment_callback(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        await call.answer("Siz admin emassiz!", show_alert=True)
        return

    _, payment_id_str, user_id_str = call.data.split(":")
    payment_id = int(payment_id_str)
    target_user_id = int(user_id_str)

    payment = await get_payment(payment_id)
    if not payment:
        await call.answer("To'lov topilmadi.", show_alert=True)
        return

    locked = await update_payment_status(payment_id, "bekor_qilindi")
    if not locked:
        await call.answer("Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    await call.message.edit_caption(
        caption=call.message.caption + f"\n\n❌ <b>Admin tomonidan BEKOR QILINDI ({call.from_user.first_name})</b>",
        reply_markup=None
    )
    await call.answer("To'lov bekor qilindi.")

    # Foydalanuvchiga xabar berish
    try:
        await call.bot.send_message(
            chat_id=target_user_id,
            text="❌ <b>Kechirasiz, sizning to'lov chekingiz tasdiqlanmadi.</b>\n"
                 "To'lov amalga oshirilmagan yoki chek noaniq bo'lishi mumkin. Qayta urinib ko'ring yoki adminga murojaat qiling."
        )
    except Exception:
        pass
