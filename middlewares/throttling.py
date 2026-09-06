import time
import logging
from typing import Callable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.6):
        self.rate_limit = rate_limit
        self.users: Dict[int, float] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Any],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if not user:
            return await handler(event, data)

        now = time.time()
        last_time = self.users.get(user.id, 0)

        if now - last_time < self.rate_limit:
            logger.warning(f"⛔️ Throttled: user {user.id} - too fast")
            await event.answer("🚫 Juda ko‘p so‘rov yuborildi. Iltimos, biroz kuting.")
            return

        self.users[user.id] = now
        return await handler(event, data)
