from aiogram.types import CallbackQuery
from aiogram import Router, F
from app.utils.subscription import check_user_subscriptions
from app.keyboards.inline.channels import channels_check_keyboard
from app.keyboards.default.menu import main_menu_keyboard
from data.config import ADMINS

router = Router()

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(call: CallbackQuery):
    user_id = call.from_user.id
    is_subscribed, unsub_channels = await check_user_subscriptions(call.bot, user_id)

    if not is_subscribed:
        await call.answer(
            text="❌ Siz hali barcha kanallarga a'zo bo'lmadingiz! Iltimos, barcha kanallarga obuna bo'ling.",
            show_alert=True
        )
        # Klaviaturani yangilash
        try:
            await call.message.edit_reply_markup(reply_markup=channels_check_keyboard(unsub_channels))
        except Exception:
            pass
        return

    await call.answer("✅ Rahmat! Obuna muvaffaqiyatli tasdiqlandi.", show_alert=True)
    try:
        await call.message.delete()
    except Exception:
        pass

    is_admin = user_id in ADMINS
    await call.bot.send_message(
        chat_id=user_id,
        text="🎬 Botdan to'liq foydalanishingiz mumkin!\nKino yoki serial kodini yuboring:",
        reply_markup=main_menu_keyboard(is_admin=is_admin)
    )
