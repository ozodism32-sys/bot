"""/start, bekor qilish, /stats, /help va global xato ushlagich (bot.py da ro'yxatdan o'tadi)."""
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent, Message

import db
from config import settings
from keyboards import BTN_CANCEL, main_menu

log = logging.getLogger(__name__)
router = Router(name="common")

WELCOME = (
    "Assalomu alaykum! 👋\n\n"
    "Men tadbirlar uchun rasmiy <b>BAYONNOMA</b> hujjatini (Word / PDF) tayyorlab beraman.\n"
    "Savollarga javob bering — qolganini o'zim qilaman.\n\n"
    "Quyidagi menyudan tanlang:"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await db.ensure_user(message.from_user.id)
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📝 <b>Yangi bayonnoma</b> — savollar orqali hujjat yaratish\n"
        "📂 <b>Mening bayonnomalarim</b> — oxirgi 10 ta hujjatni qayta yuklab olish\n"
        "⚙️ <b>Doimiy ma'lumotlar</b> — universitet, fakultet, tasdiqlovchi, kotib, shahar\n\n"
        "/cancel — joriy amalni bekor qilish",
        reply_markup=main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi. Asosiy menyu:", reply_markup=main_menu())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if message.from_user.id not in settings.admin_ids:
        await message.answer("Bu buyruq faqat admin uchun.")
        return
    s = await db.stats()
    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👤 Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"📄 Yaratilgan bayonnomalar: <b>{s['protocols']}</b>\n"
        f"📅 Bugun yaratilgan: <b>{s['today']}</b>"
    )


async def on_error(event: ErrorEvent) -> bool:
    log.exception("Kutilmagan xatolik: %s", event.exception, exc_info=event.exception)
    update = event.update
    target = None
    if update.message:
        target = update.message
    elif update.callback_query and update.callback_query.message:
        target = update.callback_query.message
        try:
            await update.callback_query.answer()
        except Exception:
            pass
    if target is not None:
        try:
            await target.answer(
                "⚠️ Kutilmagan xatolik yuz berdi. Iltimos, qayta urinib ko'ring "
                "yoki /start buyrug'ini bosing."
            )
        except Exception:
            log.exception("Xato xabarini yuborib bo'lmadi")
    return True
