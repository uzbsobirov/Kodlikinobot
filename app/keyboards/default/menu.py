from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.keyboards import texts as t

def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=t.PERSONAL_CABINET), KeyboardButton(text=t.PRO_SUBSCRIPTION)]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text=t.ADMIN_PANEL)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.CANCEL)]],
        resize_keyboard=True
    )

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.ADD_MOVIE), KeyboardButton(text=t.ADD_EPISODE)],
            [KeyboardButton(text=t.DELETE_MOVIE), KeyboardButton(text=t.STATISTICS)],
            [KeyboardButton(text=t.CARDS_MANAGEMENT), KeyboardButton(text=t.PRO_PRICE_SETTINGS)],
            [KeyboardButton(text=t.CHANNELS_MANAGEMENT), KeyboardButton(text=t.BROADCAST)],
            [KeyboardButton(text=t.ADMINS_MANAGEMENT), KeyboardButton(text=t.BACK_TO_MAIN_MENU)]
        ],
        resize_keyboard=True
    )
