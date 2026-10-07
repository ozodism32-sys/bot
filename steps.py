"""Bayonnoma yaratish qadamlarining tavsifi (tartib, savol matni, turi)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    key: str
    title: str          # Xulosa va tahrirlash menyusida ko'rinadigan nom
    prompt: str
    kind: str = "text"  # text | int | time | date | number | event_type | block | photos | signers
    profile: str | None = None   # users jadvalidagi ustun (avvalgi qiymat uchun)


STEPS: list[Step] = [
    Step("approver_position", "Tasdiqlovchi lavozimi",
         "1/18. Tasdiqlovchining <b>lavozimini</b> kiriting.\n<i>Masalan: Iqtisodiyot fakulteti dekani</i>",
         profile="tasdiqlovchi_lavozim"),
    Step("approver_name", "Tasdiqlovchi I.Familiyasi",
         "2/18. Tasdiqlovchining <b>I.Familiyasini</b> kiriting.\n<i>Masalan: A.Turakulov</i>",
         profile="tasdiqlovchi_fio"),
    Step("university", "Universitet",
         "3/18. <b>Universitet</b> nomini kiriting.\n<i>Masalan: Termiz davlat universiteti</i>",
         profile="universitet"),
    Step("faculty", "Fakultet",
         "4/18. <b>Fakultet</b> nomini kiriting.\n<i>Masalan: Iqtisodiyot fakulteti</i>",
         profile="fakultet"),
    Step("event_name", "Tadbir nomi",
         "5/18. <b>Tadbir nomini</b> kiriting.\n<i>Masalan: Arxeologiya muzeyi</i>"),
    Step("event_type", "Tadbir turi", "6/18. <b>Tadbir turini</b> tanlang:", kind="event_type"),
    Step("number", "Bayonnoma raqami",
         "7/18. <b>Bayonnoma raqamini</b> kiriting yoki o'tkazib yuboring (hujjatda ____ qoladi).",
         kind="number"),
    Step("date", "Sana",
         "8/18. Tadbir <b>sanasini</b> KK.OO.YYYY formatida kiriting yoki «Bugun»ni bosing.\n"
         "<i>Masalan: 18.09.2026</i>", kind="date"),
    Step("city", "Shahar", "9/18. <b>Shahar</b> nomini kiriting.\n<i>Masalan: Termiz</i>",
         profile="shahar"),
    Step("participants", "Tadbir ishtirokchilari",
         "10/18. <b>Tadbir ishtirokchilarini</b> kiriting.\n"
         "<i>Masalan: Fakultet tyutorlari, 1-bosqich talaba yoshlari</i>"),
    Step("venue", "O'tkazish joyi",
         "11/18. Tadbir <b>o'tkazish joyini</b> kiriting.\n<i>Masalan: Termiz arxeologiya muzeyi</i>"),
    Step("count", "Ishtirokchilar soni",
         "12/18. <b>Ishtirokchilar sonini</b> kiriting (faqat raqam).\n<i>Masalan: 30</i>", kind="int"),
    Step("time", "Vaqti",
         "13/18. Tadbir <b>vaqtini</b> SS:DD formatida kiriting.\n<i>Masalan: 10:00</i>", kind="time"),
    Step("agenda", "Kun tartibi", "14/18. <b>KUN TARTIBI</b> — kim yozadi?", kind="block"),
    Step("heard", "Eshitildi", "15/18. <b>ESHITILDI</b> matni — kim yozadi?", kind="block"),
    Step("photos", "Rasmlar",
         "16/18. Tadbirdan <b>rasmlarni</b> yuboring (0–6 ta). Rasm yoki fayl ko'rinishida "
         "yuborishingiz mumkin.\nTugatgach «✅ Tayyor» tugmasini bosing.", kind="photos"),
    Step("decisions", "Qaror qilindi", "17/18. <b>QAROR QILINDI</b> — kim yozadi?", kind="block"),
    Step("secretary", "Yig'ilish kotibi",
         "18/18. <b>Yig'ilish kotibining</b> I.Familiyasini kiriting.\n<i>Masalan: D.Normatova</i>",
         profile="kotib_fio"),
    Step("signers", "Qo'shimcha imzolar",
         "Qo'shimcha imzo qo'yuvchilar (masalan, Yig'ilish raisi) kerakmi?", kind="signers"),
]

STEP_BY_KEY = {s.key: s for s in STEPS}
STEP_KEYS = [s.key for s in STEPS]

EVENT_TYPES = ["Tashrif", "Uchrashuv", "Davra suhbati", "Ma'naviy soat", "Seminar"]

BLOCK_NAMES = {"agenda": "KUN TARTIBI", "heard": "ESHITILDI", "decisions": "QAROR QILINDI"}

PROFILE_TITLES = {
    "universitet": "Universitet",
    "fakultet": "Fakultet",
    "tasdiqlovchi_lavozim": "Tasdiqlovchi lavozimi",
    "tasdiqlovchi_fio": "Tasdiqlovchi I.Familiyasi",
    "kotib_fio": "Yig'ilish kotibi",
    "shahar": "Shahar",
}

MAX_PHOTOS = 6


def next_step(key: str) -> str | None:
    i = STEP_KEYS.index(key)
    return STEP_KEYS[i + 1] if i + 1 < len(STEP_KEYS) else None


def prev_step(key: str) -> str | None:
    i = STEP_KEYS.index(key)
    return STEP_KEYS[i - 1] if i > 0 else None
