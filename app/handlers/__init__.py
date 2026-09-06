from aiogram import Dispatcher
from app.handlers import admin, users

def setup(dp: Dispatcher):
    """
    Botning routerlarini sozlash uchun setup funksiyasi.
    """
    admin.setup(dp)  # Admin paneli handlerlari
    users.setup(dp)  # Foydalanuvchi bilan bog'liq handlerlar
