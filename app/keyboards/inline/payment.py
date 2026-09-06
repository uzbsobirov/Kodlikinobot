from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def buy_pro_keyboard(from_sub: bool = False) -> InlineKeyboardMarkup:
    back_button = (
        InlineKeyboardButton(text="⬅️ Kanallar ro'yxatiga qaytish", callback_data="back_to_sub_channels")
        if from_sub
        else InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_payment")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 To'lov chekini (skrinshot) yuborish", callback_data="send_receipt")],
            [back_button]
        ]
    )

def admin_payment_action_keyboard(payment_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash (+30 kun)", callback_data=f"approve_pay:{payment_id}:{user_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"reject_pay:{payment_id}:{user_id}")
            ]
        ]
    )
