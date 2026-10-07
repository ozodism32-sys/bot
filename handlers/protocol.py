"""Yangi bayonnoma yaratish (FSM): savollar, AI matn, rasmlar, xulosa, format tanlash."""
import asyncio
import logging
import shutil
import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

import ai_writer
import db
import keyboards as kb
from pdf_converter import PdfConversionError
from protocol_service import create_and_build, draft_dir
from states import ProtocolForm
from steps import BLOCK_NAMES, EVENT_TYPES, MAX_PHOTOS, STEP_BY_KEY, next_step, prev_step
from utils import parse_date, parse_time, protocol_filename, split_lines, split_paragraphs

from .helpers import drop_kb, format_block, h, send_long, summary_text

log = logging.getLogger(__name__)
router = Router(name="protocol")

_photo_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

PROFILE_MAP = {  # qadam -> users jadvali ustuni
    "approver_position": "tasdiqlovchi_lavozim",
    "approver_name": "tasdiqlovchi_fio",
    "university": "universitet",
    "faculty": "fakultet",
    "city": "shahar",
    "secretary": "kotib_fio",
}

TEXT_STATES = (
    ProtocolForm.approver_position, ProtocolForm.approver_name, ProtocolForm.university,
    ProtocolForm.faculty, ProtocolForm.event_name, ProtocolForm.event_type,
    ProtocolForm.event_type_custom, ProtocolForm.number, ProtocolForm.date, ProtocolForm.city,
    ProtocolForm.participants, ProtocolForm.venue, ProtocolForm.count, ProtocolForm.time,
    ProtocolForm.secretary,
)
MAX_TEXT_LEN = 500


# ============================================================ umumiy oqim
def _empty(value) -> bool:
    return value in (None, "", [])


async def start_wizard(state: FSMContext, user_id: int, initial: dict | None = None) -> None:
    await state.clear()
    await db.ensure_user(user_id)
    profile = await db.get_profile(user_id)
    await state.set_data({
        **(initial or {}),
        "profile": profile,
        "draft_id": uuid.uuid4().hex,
        "editing": bool(initial),
    })


async def ask_step(message: Message, state: FSMContext, key: str) -> None:
    step = STEP_BY_KEY[key]
    await state.set_state(getattr(ProtocolForm, key))
    await state.update_data(step=key)
    data = await state.get_data()
    current = data.get(key)
    prev_value = current
    if _empty(prev_value) and step.profile:
        prev_value = data.get("profile", {}).get(step.profile)

    text = step.prompt
    if step.kind in ("text", "int", "time"):
        markup = kb.inline([kb.keep_row(key, prev_value)])
    elif step.kind == "date":
        markup = kb.inline([[("📅 Bugun", "today")], kb.keep_row(key, prev_value)])
    elif step.kind == "number":
        markup = kb.inline([[("⏭ O'tkazib yuborish", "skipnum")], kb.keep_row(key, prev_value)])
    elif step.kind == "event_type":
        markup = kb.event_type_kb(current)
        text += "\n<i>Yoki turini o'zingiz yozib yuboring.</i>"
    elif step.kind == "block":
        markup = kb.block_mode_kb(key, not _empty(current))
        if not _empty(current):
            text += "\n\n<b>Joriy matn:</b>\n" + format_block(key, current)
    elif step.kind == "photos":
        await state.update_data(new_photos=[])
        markup = kb.photos_kb(len(data.get("photos") or []))
    elif step.kind == "signers":
        signers = data.get("signers") or []
        if signers:
            text += "\n\n<b>Qo'shilganlar:</b>\n" + "\n".join(
                f"• {h(s['position'])}: {h(s['name'])}" for s in signers)
        markup = kb.signers_kb(bool(signers))
    else:
        markup = None
    await send_long(message, text, reply_markup=markup)


