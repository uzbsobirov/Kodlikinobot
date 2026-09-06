from aiogram import Dispatcher
from .start import router as start_router
from .help import router as help_router
from .subscription import router as subscription_router
from .profile import router as profile_router
from .premium import router as premium_router
from .search import router as search_router

def setup(dp: Dispatcher):
    """
    Foydalanuvchi routerlarini tartib bo'yicha ulash
    """
    dp.include_routers(
        start_router,
        help_router,
        subscription_router,
        profile_router,
        premium_router,
        search_router  # search_router matnli qidiruvni ushlashi uchun oxirida qo'yiladi
    )