import asyncio
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from data.config import ADMINS
from database.crud import get_all_user_ids
from app.state.states import AdminBroadcastState
from app.keyboards.default.menu import cancel_keyboard, admin_menu_keyboard

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def parse_inline_buttons(text: str) -> list[list[dict]]:
    """
    Formatlarni qo'llab-quvvatlaydi:
    Tugma nomi + https://havola
    Tugma nomi - https://havola
    Tugma 1 + https://link1 && Tugma 2 + https://link2 (bir qatorda)
    """
    rows = []
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        raw_buttons = line.split(" && ") if " && " in line else [line]
        row = []
        for btn_raw in raw_buttons:
            btn_raw = btn_raw.strip()
            parts = None
            for delim in [" + ", " - ", " | ", " -> ", " : ", "+", " -", "- "]:
                if delim in btn_raw:
                    p = btn_raw.split(delim, 1)
                    url_candidate = p[1].strip()
                    if url_candidate.startswith("http://") or url_candidate.startswith("https://") or url_candidate.startswith("tg://"):
                        parts = (p[0].strip(), url_candidate)
                        break
            if parts:
                row.append({"text": parts[0], "url": parts[1]})
        if row:
            rows.append(row)
    return rows

def build_inline_markup(buttons: list[list[dict]]) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    kb = []
    for row in buttons:
        r = []
        for btn in row:
            r.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
        if r:
            kb.append(r)
    return InlineKeyboardMarkup(inline_keyboard=kb) if kb else None

