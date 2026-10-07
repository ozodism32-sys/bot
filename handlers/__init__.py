from aiogram import F, Router
from aiogram.types import CallbackQuery

from . import common, history, protocol, settings

fallback_router = Router(name="fallback")


@fallback_router.callback_query(F.data)
async def stale_callback(cb: CallbackQuery) -> None:
    await cb.answer("Bu tugma eskirgan. /start buyrug'ini bosing.", show_alert=False)


# Tartib muhim: protocol routeridagi umumiy matn handleri menyu tugmalaridan keyin turishi kerak
routers = [common.router, history.router, settings.router, protocol.router, fallback_router]
