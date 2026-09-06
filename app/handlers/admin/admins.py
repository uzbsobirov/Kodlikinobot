import logging
from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from data.config import ADMINS, ENV_ADMINS, is_admin
from database.crud import (
    get_all_admins, add_admin, delete_admin,
    get_admin_by_tg_id
)
from database.base import async_session
from database.models import User
from sqlalchemy import select
from app.state.states import AdminManageState
from app.keyboards.inline.admin import (
    admin_admins_list_keyboard,
    admin_delete_select_keyboard,
    admin_delete_confirm_keyboard
)
from app.keyboards.default.menu import cancel_keyboard, admin_menu_keyboard, main_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()



async def send_admins_list(user_id: int, bot):
    admins = await get_all_admins()

    lines = []
    for i, a in enumerate(admins, start=1):
        is_owner = a.role == "owner" or a.telegram_id in ENV_ADMINS
        badge = "👑 <b>Asosiy Admin</b>" if is_owner else "🛡 <b>Admin</b>"
        
        name_str = a.full_name or f"ID: {a.telegram_id}"
        username_str = f" (@{a.username})" if a.username else ""
        date_str = a.created_at.strftime("%d.%m.%Y") if a.created_at else ""

        lines.append(
            f"{i}. {badge} — {name_str}{username_str}\n"
            f"   🆔 <code>{a.telegram_id}</code> | 📅 {date_str}"
        )

    list_text = "\n\n".join(lines) if lines else "<i>Hozircha adminlar yo'q.</i>"

    text = (
        "👥 <b>Administratorlar ro'yxati (Baza bo'yicha)</b>\n\n"
        f"Botda hozirda <b>{len(admins)}</b> ta administrator mavjud:\n\n"
        f"{list_text}\n\n"
        "<i>Quyidagi tugmalar orqali yangi admin qo'shishingiz yoki mavjudlarini boshqarishingiz mumkin:</i>"
    )

    await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=admin_admins_list_keyboard(admins, user_id, ENV_ADMINS)
    )

@router.message(F.text == "👥 Adminlar boshqaruvi")
async def admins_list_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_admins_list(message.from_user.id, message.bot)

@router.callback_query(F.data == "admin_manage_admins")
async def admins_list_callback(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.clear()
    try:
        await call.message.delete()
    except Exception:
        pass
    await send_admins_list(call.from_user.id, call.bot)
    await call.answer()

# Yangi admin qo'shish so'rovi
@router.callback_query(F.data == "admin_add_admin")
async def start_add_admin(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminManageState.waiting_for_admin_id)
    try:
        await call.message.delete()
    except Exception:
        pass

    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="👥 <b>Yangi admin tayinlash</b>\n\n"
             "Admin qilmoqchi bo'lgan shaxsni kiritish uchun:\n"
             "1️⃣ Uning <b>Telegram ID</b> raqamini yuboring (masalan: <code>123456789</code>)\n"
             "2️⃣ Yoki uning bitta xabarini shu yerga <b>Forward</b> qiling.\n\n"
             "<i>💡 Eslatma: Foydalanuvchi botdan foydalangan bo'lsa, uning ismi va ma'lumotlari avtomatik aniqlanadi.</i>",
        reply_markup=cancel_keyboard()
    )
    await call.answer()

