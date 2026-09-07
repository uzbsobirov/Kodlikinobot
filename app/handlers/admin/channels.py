import logging
from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from data.config import ADMINS
from database.crud import get_all_channels, add_channel, delete_channel
from app.state.states import AdminChannelState
from app.keyboards.inline.admin import admin_channels_list_keyboard, channel_type_choice_keyboard
from app.keyboards.default.menu import cancel_keyboard, admin_menu_keyboard, main_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS



async def send_channels_list(user_id: int, bot):
    channels = await get_all_channels()
    text = (
        "📢 <b>Majburiy a'zolik kanallari</b>\n\n"
        "Foydalanuvchilar botdan foydalanishdan oldin quyidagi kanallarga a'zo bo'lishlari talab qilinadi:\n\n"
        "<i>Eslatma: Bot ushbu kanallarda administrator bo'lishi shart!</i>"
    )
    await bot.send_message(chat_id=user_id, text=text, reply_markup=admin_channels_list_keyboard(channels))

@router.message(F.text == "📢 Majburiy kanallar")
async def channels_list_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_channels_list(message.from_user.id, message.bot)

@router.callback_query(F.data == "admin_channels")
async def channels_list_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    channels = await get_all_channels()
    text = (
        "📢 <b>Majburiy a'zolik kanallari</b>\n\n"
        "Foydalanuvchilar botdan foydalanishdan oldin quyidagi kanallarga a'zo bo'lishlari talab qilinadi:\n\n"
        "<i>Eslatma: Bot ushbu kanallarda administrator bo'lishi shart!</i>"
    )
    await call.message.edit_text(text=text, reply_markup=admin_channels_list_keyboard(channels))
    await call.answer()

@router.callback_query(F.data.startswith("channel_del:"))
async def delete_channel_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    channel_pk_id = int(call.data.split(":")[1])
    await delete_channel(channel_pk_id)

    channels = await get_all_channels()
    await call.message.edit_text(
        text="🗑 Yozuv majburiy ro'yxatdan o'chirildi.\n\n📢 <b>Majburiy kanallar:</b>",
        reply_markup=admin_channels_list_keyboard(channels)
    )
    await call.answer("O'chirildi.")

# Yangi kanal/havola qo'shish — avval turini tanlaymiz
@router.callback_query(F.data == "channel_add")
async def start_add_channel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.clear()
    await call.message.edit_text(
        text="➕ <b>Qanday turdagi majburiy havola qo'shmoqchisiz?</b>\n\n"
             "📢 <b>Telegram kanal</b> — oddiy ochiq kanal bo'lsin yoki \"so'rov orqali qo'shilish\" "
             "(join request) yoqilgan kanal bo'lsin — bot avtomatik tekshiradi va so'rovlarni o'zi tasdiqlaydi.\n\n"
             "📸 <b>Instagram / boshqa havola</b> — faqat havola sifatida ko'rsatiladi, chunki bunday "
             "joylarda a'zolikni bot orqali tekshirib bo'lmaydi (Instagram API bunga ruxsat bermaydi).",
        reply_markup=channel_type_choice_keyboard()
    )
    await call.answer()

@router.callback_query(F.data == "channel_add_type:telegram")
async def start_add_telegram_channel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminChannelState.waiting_for_channel_id)
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="📢 <b>Majburiy a'zolik uchun Telegram kanal qo'shish</b>\n\n"
             "Kanalni qo'shish uchun quyidagi 2 usuldan birini tanlang:\n"
             "1️⃣ Kanaldan istalgan bitta xabarni (postni) bu yerga <b>Forward</b> qiling.\n"
             "2️⃣ Yoki kanal <b>ID</b>sini (masalan: <code>-1003880553725</code>) yoki <b>username</b>ini (<code>@kanal_nomi</code>) yozib yuboring.\n\n"
             "<i>⚠️ Muhim: Bot kanalda administrator bo'lishi va \"Foydalanuvchi qo'shish\" (Add/Invite Users) "
             "huquqiga ega bo'lishi shart — aks holda \"so'rov orqali qo'shilish\" yoqilgan kanallarda "
             "so'rovlarni avtomatik tasdiqlab bera olmaydi.</i>",
        reply_markup=cancel_keyboard()
    )
    await call.answer()

@router.callback_query(F.data == "channel_add_type:other")
async def start_add_other_channel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminChannelState.waiting_for_other_name)
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="📸 <b>Instagram / boshqa havola qo'shish</b>\n\n"
             "Havola qanday nom bilan ko'rsatilsin? (masalan: <code>Instagram sahifamiz</code>):",
        reply_markup=cancel_keyboard()
    )
    await call.answer()

@router.message(AdminChannelState.waiting_for_other_name, F.text)
async def process_other_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text in ["❌ Bekor qilish", "🔙 Asosiy menyu"]:
        await state.clear()
        if message.text == "🔙 Asosiy menyu":
            await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=True))
        else:
            await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_keyboard())
        return

    await state.update_data(other_name=message.text.strip())
    await state.set_state(AdminChannelState.waiting_for_other_link)
    await message.answer(
        "🔗 Endi havolaning o'zini yuboring (masalan: <code>https://instagram.com/kodlikino</code>):"
    )

