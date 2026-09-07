import logging
from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from data.config import ADMINS
from database.crud import get_all_channels, add_channel, delete_channel
from app.state.states import AdminChannelState
from app.keyboards.inline.admin import (
    admin_channels_list_keyboard,
    channel_category_choice_keyboard,
    channel_mode_choice_keyboard,
    add_bot_admin_keyboard
)
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

# Yangi kanal/havola qo'shish — avval kategoriyasini tanlaymiz
@router.callback_query(F.data == "channel_add")
async def start_add_channel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.clear()
    await call.message.edit_text(
        text="➕ <b>Nima qo'shmoqchisiz?</b>\n\n"
             "📢 <b>Kanal/guruh ulash</b> — bot a'zolikni tekshiradigan majburiy Telegram kanal yoki guruh.\n\n"
             "🔗 <b>Tashqi link</b> — Instagram va shunga o'xshash, bot tekshira olmaydigan havolalar "
             "(faqat ko'rsatiladi, a'zolik shart qilinmaydi).",
        reply_markup=channel_category_choice_keyboard()
    )
    await call.answer()

@router.callback_query(F.data == "channel_add_category:channel")
async def choose_channel_mode(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await call.message.edit_text(
        text="📢 <b>Qanday turdagi kanal/guruh qo'shmoqchisiz?</b>\n\n"
             "🔒 <b>So'rovli (request)</b> — foydalanuvchi \"Request to Join\" bosadi, bot avtomatik "
             "tasdiqlaydi. Katta (ko'p a'zoli) kanal/guruhlar uchun tavsiya etiladi.\n\n"
             "🌐 <b>Oddiy (ochiq)</b> — foydalanuvchi to'g'ridan-to'g'ri, so'rovsiz a'zo bo'ladi.",
        reply_markup=channel_mode_choice_keyboard()
    )
    await call.answer()

@router.callback_query(F.data.startswith("channel_add_mode:"))
async def start_add_telegram_channel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    link_mode = call.data.split(":")[1]  # "request" yoki "open"
    await state.update_data(link_mode=link_mode)
    await state.set_state(AdminChannelState.waiting_for_channel_id)
    try:
        await call.message.delete()
    except Exception:
        pass

    bot_me = await call.bot.get_me()
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="🤖 <b>1-qadam: Botni admin qiling</b>\n\n"
             "Pastdagi tugma orqali kanal/guruhingizni ro'yxatdan tanlasangiz, bot kerakli huquq "
             "(\"Foydalanuvchi qo'shish\") bilan avtomatik admin bo'ladi — qo'lda sozlash shart emas.\n\n"
             "<i>Agar botni allaqachon qo'lda admin qilib qo'ygan bo'lsangiz, bu qadamni o'tkazib yuborishingiz mumkin.</i>",
        reply_markup=add_bot_admin_keyboard(bot_me.username)
    )
    await call.bot.send_message(
        chat_id=call.from_user.id,
        text="📢 <b>2-qadam: Kanal/guruhni bog'lash</b>\n\n"
             "1️⃣ Kanal/guruhdan istalgan bitta xabarni bu yerga <b>Forward</b> qiling.\n"
             "2️⃣ Yoki <b>ID</b>sini (masalan: <code>-1003880553725</code>) yoki <b>username</b>ini "
             "(<code>@nomi</code>) yozib yuboring.",
        reply_markup=cancel_keyboard()
    )
    await call.answer()

