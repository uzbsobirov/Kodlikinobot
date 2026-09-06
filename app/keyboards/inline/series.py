from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from database.models import Episode

def seasons_keyboard(movie_id: int, seasons: List[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for s in seasons:
        row.append(InlineKeyboardButton(text=f"📁 {s}-Fasl", callback_data=f"season:{movie_id}:{s}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def episodes_keyboard(movie_id: int, season: int, episodes: List[Episode]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for ep in episodes:
        btn_text = f"▶️ {ep.episode}-qism"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"episode:{ep.id}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Orqaga qaytish tugmasi
    buttons.append([InlineKeyboardButton(text="⬅️ Fasllar ro'yxatiga qaytish", callback_data=f"back_to_seasons:{movie_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
