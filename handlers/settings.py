"""Doimiy ma'lumotlar: universitet, fakultet, tasdiqlovchi, kotib, shahar."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
import keyboards as kb
from states import SettingsForm
from steps import PROFILE_TITLES

from .helpers import h

router = Router(name="settings")


async def show_settings(message: Message, user_id: int) -> None:
    profile = await db.get_profile(user_id)
    lines = ["⚙️ <b>Doimiy ma'lumotlar</b>",
             "Bu qiymatlar yangi bayonnoma yaratishda avtomatik taklif qilinadi.\n"]
    for field, title in PROFILE_TITLES.items():
        lines.append(f"<b>{title}:</b> {h(profile.get(field) or '—')}")
    lines.append("\nO'zgartirish uchun tanlang:")
    await message.answer("\n".join(lines), reply_markup=kb.settings_kb())


@router.message(F.text == kb.BTN_SETTINGS)
async def settings_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await db.ensure_user(message.from_user.id)
    await show_settings(message, message.from_user.id)


@router.callback_query(F.data.startswith("set:"))
async def settings_choose(cb: CallbackQuery, state: FSMContext) -> None:
    field = cb.data.split(":", 1)[1]
    if field not in PROFILE_TITLES:
        await cb.answer()
        return
    await cb.answer()
    await state.set_state(SettingsForm.value)
    await state.update_data(field=field)
    await cb.message.answer(f"<b>{PROFILE_TITLES[field]}</b> uchun yangi qiymatni kiriting:",
                            reply_markup=kb.nav_menu())


@router.message(SettingsForm.value, F.text == kb.BTN_BACK)
async def settings_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Asosiy menyu", reply_markup=kb.main_menu())
    await show_settings(message, message.from_user.id)


@router.message(SettingsForm.value, F.text)
async def settings_value(message: Message, state: FSMContext) -> None:
    value = message.text.strip()[:300]
    if not value:
        await message.answer("Qiymat bo'sh bo'lmasligi kerak.")
        return
    data = await state.get_data()
    await db.update_profile(message.from_user.id, **{data["field"]: value})
    await state.clear()
    await message.answer("✅ Saqlandi.", reply_markup=kb.main_menu())
    await show_settings(message, message.from_user.id)