@router.message(AdminChannelState.waiting_for_other_link, F.text)
async def process_other_link(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text in ["❌ Bekor qilish", "🔙 Asosiy menyu"]:
        await state.clear()
        if message.text == "🔙 Asosiy menyu":
            await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=True))
        else:
            await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_keyboard())
        return

    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer("⚠️ Iltimos, to'liq havolani kiriting (masalan: https://instagram.com/...):")
        return

    data = await state.get_data()
    name = data.get("other_name", "Havola")
    await add_channel(name=name, invite_link=link, channel_id=None, channel_type="other")
    await state.clear()

    await message.answer(
        text=f"✅ <b>Havola muvaffaqiyatli qo'shildi!</b>\n\n"
             f"📸 <b>Nomi:</b> {name}\n"
             f"🔗 <b>Havola:</b> {link}\n\n"
             f"<i>Eslatma: bu turdagi havolalar uchun bot a'zolikni tekshira olmaydi, "
             f"foydalanuvchiga faqat ko'rsatib qo'yiladi.</i>",
        reply_markup=admin_menu_keyboard()
    )

@router.message(AdminChannelState.waiting_for_channel_id)
async def process_channel_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text in ["❌ Bekor qilish", "🔙 Asosiy menyu"]:
        await state.clear()
        if message.text == "🔙 Asosiy menyu":
            await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=True))
        else:
            await message.answer("❌ Kanal qo'shish bekor qilindi.", reply_markup=admin_menu_keyboard())
        return

    ch_id = None

    # 1. Forward qilingan postdan kanalni aniqlash
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        ch_id = message.forward_origin.chat.id
    elif message.forward_from_chat:
        ch_id = message.forward_from_chat.id

    # 2. Matn ko'rinishida kiritilgan bo'lsa (ID, username yoki havola)
    if not ch_id and message.text:
        raw = message.text.strip()
        if raw.startswith("https://t.me/"):
            raw_user = raw.replace("https://t.me/", "")
            if not raw_user.startswith("+"):
                raw = f"@{raw_user}"

        if raw.startswith("@"):
            ch_id = raw
        else:
            clean_digits = raw.replace(" ", "")
            try:
                if clean_digits.startswith("-100") or clean_digits.startswith("-"):
                    ch_id = int(clean_digits)
                elif clean_digits.isdigit():
                    ch_id = int(f"-100{clean_digits}")
                else:
                    ch_id = raw
            except ValueError:
                ch_id = raw

    if not ch_id:
        await message.answer(
            "⚠️ Kanal aniqlanmadi!\n"
            "Iltimos, kanaldan biror xabarni <b>Forward</b> qiling yoki kanal <b>ID</b>sini (masalan: <code>-1003880553725</code>) yuboring:"
        )
        return

    # Bot adminligini va kanal ma'lumotlarini olish
    try:
        chat = await message.bot.get_chat(ch_id)
    except Exception as e:
        await message.answer(
            f"⚠️ Bot ushbu kanalga ulanolmadi: <code>{e}</code>\n\n"
            "• Bot kanalda <b>Administrator</b> ekanligiga ishonch hosil qiling.\n"
            "• Qaytadan post forward qiling yoki ID yuboring:"
        )
        return

    channel_id = chat.id
    channel_name = chat.title or "Kanal"

    # Havolani (link) avtomatik olish — avval "so'rov orqali qo'shilish"
    # (join request) havolasini yaratishga harakat qilamiz, shunda bot
    # so'rovlarni avtomatik tasdiqlay oladi. Bunga huquq yetmasa
    # (masalan bot "Foydalanuvchi qo'shish" huquqiga ega bo'lmasa),
    # oddiy ochiq havolaga qaytamiz.
    invite_link = None
    try:
        created_link = await message.bot.create_chat_invite_link(
            chat_id=channel_id,
            name="Kodlikino Majburiy Obuna",
            creates_join_request=True
        )
        invite_link = created_link.invite_link
    except Exception as err:
        logger.warning(f"So'rov orqali qo'shilish havolasi yaratilmadi: {err}")
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        elif chat.invite_link:
            invite_link = chat.invite_link

    # Agar havola baribir olinmasa, qo'lda so'raymiz (fallback)
    if not invite_link:
        await state.update_data(channel_id=channel_id, channel_name=channel_name)
        await state.set_state(AdminChannelState.waiting_for_invite_link)
        await message.answer(
            f"📢 Kanal: <b>{channel_name}</b> (<code>{channel_id}</code>)\n\n"
            "⚠️ Kanal yopiq va botda taklif havolasi yaratish huquqi yetarli bo'lmadi.\n"
            "Iltimos, ushbu kanal uchun taklif havolasini (link) yuboring:\n<i>(Masalan: https://t.me/+AbCdEf...)</i>",
            reply_markup=cancel_keyboard()
        )
        return

    # Barchasi tayyor, bazaga saqlaymiz!
    await add_channel(channel_id=channel_id, name=channel_name, invite_link=invite_link)
    await state.clear()

    await message.answer(
        text=f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
             f"📢 <b>Nomi:</b> {channel_name}\n"
             f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
             f"🔗 <b>Havola:</b> {invite_link}",
        reply_markup=admin_menu_keyboard()
    )

@router.message(AdminChannelState.waiting_for_invite_link, F.text)
async def process_invite_link(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text in ["❌ Bekor qilish", "🔙 Asosiy menyu"]:
        await state.clear()
        if message.text == "🔙 Asosiy menyu":
            await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=True))
        else:
            await message.answer("❌ Kanal qo'shish bekor qilindi.", reply_markup=admin_menu_keyboard())
        return

    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer("⚠️ Iltimos, to'liq havolani kiriting (masalan: https://t.me/...):")
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")
    channel_name = data.get("channel_name")

    await add_channel(channel_id=channel_id, name=channel_name, invite_link=link)
    await state.clear()

    await message.answer(
        text=f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
             f"📢 <b>Nomi:</b> {channel_name}\n"
             f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
             f"🔗 <b>Havola:</b> {link}",
        reply_markup=admin_menu_keyboard()
    )