def broadcast_control_keyboard(is_forward: bool, send_mode: str, has_buttons: bool) -> InlineKeyboardMarkup:
    keyboard = []
    btn_row = [InlineKeyboardButton(text="➕ Tugma qo'shish", callback_data="bc_add_btn")]
    if has_buttons:
        btn_row.append(InlineKeyboardButton(text="🗑 Tugmalarni o'chirish", callback_data="bc_clear_btns"))
    keyboard.append(btn_row)

    if is_forward:
        if send_mode == "forward":
            mode_label = "⏩ Forward (Asl kanal ko'rinadi, tugmasiz)"
        else:
            mode_label = "📄 Nusxa (Tugmali / chiroyli format)"
        keyboard.append([InlineKeyboardButton(text=f"Rejim: {mode_label} 🔁", callback_data="bc_toggle_mode")])

    keyboard.append([
        InlineKeyboardButton(text="🚀 Yuborishni boshlash", callback_data="bc_send"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def start_broadcast_flow(user_id: int, bot, state: FSMContext):
    await state.set_state(AdminBroadcastState.waiting_for_message)
    await bot.send_message(
        chat_id=user_id,
        text="✉️ <b>Reklama / Xabarnoma yuborish</b>\n\n"
             "Foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:\n"
             "• Oddiy matn, rasm, video, audio yoki fayl\n"
             "• Kanal yoki boshqa botdan <b>Forward</b> qilingan xabar\n"
             "• <b>@PostBot</b> yoki boshqa botlardan inline tugmali xabarlar\n\n"
             "<i>Ixtiyoriy xabarni botga yuboring:</i>",
        reply_markup=cancel_keyboard()
    )

@router.message(F.text == "✉️ Xabar tarqatish")
async def broadcast_message_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await start_broadcast_flow(message.from_user.id, message.bot, state)

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await start_broadcast_flow(call.from_user.id, call.bot, state)
    await call.answer()

async def show_broadcast_preview(user_id: int, bot, state: FSMContext):
    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    is_forward = data.get("is_forward", False)
    send_mode = data.get("send_mode", "copy")
    buttons = data.get("buttons", [])

    markup = build_inline_markup(buttons)

    # Eski preview xabarlarini tozalash (agar mavjud bo'lsa)
    old_preview_ids = data.get("preview_msg_ids", [])
    for mid in old_preview_ids:
        try:
            await bot.delete_message(chat_id=user_id, message_id=mid)
        except Exception:
            pass

    msg1 = await bot.send_message(
        chat_id=user_id,
        text="👁 <b>Post namunasi (Preview):</b>\n<i>Foydalanuvchilarga quyidagi ko'rinishda boradi:</i>"
    )

    if send_mode == "forward":
        msg2 = await bot.forward_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id)
    else:
        msg2 = await bot.copy_message(
            chat_id=user_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            reply_markup=markup
        )

    btn_count = sum(len(r) for r in buttons)
    mode_text = "⏩ Forward (Asl kanal/muallif ko'rinadi, inline tugmasiz)" if send_mode == "forward" else "📄 Nusxa (Inline tugmali chiroyli xabar)"
    ctrl_text = (
        "⚙️ <b>Xabarnoma sozlamalari:</b>\n\n"
        f"• <b>Yuborish usuli:</b> {mode_text}\n"
        f"• <b>Inline tugmalar:</b> {btn_count} ta\n\n"
        "Xabarni tasdiqlang yoki tugma qo'shing:"
    )
    msg3 = await bot.send_message(
        chat_id=user_id,
        text=ctrl_text,
        reply_markup=broadcast_control_keyboard(is_forward, send_mode, bool(buttons))
    )

    await state.update_data(preview_msg_ids=[msg1.message_id, msg2.message_id, msg3.message_id])
    await state.set_state(AdminBroadcastState.waiting_for_confirm)

async def _send_broadcast_message(
    bot: Bot, chat_id: int, send_mode: str, from_chat_id: int, message_id: int,
    markup: InlineKeyboardMarkup | None
) -> None:
    if send_mode == "forward":
        await bot.forward_message(chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id)
    else:
        await bot.copy_message(
            chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id, reply_markup=markup
        )

@router.message(AdminBroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    # Forward xabarligini tekshirish
    is_forward = bool(
        getattr(message, "forward_origin", None) or
        getattr(message, "forward_from", None) or
        getattr(message, "forward_from_chat", None) or
        getattr(message, "forward_date", None)
    )

    # PostBot yoki boshqa botlardan kelgan inline tugmalarni ajratib olish
    buttons = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            r = []
            for btn in row:
                if btn.url:
                    r.append({"text": btn.text, "url": btn.url})
            if r:
                buttons.append(r)

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        is_forward=is_forward,
        send_mode="copy",  # Default nusxa (tugmalar qo'llab-quvvatlanishi uchun)
        buttons=buttons,
        preview_msg_ids=[]
    )

    await show_broadcast_preview(message.from_user.id, message.bot, state)

# Inline tugma qo'shish so'rovi
@router.callback_query(AdminBroadcastState.waiting_for_confirm, F.data == "bc_add_btn")
async def ask_add_button(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminBroadcastState.waiting_for_button)
    await call.message.edit_text(
        text="➕ <b>Inline tugma qo'shish</b>\n\n"
             "Tugma matni va havolasini quyidagi formatda yuboring:\n"
             "<code>Tugma nomi + https://t.me/kanal_yoki_sayt</code>\n\n"
             "Bir nechta tugma kiritish uchun yangi qatordan yozing:\n"
             "<code>Kanalimiz + https://t.me/kanal</code>\n"
             "<code>Admin bilan aloqa + https://t.me/admin</code>\n\n"
             "<i>💡 Eslatma: Telegram qoidasiga ko'ra, inline tugmalar 'Nusxa' rejimida qo'shiladi va ishlaydi.</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Bekor qilish (Orqaga)", callback_data="bc_back_preview")]]
        )
    )
    await call.answer()

@router.callback_query(AdminBroadcastState.waiting_for_button, F.data == "bc_back_preview")
async def back_to_preview_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminBroadcastState.waiting_for_confirm)
    try:
        await call.message.delete()
    except Exception:
        pass
    await show_broadcast_preview(call.from_user.id, call.bot, state)
    await call.answer()

