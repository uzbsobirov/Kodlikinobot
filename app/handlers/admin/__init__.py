from aiogram import Dispatcher
from .panel import router as panel_router
from .movies import router as movies_router
from .cards import router as cards_router
from .channels import router as channels_router
from .broadcast import router as broadcast_router
from .admins import router as admins_router

def setup(dp: Dispatcher):
    """
    Admin paneli routerlarini ulash
    """
    dp.include_routers(
        panel_router,
        movies_router,
        cards_router,
        channels_router,
        broadcast_router,
        admins_router
    )

