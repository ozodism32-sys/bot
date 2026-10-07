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
         "Tasdiqlovchining <b>lavozimini</b> kiriting.\n<i>Masalan: Iqtisodiyot fakulteti dekani</i>",
         profile="tasdiqlovchi_lavozim"),
    Step("approver_name", "Tasdiqlovchi I.Familiyasi",
         "Tasdiqlovchining <b>I.Familiyasini</b> kiriting.\n<i>Masalan: A.Turakulov</i>",
         profile="tasdiqlovchi_fio"),
    Step("university", "Universitet",
         "<b>Universitet</b> nomini kiriting.\n<i>Masalan: Termiz davlat universiteti</i>",
         profile="universitet"),
    Step("faculty", "Fakultet",
         "<b>Fakultet</b> nomini kiriting.\n<i>Masalan: Iqtisodiyot fakulteti</i>",
         profile="fakultet"),
    Step("event_name", "Tadbir nomi",
         "<b>Tadbir nomini</b> kiriting.\n<i>Masalan: Arxeologiya muzeyi</i>"),
    Step("event_type", "Tadbir turi", "<b>Tadbir turini</b> tanlang:", kind="event_type"),
    Step("number", "Bayonnoma raqami",
         "<b>Bayonnoma raqamini</b> kiriting yoki o'tkazib yuboring (hujjatda ____ qoladi).",
         kind="number"),
    Step("date", "Sana",
         "Tadbir <b>sanasini</b> KK.OO.YYYY formatida kiriting yoki «Bugun»ni bosing.\n"
         "<i>Masalan: 18.09.2026</i>", kind="date"),
    Step("city", "Shahar", "<b>Shahar</b> nomini kiriting.\n<i>Masalan: Termiz</i>",
         profile="shahar"),
    Step("participants", "Tadbir ishtirokchilari",
         "<b>Tadbir ishtirokchilarini</b> kiriting.\n"
         "<i>Masalan: Fakultet tyutorlari, 1-bosqich talaba yoshlari</i>"),
    Step("venue", "O'tkazish joyi",
         "Tadbir <b>o'tkazish joyini</b> kiriting.\n<i>Masalan: Termiz arxeologiya muzeyi</i>"),
    Step("count", "Ishtirokchilar soni",
         "<b>Ishtirokchilar sonini</b> kiriting (faqat raqam).\n<i>Masalan: 30</i>", kind="int"),
    Step("time", "Vaqti",
         "Tadbir <b>vaqtini</b> SS:DD formatida kiriting.\n<i>Masalan: 10:00</i>", kind="time"),
    Step("agenda", "Kun tartibi", "<b>KUN TARTIBI</b> — kim yozadi?", kind="block"),
    Step("heard", "Eshitildi", "<b>ESHITILDI</b> matni — kim yozadi?", kind="block"),
    Step("photos", "Rasmlar",
         "Tadbirdan <b>rasmlarni</b> yuboring (0–6 ta). Rasm yoki fayl ko'rinishida "
         "yuborishingiz mumkin.\nTugatgach «✅ Tayyor» tugmasini bosing.", kind="photos"),
    Step("decisions", "Qaror qilindi", "<b>QAROR QILINDI</b> — kim yozadi?", kind="block"),
    Step("secretary", "Yig'ilish kotibi",
         "<b>Yig'ilish kotibining</b> I.Familiyasini kiriting.\n<i>Masalan: D.Normatova</i>",
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


# Doimiy ma'lumotlar: faqat profilda bo'lmasa so'raladi, keyin eslab qolinadi
PROFILE_STEPS = ["approver_position", "approver_name", "university", "faculty", "city", "secretary"]
# Har safar so'raladigan qisqa savollar
EVENT_STEPS = ["event_name", "event_type", "date", "time", "venue", "count", "participants"]
# AI yozadigan matnlar (AI ishlamasa qo'lda so'raladi)
BLOCK_STEPS = ["agenda", "heard", "decisions"]

# Tugma bilan tez tanlanadigan standart qiymatlar
DEFAULTS = {"participants": "Fakultet tyutorlari, talaba yoshlari"}


def build_flow(missing_profile: list[str], ai_enabled: bool) -> list[str]:
    """Foydalanuvchiga beriladigan savollar ketma-ketligi."""
    flow = [k for k in PROFILE_STEPS if k in missing_profile] + EVENT_STEPS
    if not ai_enabled:
        flow += BLOCK_STEPS
    return flow + ["photos"]


def next_in(flow: list[str], key: str) -> str | None:
    if key not in flow:
        return None
    i = flow.index(key)
    return flow[i + 1] if i + 1 < len(flow) else None


def prev_in(flow: list[str], key: str) -> str | None:
    if key not in flow:
        return None
    i = flow.index(key)
    return flow[i - 1] if i > 0 else None