# Yangi tugmalarni qabul qilish
@router.message(AdminBroadcastState.waiting_for_button, F.text)
async def process_added_buttons(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    new_buttons = parse_inline_buttons(message.text)
    if not new_buttons:
        await message.answer(
            "⚠️ Format noto'g'ri yoki havola aniqlanmadi!\n"
            "Iltimos, namunadagidek kiriting:\n"
            "<code>Tugma nomi + https://t.me/kanal</code>"
        )
        return

    data = await state.get_data()
    buttons = data.get("buttons", [])
    buttons.extend(new_buttons)

    # Agar xabar forward rejimida bo'lsa, avtomatik nusxa rejimiga o'tkazamiz
    # chunki Telegram platformasida 'Forward' xabarlarga inline tugma qo'shib bo'lmaydi
    send_mode = data.get("send_mode", "copy")
    notice = ""
    if send_mode == "forward":
        send_mode = "copy"
        notice = "\n\n<i>💡 Telegram cheklovi sababli 'Forward' xabarlarga tugma ulab bo'lmaydi. Xabar avtomatik 'Nusxa' rejimiga o'tkazildi va tugmalar biriktirildi.</i>"

    await state.update_data(buttons=buttons, send_mode=send_mode)

    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(f"✅ Tugma(lar) muvaffaqiyatli qo'shildi!{notice}")
    await show_broadcast_preview(message.from_user.id, message.bot, state)

# Tugmalarni tozalash
@router.callback_query(AdminBroadcastState.waiting_for_confirm, F.data == "bc_clear_btns")
async def clear_buttons_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.update_data(buttons=[])
    await call.answer("🗑 Barcha inline tugmalar olib tashlandi.")
    await show_broadcast_preview(call.from_user.id, call.bot, state)

# Forward / Nusxa rejimini almashtirish
@router.callback_query(AdminBroadcastState.waiting_for_confirm, F.data == "bc_toggle_mode")
async def toggle_mode_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    data = await state.get_data()
    buttons = data.get("buttons", [])
    current_mode = data.get("send_mode", "copy")

    if current_mode == "copy":
        if buttons:
            await call.answer(
                "⚠️ Telegram cheklovi: 'Forward' qilingan xabarlarga inline tugma qo'shib bo'lmaydi!\n\n"
                "Xabarni 'Forward' ko'rinishida yuborish uchun avval '🗑 Tugmalarni o'chirish' tugmasini bosing.",
                show_alert=True
            )
            return
        new_mode = "forward"
    else:
        new_mode = "copy"

    await state.update_data(send_mode=new_mode)
    await show_broadcast_preview(call.from_user.id, call.bot, state)
    await call.answer("Yuborish usuli o'zgartirildi.")

# Xabarni tarqatish
@router.callback_query(AdminBroadcastState.waiting_for_confirm, F.data == "bc_send")
async def confirm_broadcast_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    send_mode = data.get("send_mode", "copy")
    buttons = data.get("buttons", [])
    preview_msg_ids = data.get("preview_msg_ids", [])
    markup = build_inline_markup(buttons)

    # Preview xabarlarini o'chirish
    for mid in preview_msg_ids:
        try:
            await call.bot.delete_message(chat_id=call.from_user.id, message_id=mid)
        except Exception:
            pass

    await state.clear()
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="⏳ <b>Xabarnoma tarqatilmoqda, iltimos kuting...</b>"
    )

    user_ids = await get_all_user_ids()
    total = len(user_ids)
    success = 0
    failed = 0

    for uid in user_ids:
        try:
            await _send_broadcast_message(call.bot, uid, send_mode, from_chat_id, message_id, markup)
            success += 1
        except TelegramRetryAfter as e:
            # Telegram flood-limit qo'ygan — ko'rsatilgan soniya kutib, shu foydalanuvchiga bir marta qayta urinamiz
            await asyncio.sleep(e.retry_after)
            try:
                await _send_broadcast_message(call.bot, uid, send_mode, from_chat_id, message_id, markup)
                success += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            # Bot bloklangan yoki chiqarib yuborilgan — qayta urinish shart emas
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)

    await call.bot.send_message(
        chat_id=call.from_user.id,
        text=f"📊 <b>Xabarnoma yakunlandi!</b>\n\n"
             f"👥 Jami: {total} ta\n"
             f"✅ Yetkazildi: {success} ta\n"
             f"❌ Yetkazilmadi (bloklangan): {failed} ta",
        reply_markup=admin_menu_keyboard()
    )
    await call.answer()

# Bekor qilish
@router.callback_query(AdminBroadcastState.waiting_for_confirm, F.data == "bc_cancel")
async def cancel_broadcast_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    data = await state.get_data()
    preview_msg_ids = data.get("preview_msg_ids", [])
    for mid in preview_msg_ids:
        try:
            await call.bot.delete_message(chat_id=call.from_user.id, message_id=mid)
        except Exception:
            pass

    await state.clear()
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="❌ Xabarnoma bekor qilindi.",
        reply_markup=admin_menu_keyboard()
    )
    await call.answer()
