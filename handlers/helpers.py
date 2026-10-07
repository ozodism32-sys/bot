"""Handlerlar uchun umumiy yordamchilar."""
from html import escape

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from steps import STEP_BY_KEY
from utils import date_to_words

TG_LIMIT = 4000


def h(value) -> str:
    return escape(str(value if value is not None else ""))


async def drop_kb(cb: CallbackQuery) -> None:
    """Bosilgan tugmalarni olib tashlaydi (ikki marta bosishdan himoya)."""
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass


def split_message(text: str, limit: int = TG_LIMIT) -> list[str]:
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [""]


async def send_long(message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None,
                    parse_mode: str | None = "HTML") -> Message:
    chunks = split_message(text)
    sent = None
    for i, chunk in enumerate(chunks):
        sent = await message.answer(
            chunk, parse_mode=parse_mode,
            reply_markup=reply_markup if i == len(chunks) - 1 else None,
        )
    return sent


def format_block(key: str, items: list[str]) -> str:
    if key == "heard":
        return "\n\n".join(h(p) for p in items)
    return "\n".join(f"{i}. {h(x)}" for i, x in enumerate(items, 1))


def summary_text(data: dict) -> str:
    t = lambda k: STEP_BY_KEY[k].title  # noqa: E731
    signers = data.get("signers") or []
    sign_lines = [f"• {h(s['position'])}: {h(s['name'])}" for s in signers]
    sign_lines.append(f"• Yig'ilish kotibi: {h(data.get('secretary'))}")
    lines = [
        "📋 <b>BAYONNOMA XULOSASI</b>",
        "",
        f"<b>{t('approver_position')}:</b> {h(data.get('approver_position'))}",
        f"<b>{t('approver_name')}:</b> {h(data.get('approver_name'))}",
        f"<b>{t('university')}:</b> {h(data.get('university'))}",
        f"<b>{t('faculty')}:</b> {h(data.get('faculty'))}",
        f"<b>{t('event_name')}:</b> {h(data.get('event_name'))}",
        f"<b>{t('event_type')}:</b> {h(data.get('event_type'))}",
        f"<b>{t('number')}:</b> № {h(data.get('number') or '____')}",
        f"<b>{t('date')}:</b> {h(data.get('date'))} ({h(date_to_words(data.get('date', '')))})",
        f"<b>{t('city')}:</b> {h(data.get('city'))}",
        f"<b>{t('participants')}:</b> {h(data.get('participants'))}",
        f"<b>{t('venue')}:</b> {h(data.get('venue'))}",
        f"<b>{t('count')}:</b> Jami {h(data.get('count'))} nafar",
        f"<b>{t('time')}:</b> {h(data.get('time'))}",
        "",
        "<b>KUN TARTIBI:</b>",
        format_block("agenda", data.get("agenda") or []),
        "",
        "<b>ESHITILDI:</b>",
        format_block("heard", data.get("heard") or []),
        "",
        f"<b>{t('photos')}:</b> {len(data.get('photos') or [])} ta",
        "",
        "<b>QAROR QILINDI:</b>",
        format_block("decisions", data.get("decisions") or []),
        "",
        "<b>Imzolar:</b>",
        *sign_lines,
    ]
    return "\n".join(lines)
