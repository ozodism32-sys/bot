"""Reply va inline klaviaturalar."""
from aiogram.types import InlineKeyboardButton as IB, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from steps import EVENT_TYPES, PROFILE_TITLES, STEPS

BTN_NEW = "📝 Yangi bayonnoma"
BTN_HISTORY = "📂 Mening bayonnomalarim"
BTN_SETTINGS = "⚙️ Doimiy ma'lumotlar"
BTN_BACK = "⬅️ Orqaga"
BTN_CANCEL = "❌ Bekor qilish"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_NEW)],
                  [KeyboardButton(text=BTN_HISTORY), KeyboardButton(text=BTN_SETTINGS)]],
        resize_keyboard=True,
    )


def nav_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK), KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def _short(text: str, n: int = 40) -> str:
    text = str(text).replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


def inline(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup | None:
    rows = [[IB(text=t, callback_data=c) for t, c in row] for row in rows if row]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def keep_row(key: str, value) -> list[tuple[str, str]]:
    if value in (None, "", []):
        return []
    return [(f"✅ Avvalgisini ishlatish: {_short(value)}", f"keep:{key}")]


def event_type_kb(current: str | None) -> InlineKeyboardMarkup:
    rows = [[(t, f"etype:{i}") for i, t in enumerate(EVENT_TYPES[j:j + 2], start=j)]
            for j in range(0, len(EVENT_TYPES), 2)]
    rows.append([("✍️ Boshqa (qo'lda yozish)", "etype:other")])
    rows.insert(0, keep_row("event_type", current))
    return inline(rows)


def block_mode_kb(key: str, has_value: bool) -> InlineKeyboardMarkup:
    rows = [[("🤖 AI yozsin", f"blk:{key}:ai"), ("✍️ O'zim yozaman", f"blk:{key}:manual")]]
    if has_value:
        rows.insert(0, [("✅ Joriy matnni qoldirish", f"keep:{key}")])
    return inline(rows)


def block_review_kb(key: str) -> InlineKeyboardMarkup:
    return inline([
        [("✅ Qabul qilish", f"blk:{key}:accept")],
        [("🔄 Qayta yozish", f"blk:{key}:regen"), ("✍️ O'zim tahrirlayman", f"blk:{key}:edit")],
    ])


def ai_failed_kb(key: str) -> InlineKeyboardMarkup:
    return inline([[("🔄 Qayta urinish", f"blk:{key}:ai"), ("✍️ O'zim yozaman", f"blk:{key}:manual")]])


def photos_kb(existing: int) -> InlineKeyboardMarkup:
    rows = [[("✅ Tayyor", "ph:done")], [("➡️ Rasmsiz davom etish", "ph:none")]]
    if existing:
        rows.insert(0, [(f"✅ Joriy rasmlarni qoldirish ({existing} ta)", "keep:photos")])
    return inline(rows)


def signers_kb(has_extra: bool) -> InlineKeyboardMarkup:
    rows = [[("➕ Yana imzo qo'shish", "sg:add")], [("✅ Davom etish", "sg:done")]]
    if has_extra:
        rows.insert(1, [("🗑 Qo'shimcha imzolarni o'chirish", "sg:clear")])
    return inline(rows)


def summary_kb() -> InlineKeyboardMarkup:
    return inline([[("✏️ Tahrirlash", "sum:edit"), ("✅ Tasdiqlash", "sum:ok")]])


def edit_fields_kb() -> InlineKeyboardMarkup:
    buttons = [(s.title, f"ed:{s.key}") for s in STEPS]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([("⬅️ Xulosaga qaytish", "sum:back")])
    return inline(rows)


def format_kb() -> InlineKeyboardMarkup:
    return inline([[("📄 PDF", "fmt:pdf"), ("📝 Word (DOCX)", "fmt:docx")],
                   [("📦 Ikkalasi ham", "fmt:both")]])


def after_send_kb(protocol_id: int) -> InlineKeyboardMarkup:
    return inline([[("🔁 Shu ma'lumotlar asosida yangisini yaratish", f"copy:{protocol_id}")]])


def history_kb(protocols: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for p in protocols:
        d = p["data"]
        rows.append([(f"№{p['id']} · {_short(d.get('event_name', ''), 28)} · {d.get('date', '')}",
                      f"hist:{p['id']}")])
    return inline(rows)


def history_item_kb(protocol_id: int) -> InlineKeyboardMarkup:
    return inline([
        [("📄 PDF", f"dl:{protocol_id}:pdf"), ("📝 DOCX", f"dl:{protocol_id}:docx"),
         ("📦 Ikkalasi", f"dl:{protocol_id}:both")],
        [("🔁 Shu asosida yangisini yaratish", f"copy:{protocol_id}")],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    buttons = [(title, f"set:{field}") for field, title in PROFILE_TITLES.items()]
    return inline([buttons[i:i + 2] for i in range(0, len(buttons), 2)])