@router.message(AdminManageState.waiting_for_admin_id)
async def process_admin_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    target_id = None
    full_name = None
    username = None

    # 1. Forward xabar orqali aniqlash
    if message.forward_from:
        target_id = message.forward_from.id
        full_name = message.forward_from.full_name
        username = message.forward_from.username
    elif message.forward_origin and getattr(message.forward_origin, "sender_user", None):
        sender = message.forward_origin.sender_user
        target_id = sender.id
        full_name = sender.full_name
        username = sender.username
    elif message.forward_sender_name or message.forward_origin:
        await message.answer(
            "⚠️ Ushbu foydalanuvchi o'z profilini Telegram maxfiylik sozlamalarida yashirgan.\n"
            "Iltimos, uning raqamli <b>Telegram ID</b> sini to'g'ridan-to'g'ri yozib yuboring (masalan: <code>123456789</code>):"
        )
        return
    elif message.text:
        text = message.text.strip()
        if not text.isdigit():
            await message.answer("⚠️ Iltimos, faqat musbat raqamlardan iborat Telegram ID kiriting:")
            return
        target_id = int(text)

    if not target_id:
        await message.answer("⚠️ Foydalanuvchi ID si aniqlanmadi. Qayta urinib ko'ring:")
        return

    # Allaqachon admin ekanligini tekshirish
    existing_admin = await get_admin_by_tg_id(target_id)
    if existing_admin or target_id in ADMINS:
        await message.answer(
            f"⚠️ Ushbu foydalanuvchi (ID: <code>{target_id}</code>) allaqachon adminlar ro'yxatida mavjud!",
            reply_markup=admin_menu_keyboard()
        )
        await state.clear()
        return

    # User jadvalidan ma'lumot qidirish
    if not full_name:
        async with async_session() as session:
            res = await session.execute(select(User).where(User.telegram_id == target_id))
            u = res.scalar_one_or_none()
            if u:
                full_name = u.full_name
                username = u.username

    # Agar bot orqali chat ma'lumotlarini olish mumkin bo'lsa
    if not full_name:
        try:
            chat = await message.bot.get_chat(target_id)
            full_name = chat.full_name
            username = chat.username
        except Exception:
            full_name = f"Admin ({target_id})"

    # Bazaga qo'shish
    await add_admin(
        telegram_id=target_id,
        full_name=full_name,
        username=username,
        role="admin",
        added_by=message.from_user.id
    )
    await state.clear()

    await message.answer(
        f"✅ <b>Yangi administrator muvaffaqiyatli qo'shildi!</b>\n\n"
        f"👤 <b>Ism:</b> {full_name}\n"
        f"🆔 <b>Telegram ID:</b> <code>{target_id}</code>\n"
        f"🏷 <b>Username:</b> @{username if username else 'yo`q'}\n\n"
        f"<i>Endi ushbu foydalanuvchi botda to'liq adminlik huquqlariga ega bo'ldi.</i>",
        reply_markup=admin_menu_keyboard()
    )

    # Yangi adminga xabar berishga harakat qilish
    try:
        await message.bot.send_message(
            chat_id=target_id,
            text="🎉 <b>Tabriklaymiz!</b> Sizga ushbu botda Administratorlik huquqi berildi.\n"
                 "Admin panelga kirish uchun /start bosing.",
            reply_markup=main_menu_keyboard(is_admin=True)
        )
    except Exception:
        pass

    await send_admins_list(message.from_user.id, message.bot)

# Adminni o'chirish menyusi
@router.callback_query(F.data == "admin_del_menu")
async def admin_delete_menu_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    admins = await get_all_admins()
    await call.message.edit_text(
        text="🗑 <b>Adminlikdan bo'shatmoqchi bo'lgan administratorni tanlang:</b>\n\n"
             "<i>Eslatma: Asosiy (.env) adminlar va o'zingizni o'chirib bo'lmaydi.</i>",
        reply_markup=admin_delete_select_keyboard(admins, call.from_user.id, ENV_ADMINS)
    )
    await call.answer()

# O'chirishni tasdiqlash
@router.callback_query(F.data.startswith("admin_del_confirm:"))
async def admin_del_confirm_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    admin_tg_id = int(call.data.split(":")[1])
    target = await get_admin_by_tg_id(admin_tg_id)
    name_str = target.full_name if target else f"ID: {admin_tg_id}"

    await call.message.edit_text(
        text=f"❓ Haqiqatan ham <b>{name_str}</b> (<code>{admin_tg_id}</code>) ni administratorlikdan olib tashlamoqchimisiz?",
        reply_markup=admin_delete_confirm_keyboard(admin_tg_id)
    )
    await call.answer()

# O'chirishni ijro etish
@router.callback_query(F.data.startswith("admin_del_yes:"))
async def admin_del_yes_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    admin_tg_id = int(call.data.split(":")[1])
    target = await get_admin_by_tg_id(admin_tg_id)
    name_str = target.full_name if target else f"ID: {admin_tg_id}"

    success = await delete_admin(admin_tg_id)
    if success:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.bot.send_message(
            chat_id=call.from_user.id,
            text=f"🗑 <b>{name_str}</b> administratorlikdan muvaffaqiyatli olib tashlandi.",
            reply_markup=admin_menu_keyboard()
        )
        # O'chirilgan foydalanuvchiga xabar
        try:
            await call.bot.send_message(
                chat_id=admin_tg_id,
                text="ℹ️ Sizning botdagi administratorlik huquqlaringiz to'xtatildi.",
                reply_markup=main_menu_keyboard(is_admin=False)
            )
        except Exception:
            pass
    else:
        await call.answer("⚠️ Ushbu adminni o'chirib bo'lmaydi!", show_alert=True)

    await send_admins_list(call.from_user.id, call.bot)
    await call.answer()
