"""Umumiy yordamchi funksiyalar: sana, vaqt, matn normalizatsiyasi, fayl nomi."""
import re
from datetime import date, datetime

UZ_MONTHS = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr",
]

# O‘ va G‘ uchun belgi, boshqa joylarda tutuq belgisi (ta’lim)
OKINA = "‘"   # ‘
TUTUQ = "’"   # ’
_APOSTROPHES = "'`‘’ʻʼ´"


def normalize_uz(text: str) -> str:
    """o', g' -> o‘, g‘ ; boshqa apostroflar -> ’ (Times New Roman'da to'g'ri chiqadi)."""
    if not text:
        return text
    text = re.sub(rf"([oOgG])[{_APOSTROPHES}]", rf"\1{OKINA}", text)
    text = re.sub(rf"(?<=\w)(?<![oOgG])[{_APOSTROPHES}](?=\w)", TUTUQ, text)
    return text


def parse_date(text: str) -> date | None:
    text = text.strip().replace("/", ".").replace("-", ".")
    try:
        return datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        return None


def date_to_words(value: str) -> str:
    """'18.09.2026' -> '2026-yil 18-sentyabr'."""
    d = parse_date(value)
    if not d:
        return value
    return f"{d.year}-yil {d.day}-{UZ_MONTHS[d.month - 1]}"


def parse_time(text: str) -> str | None:
    m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*", text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return f"{h:02d}:{mi:02d}"
    return None


def faculty_locative(faculty: str) -> str:
    """'Iqtisodiyot fakulteti' -> 'Iqtisodiyot fakultetida'."""
    f = faculty.strip()
    low = f.lower()
    if low.endswith("fakulteti"):
        return f + "da"
    if low.endswith("fakultet"):
        return f + "ida"
    return f


def dative_suffix(word: str) -> str:
    """O'zbek tilida jo'nalish kelishigi qo'shimchasi: -ga / -ka / -qa."""
    last = word.strip().strip("\"“”«»").lower()[-1:] if word.strip() else ""
    if last == "k":
        return "ka"
    if last == "q":
        return "qa"
    return "ga"


_TRANSLIT = {
    "ʻ": "", "ʼ": "", "‘": "", "’": "", "'": "", "`": "",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}


def safe_filename(text: str, max_len: int = 60) -> str:
    out = []
    for ch in text:
        low = ch.lower()
        if low in _TRANSLIT:
            rep = _TRANSLIT[low]
            out.append(rep.capitalize() if ch != low and rep else rep)
        else:
            out.append(ch)
    s = "".join(out)
    s = re.sub(r"[^A-Za-z0-9.]+", "_", s).strip("_.")
    return s[:max_len].rstrip("_") or "bayonnoma"


def protocol_filename(data: dict, ext: str) -> str:
    name = safe_filename(data.get("event_name", "tadbir"))
    dt = safe_filename(data.get("date", ""))
    return f"Bayonnoma_{name}_{dt}.{ext}"


def split_lines(text: str) -> list[str]:
    """Har bir qatordan band ajratadi, boshidagi raqam/belgilarni olib tashlaydi."""
    items = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(\d+\s*[.)\-]|[-•*–])\s*", "", line).strip()
        if line:
            items.append(line)
    return items


def split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in text.strip().splitlines() if p.strip()]
    return parts