async def advance(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("editing"):
        await show_summary(message, state)
        return
    nxt = next_step(data["step"])
    if nxt:
        await ask_step(message, state, nxt)
    else:
        await show_summary(message, state)


async def set_and_advance(message: Message, state: FSMContext, key: str, value) -> None:
    await state.update_data({key: value})
    await advance(message, state)


async def show_summary(message: Message, state: FSMContext) -> None:
    await state.set_state(ProtocolForm.summary)
    await state.update_data(editing=True)
    data = await state.get_data()
    await send_long(message, summary_text(data), reply_markup=kb.summary_kb())


async def _check_step(cb: CallbackQuery, state: FSMContext, key: str) -> bool:
    data = await state.get_data()
    if data.get("step") != key:
        await cb.answer("Bu tugma eskirgan.", show_alert=False)
        return False
    return True


# ============================================================ boshlash / navigatsiya
@router.message(F.text == kb.BTN_NEW)
async def new_protocol(message: Message, state: FSMContext) -> None:
    await start_wizard(state, message.from_user.id)
    await message.answer(
        "📝 Yangi bayonnoma yaratishni boshlaymiz.\n"
        "Har qadamda «⬅️ Orqaga» yoki «❌ Bekor qilish» tugmalaridan foydalanishingiz mumkin.",
        reply_markup=kb.nav_menu(),
    )
    await ask_step(message, state, "approver_position")


@router.message(StateFilter(ProtocolForm), F.text == kb.BTN_BACK)
async def go_back(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    data = await state.get_data()
    step = data.get("step", "approver_position")
    if current_state == ProtocolForm.format_select.state:
        await show_summary(message, state)
    elif current_state == ProtocolForm.summary.state:
        await ask_step(message, state, "signers")
    elif data.get("editing"):
        await show_summary(message, state)
    elif current_state == getattr(ProtocolForm, step).state:
        await ask_step(message, state, prev_step(step) or step)
    else:  # yordamchi holat — joriy qadamni qaytadan so'raymiz
        await ask_step(message, state, step)


@router.callback_query(StateFilter(ProtocolForm), F.data.startswith("keep:"))
async def keep_value(cb: CallbackQuery, state: FSMContext) -> None:
    key = cb.data.split(":", 1)[1]
    if not await _check_step(cb, state, key):
        return
    await cb.answer()
    data = await state.get_data()
    value = data.get(key)
    step = STEP_BY_KEY[key]
    if _empty(value) and step.profile:
        value = data.get("profile", {}).get(step.profile)
    await drop_kb(cb)
    if key == "photos":
        await advance(cb.message, state)
    else:
        await cb.message.answer(f"✅ {h(value if not isinstance(value, list) else 'saqlandi')}")
        await set_and_advance(cb.message, state, key, value)


# ============================================================ oddiy matnli qadamlar
@router.message(StateFilter(*TEXT_STATES), F.text)
async def text_input(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    key = current_state.split(":", 1)[1]
    if key == "event_type_custom":
        key = "event_type"
    kind = STEP_BY_KEY[key].kind
    text = message.text.strip()

    if not text:
        await message.answer("Iltimos, qiymat kiriting.")
        return
    if len(text) > MAX_TEXT_LEN:
        await message.answer(f"Matn juda uzun (maksimal {MAX_TEXT_LEN} belgi). Qisqaroq yozing.")
        return

    if kind == "int":
        digits = text.replace(" ", "")
        if not digits.isdigit() or not 0 < int(digits) <= 100000:
            await message.answer("❗️ Faqat musbat raqam kiriting. Masalan: <b>30</b>")
            return
        value = int(digits)
    elif kind == "time":
        value = parse_time(text)
        if not value:
            await message.answer("❗️ Vaqt SS:DD formatida bo'lishi kerak. Masalan: <b>10:00</b>")
            return
    elif kind == "date":
        d = parse_date(text)
        if not d or not 2000 <= d.year <= 2100:
            await message.answer("❗️ Sana KK.OO.YYYY formatida bo'lishi kerak. Masalan: <b>18.09.2026</b>")
            return
        value = d.strftime("%d.%m.%Y")
    elif kind == "number":
        if len(text) > 20:
            await message.answer("❗️ Raqam juda uzun.")
            return
        value = text.lstrip("№").strip()
    else:
        value = text
    await set_and_advance(message, state, key, value)


@router.message(StateFilter(*TEXT_STATES))
async def text_expected(message: Message) -> None:
    await message.answer("Iltimos, javobni matn ko'rinishida yuboring.")


@router.callback_query(ProtocolForm.date, F.data == "today")
async def date_today(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    value = date.today().strftime("%d.%m.%Y")
    await drop_kb(cb)
    await cb.message.answer(f"📅 {value}")
    await set_and_advance(cb.message, state, "date", value)


@router.callback_query(ProtocolForm.number, F.data == "skipnum")
async def skip_number(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await drop_kb(cb)
    await set_and_advance(cb.message, state, "number", "")


@router.callback_query(ProtocolForm.event_type, F.data.startswith("etype:"))
async def choose_event_type(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    choice = cb.data.split(":", 1)[1]
    await drop_kb(cb)
    if choice == "other":
        await state.set_state(ProtocolForm.event_type_custom)
        await cb.message.answer("Tadbir turini yozing. <i>Masalan: Ekskursiya</i>")
        return
    value = EVENT_TYPES[int(choice)]
    await cb.message.answer(f"✅ {h(value)}")
    await set_and_advance(cb.message, state, "event_type", value)


# ============================================================ AI / qo'lda yoziladigan bloklar
MANUAL_HINTS = {
    "agenda": "Kun tartibi bandlarini yozing — <b>har bir band yangi qatordan</b>.",
    "heard": "ESHITILDI matnini yozing. Xatboshilarni <b>bo'sh qator</b> bilan ajrating "
             "(yoki har birini yangi qatordan yozing).",
    "decisions": "Qarorlarni yozing — <b>har bir band yangi qatordan</b>, buyruq maylida "
                 "(masalan: «...tashkil etilsin»).",
}


def _block_text(key: str, items: list[str]) -> str:
    """Foydalanuvchi nusxalab tahrirlashi uchun oddiy matn."""
    return "\n\n".join(items) if key == "heard" else "\n".join(items)


async def _ask_manual(message: Message, state: FSMContext, key: str, draft: list[str] | None) -> None:
    await state.set_state(ProtocolForm.block_manual)
    await state.update_data(block_key=key)
    await message.answer(f"✍️ {MANUAL_HINTS[key]}")
    if draft:
        await message.answer("Quyidagi matnni nusxalab, tahrirlab yuborishingiz mumkin:")
        await send_long(message, _block_text(key, draft), parse_mode=None)


async def _run_ai(message: Message, state: FSMContext, bot: Bot, key: str) -> None:
    data = await state.get_data()
    await state.set_state(ProtocolForm.block_review)
    await state.update_data(block_key=key, draft=None)
    wait = await message.answer(f"⏳ AI «{BLOCK_NAMES[key]}» matnini yozmoqda, biroz kuting...")
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        if key == "agenda":
            items = await ai_writer.generate_agenda(data)
        elif key == "heard":
            items = await ai_writer.generate_heard(data, data.get("heard_hint"))
        else:
            items = await ai_writer.generate_decisions(data)
    except ai_writer.AIWriterError as e:
        await wait.edit_text(
            f"⚠️ {h(e)}\nMatnni o'zingiz yozishingiz yoki qayta urinib ko'rishingiz mumkin.",
            reply_markup=kb.ai_failed_kb(key),
        )
        return
    except Exception:
        log.exception("AI kutilmagan xato")
        await wait.edit_text(
            "⚠️ AI ishlamay qoldi. Matnni o'zingiz yozishingiz mumkin.",
            reply_markup=kb.ai_failed_kb(key),
        )
        return
    await state.update_data(draft=items)
    await wait.delete()
    await send_long(
        message,
        f"🤖 <b>{BLOCK_NAMES[key]}:</b>\n\n{format_block(key, items)}",
        reply_markup=kb.block_review_kb(key),
    )


@router.callback_query(StateFilter(ProtocolForm), F.data.startswith("blk:"))
async def block_action(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    _, key, action = cb.data.split(":")
    if not await _check_step(cb, state, key):
        return
    await cb.answer()
    await drop_kb(cb)
    data = await state.get_data()

    if action == "manual":
        await _ask_manual(cb.message, state, key, data.get(key) or None)
    elif action == "ai":
        if key == "heard" and await state.get_state() != ProtocolForm.block_review.state:
            await state.set_state(ProtocolForm.heard_hint)
            await cb.message.answer(
                "💬 Tadbirda nimalar gapirildi? Qisqacha izoh yozing — AI shu asosida matn tuzadi.\n"
                "<i>Masalan: muzey tarixi, Fayoztepa topilmalari, talabalar savollari</i>",
                reply_markup=kb.inline([[("⏭ Izohsiz davom etish", "hint:skip")]]),
            )
        else:
            await _run_ai(cb.message, state, bot, key)
    elif action == "regen":
        await _run_ai(cb.message, state, bot, key)
    elif action == "accept":
        draft = data.get("draft")
        if not draft:
            await ask_step(cb.message, state, key)
            return
        await cb.message.answer("✅ Qabul qilindi.")
        await set_and_advance(cb.message, state, key, draft)
    elif action == "edit":
        await _ask_manual(cb.message, state, key, data.get("draft"))


@router.message(ProtocolForm.heard_hint, F.text)
async def heard_hint(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(heard_hint=message.text.strip()[:1500])
    await _run_ai(message, state, bot, "heard")


@router.callback_query(ProtocolForm.heard_hint, F.data == "hint:skip")
async def heard_hint_skip(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await cb.answer()
    await drop_kb(cb)
    await state.update_data(heard_hint=None)
    await _run_ai(cb.message, state, bot, "heard")


@router.message(ProtocolForm.block_manual, F.text)
async def block_manual_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    key = data["block_key"]
    items = split_paragraphs(message.text) if key == "heard" else split_lines(message.text)
    if not items:
        await message.answer("Matn bo'sh. Iltimos, qaytadan yozing.")
        return
    await message.answer(f"✅ {BLOCK_NAMES[key]} saqlandi ({len(items)} ta {'xatboshi' if key == 'heard' else 'band'}).")
    await set_and_advance(message, state, key, items)


@router.message(StateFilter(ProtocolForm.block_manual, ProtocolForm.heard_hint))
async def block_text_expected(message: Message) -> None:
    await message.answer("Iltimos, matn yuboring.")


# ============================================================ rasmlar
@router.message(ProtocolForm.photos, F.photo | F.document)
async def photo_received(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.photo:
        file = message.photo[-1]
        ext, size = ".jpg", file.file_size
    else:
        doc = message.document
        if not (doc.mime_type or "").startswith("image/"):
            await message.answer("❗️ Faqat rasm fayllari qabul qilinadi (JPG, PNG, ...).")
            return
        file, size = doc, doc.file_size
        ext = Path(doc.file_name or "").suffix.lower() or ".jpg"
    if size and size > 20 * 1024 * 1024:
        await message.answer("❗️ Rasm hajmi 20 MB dan oshmasligi kerak.")
        return

    user_id = message.from_user.id
    async with _photo_locks[user_id]:  # albom yuborilganda bir vaqtda kelgan rasmlar uchun
        data = await state.get_data()
        photos = list(data.get("new_photos") or [])
        if len(photos) >= MAX_PHOTOS:
            await message.answer(f"Maksimal {MAX_PHOTOS} ta rasm. «✅ Tayyor» tugmasini bosing.",
                                 reply_markup=kb.inline([[("✅ Tayyor", "ph:done")]]))
            return
        dest = draft_dir(user_id, data["draft_id"]) / f"{uuid.uuid4().hex}{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            await bot.download(file, destination=dest)
        except Exception:
            log.exception("Rasmni yuklab bo'lmadi")
            await message.answer("⚠️ Rasmni yuklab bo'lmadi, qaytadan yuboring.")
            return
        photos.append(str(dest))
        await state.update_data(new_photos=photos)
    await message.answer(
        f"🖼 {len(photos)}/{MAX_PHOTOS} qabul qilindi.",
        reply_markup=kb.inline([[("✅ Tayyor", "ph:done")]]),
    )


@router.message(ProtocolForm.photos)
async def photo_expected(message: Message) -> None:
    await message.answer("Rasm yuboring yoki «✅ Tayyor» / «➡️ Rasmsiz davom etish» tugmasini bosing.",
                         reply_markup=kb.inline([[("✅ Tayyor", "ph:done")],
                                                 [("➡️ Rasmsiz davom etish", "ph:none")]]))


@router.callback_query(ProtocolForm.photos, F.data.in_({"ph:done", "ph:none"}))
async def photos_done(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await drop_kb(cb)
    async with _photo_locks[cb.from_user.id]:
        data = await state.get_data()
        if cb.data == "ph:none":
            photos = []
        else:
            photos = data.get("new_photos") or data.get("photos") or []
    await cb.message.answer(f"✅ Rasmlar: {len(photos)} ta")
    await set_and_advance(cb.message, state, "photos", photos)


# ============================================================ imzolar
@router.callback_query(ProtocolForm.signers, F.data.startswith("sg:"))
async def signers_action(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await drop_kb(cb)
    action = cb.data.split(":", 1)[1]
    if action == "add":
        await state.set_state(ProtocolForm.signer_position)
        await cb.message.answer("Imzo qo'yuvchining <b>lavozimini</b> kiriting.\n<i>Masalan: Yig'ilish raisi</i>")
    elif action == "clear":
        await state.update_data(signers=[])
        await ask_step(cb.message, state, "signers")
    else:
        await advance(cb.message, state)


@router.message(ProtocolForm.signer_position, F.text)
async def signer_position(message: Message, state: FSMContext) -> None:
    await state.update_data(tmp_signer_position=message.text.strip()[:200])
    await state.set_state(ProtocolForm.signer_name)
    await message.answer("Endi <b>F.I.Sh</b> (I.Familiya) ni kiriting.\n<i>Masalan: B.Karimov</i>")


@router.message(ProtocolForm.signer_name, F.text)
async def signer_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    signers = list(data.get("signers") or [])
    signers.append({"position": data.get("tmp_signer_position", ""), "name": message.text.strip()[:200]})
    await state.update_data(signers=signers)
    await ask_step(message, state, "signers")


# ============================================================ xulosa / tahrirlash / tasdiqlash
@router.callback_query(ProtocolForm.summary, F.data == "sum:edit")
async def summary_edit(cb: CallbackQuery) -> None:
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=kb.edit_fields_kb())


@router.callback_query(ProtocolForm.summary, F.data == "sum:back")
async def summary_back(cb: CallbackQuery) -> None:
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=kb.summary_kb())


@router.callback_query(ProtocolForm.summary, F.data.startswith("ed:"))
async def edit_field(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    key = cb.data.split(":", 1)[1]
    if key not in STEP_BY_KEY:
        return
    await drop_kb(cb)
    await state.update_data(editing=True)
    await ask_step(cb.message, state, key)


@router.callback_query(ProtocolForm.summary, F.data == "sum:ok")
async def summary_ok(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    required = ["approver_position", "approver_name", "university", "faculty", "event_name",
                "event_type", "date", "city", "participants", "venue", "count", "time", "secretary"]
    missing = [STEP_BY_KEY[k].title for k in required if _empty(data.get(k))]
    if missing:
        await cb.answer("To'ldirilmagan: " + ", ".join(missing), show_alert=True)
        return
    await cb.answer()
    await drop_kb(cb)
    await state.set_state(ProtocolForm.format_select)
    await cb.message.answer("Bayonnomani qaysi formatda yuklab olmoqchisiz?", reply_markup=kb.format_kb())


@router.callback_query(ProtocolForm.format_select, F.data.startswith("fmt:"))
async def format_chosen(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    fmt = cb.data.split(":", 1)[1]
    await cb.answer()
    await drop_kb(cb)
    data = await state.get_data()
    user_id = cb.from_user.id
    wait = await cb.message.answer("⏳ Hujjat tayyorlanmoqda...")
    await bot.send_chat_action(cb.message.chat.id, ChatAction.UPLOAD_DOCUMENT)

    try:
        result = await create_and_build(user_id, data, want_pdf=fmt in ("pdf", "both"))
    except PdfConversionError as e:
        log.error("PDF xatosi: %s", e)
        await wait.edit_text("⚠️ PDF yaratishda xatolik. Word (DOCX) formatini tanlab ko'ring.",
                             reply_markup=kb.format_kb())
        return
    except Exception:
        log.exception("Hujjat yaratishda xato")
        await wait.edit_text("⚠️ Hujjat yaratishda xatolik yuz berdi. Qayta urinib ko'ring.",
                             reply_markup=kb.format_kb())
        return

    # Doimiy ma'lumotlarni keyingi safar uchun saqlaymiz
    await db.update_profile(user_id, **{col: data.get(k) for k, col in PROFILE_MAP.items()})

    await wait.delete()
    pdata = result["data"]
    if fmt in ("docx", "both"):
        await cb.message.answer_document(
            FSInputFile(result["docx_path"], filename=protocol_filename(pdata, "docx")))
    if fmt in ("pdf", "both") and result["pdf_path"]:
        await cb.message.answer_document(
            FSInputFile(result["pdf_path"], filename=protocol_filename(pdata, "pdf")))

    shutil.rmtree(draft_dir(user_id, data["draft_id"]), ignore_errors=True)
    await state.clear()
    await cb.message.answer("✅ Bayonnoma tayyor!", reply_markup=kb.main_menu())
    await cb.message.answer("Keyingi bayonnomani tezroq yaratish uchun:",
                            reply_markup=kb.after_send_kb(result["id"]))


@router.message(StateFilter(ProtocolForm.summary, ProtocolForm.format_select,
                            ProtocolForm.block_review, ProtocolForm.signers))
async def use_buttons(message: Message) -> None:
    await message.answer("Iltimos, yuqoridagi tugmalardan foydalaning.")
