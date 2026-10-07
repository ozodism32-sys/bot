"""Mening bayonnomalarim: ro'yxat, qayta yuklab olish, nusxa asosida yangisini yaratish."""
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

import db
import keyboards as kb
from pdf_converter import PdfConversionError
from protocol_service import clean_data, ensure_files
from utils import protocol_filename

from .helpers import h
from .protocol import show_summary, start_wizard

log = logging.getLogger(__name__)
router = Router(name="history")


@router.message(F.text == kb.BTN_HISTORY)
async def history(message: Message, state: FSMContext) -> None:
    await state.clear()
    protocols = await db.list_protocols(message.from_user.id, limit=10)
    if not protocols:
        await message.answer("Sizda hali bayonnomalar yo'q. «📝 Yangi bayonnoma» tugmasini bosing.",
                             reply_markup=kb.main_menu())
        return
    await message.answer("📂 Oxirgi bayonnomalaringiz (10 tagacha):", reply_markup=kb.history_kb(protocols))


@router.callback_query(F.data.startswith("hist:"))
async def history_item(cb: CallbackQuery) -> None:
    protocol = await db.get_protocol(int(cb.data.split(":")[1]), cb.from_user.id)
    if not protocol:
        await cb.answer("Bayonnoma topilmadi.", show_alert=True)
        return
    await cb.answer()
    d = protocol["data"]
    await cb.message.answer(
        f"📄 <b>№{protocol['id']}</b> — {h(d.get('event_name'))} ({h(d.get('event_type'))})\n"
        f"📅 {h(d.get('date'))}, soat {h(d.get('time'))}\n"
        f"📍 {h(d.get('venue'))}\n"
        f"🕓 Yaratilgan: {h(protocol['created_at'].replace('T', ' '))}",
        reply_markup=kb.history_item_kb(protocol["id"]),
    )


@router.callback_query(F.data.startswith("dl:"))
async def download(cb: CallbackQuery, bot: Bot) -> None:
    _, pid, fmt = cb.data.split(":")
    protocol = await db.get_protocol(int(pid), cb.from_user.id)
    if not protocol:
        await cb.answer("Bayonnoma topilmadi.", show_alert=True)
        return
    await cb.answer("⏳ Tayyorlanmoqda...")
    await bot.send_chat_action(cb.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
    try:
        docx, pdf = await ensure_files(protocol, fmt)
    except PdfConversionError as e:
        log.error("PDF xatosi: %s", e)
        await cb.message.answer("⚠️ PDF yaratishda xatolik. DOCX formatini tanlab ko'ring.")
        return
    except Exception:
        log.exception("Faylni tayyorlashda xato")
        await cb.message.answer("⚠️ Faylni tayyorlashda xatolik yuz berdi.")
        return
    d = protocol["data"]
    if docx:
        await cb.message.answer_document(FSInputFile(docx, filename=protocol_filename(d, "docx")))
    if pdf:
        await cb.message.answer_document(FSInputFile(pdf, filename=protocol_filename(d, "pdf")))


@router.callback_query(F.data.startswith("copy:"))
async def copy_protocol(cb: CallbackQuery, state: FSMContext) -> None:
    protocol = await db.get_protocol(int(cb.data.split(":")[1]), cb.from_user.id)
    if not protocol:
        await cb.answer("Bayonnoma topilmadi.", show_alert=True)
        return
    await cb.answer()
    await start_wizard(state, cb.from_user.id, initial=clean_data(protocol["data"]))
    await cb.message.answer(
        "🔁 Ma'lumotlar nusxalandi. Quyidagi xulosadan «✏️ Tahrirlash» orqali kerakli "
        "maydonlarni o'zgartiring va «✅ Tasdiqlash»ni bosing.",
        reply_markup=kb.nav_menu(),
    )
    await show_summary(cb.message, state)