@router.callback_query(F.data == "channel_add_category:other")
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

    data = await state.get_data()
    link_mode = data.get("link_mode", "request")

    # "So'rovli" tanlangan bo'lsa — avval creates_join_request=True bilan
    # maxsus havola yaratishga harakat qilamiz, shunda bot so'rovlarni
    # avtomatik tasdiqlay oladi. Bunga huquq yetmasa (masalan bot hali
    # "Foydalanuvchi qo'shish" huquqi bilan to'liq tan olinmagan bo'lsa),
    # pastdagi oddiy havola zanjiriga tushamiz.
    invite_link = None
    got_request_link = False
    if link_mode == "request":
        try:
            created_link = await message.bot.create_chat_invite_link(
                chat_id=channel_id,
                name="Kodlikino Majburiy Obuna",
                creates_join_request=True
            )
            invite_link = created_link.invite_link
            got_request_link = True
        except Exception as err:
            logger.warning(f"So'rov orqali qo'shilish havolasi yaratilmadi: {err}")

    # "Oddiy" tanlangan bo'lsa yoki so'rovli havola yaratib bo'lmasa —
    # mavjud ochiq havolalardan foydalanamiz, aks holda oddiy havola yaratamiz.
    if not invite_link:
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        elif chat.invite_link:
            invite_link = chat.invite_link
        else:
            try:
                created_link = await message.bot.create_chat_invite_link(
                    chat_id=channel_id,
                    name="Kodlikino Majburiy Obuna"
                )
                invite_link = created_link.invite_link
            except Exception as err:
                logger.warning(f"Havola yaratilmadi: {err}")

    # Havola baribir olinmasa, qo'lda so'raymiz (fallback)
    if not invite_link:
        await state.update_data(channel_id=channel_id, channel_name=channel_name)
        await state.set_state(AdminChannelState.waiting_for_invite_link)
        await message.answer(
            f"📢 Kanal: <b>{channel_name}</b> (<code>{channel_id}</code>)\n\n"
            "⚠️ Bot ushbu kanal/guruh uchun havola yarata olmadi — huquqlar yetarli emas.\n"
            "Iltimos, ushbu kanal/guruh uchun taklif havolasini (link) yuboring:\n<i>(Masalan: https://t.me/+AbCdEf...)</i>",
            reply_markup=cancel_keyboard()
        )
        return

    warning = None
    if link_mode == "request" and not got_request_link:
        warning = (
            "⚠️ <b>Diqqat:</b> so'rovli (request) havola yaratib bo'lmadi — bot hali "
            "\"Foydalanuvchi qo'shish\" huquqi bilan to'liq tan olinmagan bo'lishi mumkin. "
            "Hozircha oddiy (so'rovsiz) havola ishlatildi. Botni adminlikdan olib tashlab, "
            "qaytadan (\"Foydalanuvchi qo'shish\" huquqi bilan) admin qilib, kanalni qaytadan "
            "qo'shib ko'ring."
        )

    await ask_for_channel_name(message, state, channel_id, channel_name, invite_link, warning)

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

    await ask_for_channel_name(message, state, channel_id, channel_name, link)


async def ask_for_channel_name(message: Message, state: FSMContext, channel_id: int, default_name: str, invite_link: str, warning: str = None):
    """Kanal aniqlangach, admindan nomni tasdiqlashni yoki o'zgartirishni so'raydi."""
    await state.update_data(channel_id=channel_id, channel_name=default_name, invite_link=invite_link)
    await state.set_state(AdminChannelState.waiting_for_channel_name)
    if warning:
        await message.answer(text=warning)
    await message.answer(
        text=f"📝 <b>Kanal nomini tasdiqlang</b>\n\n"
             f"Standart nom: <b>{default_name}</b>\n\n"
             f"Boshqa nom bilan ko'rsatmoqchi bo'lsangiz — o'sha nomni yozib yuboring.\n"
             f"Standart nom bilan qoldirish uchun <code>-</code> yuboring:",
        reply_markup=cancel_keyboard()
    )


@router.message(AdminChannelState.waiting_for_channel_name, F.text)
async def process_channel_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text in ["❌ Bekor qilish", "🔙 Asosiy menyu"]:
        await state.clear()
        if message.text == "🔙 Asosiy menyu":
            await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(is_admin=True))
        else:
            await message.answer("❌ Kanal qo'shish bekor qilindi.", reply_markup=admin_menu_keyboard())
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")
    invite_link = data.get("invite_link")
    default_name = data.get("channel_name")

    typed = message.text.strip()
    channel_name = default_name if typed == "-" else typed

    await add_channel(channel_id=channel_id, name=channel_name, invite_link=invite_link)
    await state.clear()

    await message.answer(
        text=f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
             f"📢 <b>Nomi:</b> {channel_name}\n"
             f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
             f"🔗 <b>Havola:</b> {invite_link}",
        reply_markup=admin_menu_keyboard()
    )
