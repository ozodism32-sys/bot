"""Claude API orqali "Kun tartibi", "Eshitildi" va "Qaror qilindi" matnlarini yozish."""
import logging

import anthropic

from config import settings
from utils import split_lines, split_paragraphs

log = logging.getLogger(__name__)


class AIWriterError(Exception):
    """AI matn yoza olmaganda (foydalanuvchiga tushunarli xabar bilan)."""


SYSTEM_PROMPT = """Sen O'zbekiston oliy ta'lim muassasalari uchun rasmiy hujjatlar (bayonnomalar) yozuvchi tajribali kotibsan.
Faqat o'zbek tilida, lotin alifbosida yoz. O' va G' harflarini apostrof bilan yoz (o', g').
Uslub: rasmiy, idoraviy, oliygoh hujjatlari uslubi. Ortiqcha bezaksiz, aniq va lo'nda.
Hech qanday sarlavha, izoh, markdown belgisi (**, #, -) yoki kirish so'zlari qo'shma — faqat so'ralgan matnni qaytar.

Namuna — KUN TARTIBI:
Talaba yoshlarni Surxon vohasining qadimiy tarixi va moddiy-madaniy merosi bilan tanishtirish.
Yoshlarda milliy g'urur, vatanparvarlik va tarixiy xotirani yuksaltirish.

Namuna — ESHITILDI:
Tadbirda fakultet tyutorlari talaba yoshlarga Termiz arxeologiya muzeyining tashkil topish tarixi, unda saqlanayotgan noyob eksponatlar hamda Surxon vohasida olib borilgan arxeologik tadqiqotlar haqida batafsil ma'lumot berdilar. Ular yoshlarni ajdodlarimiz qoldirgan boy merosni asrab-avaylashga, uni chuqur o'rganishga chaqirdilar.

Muzey xodimlari tomonidan Fayoztepa, Qoratepa, Dalvarzintepa kabi qadimiy yodgorliklardan topilgan ashyolar namoyish etildi va ularning jahon sivilizatsiyasidagi o'rni haqida so'zlab berildi.

Tadbir so'ngida talaba yoshlarning savollariga javob berildi, ular o'z taassurotlari bilan o'rtoqlashdilar.

Namuna — QAROR QILINDI:
Talaba yoshlar uchun tarixiy-madaniy obidalarga sayohatlar muntazam ravishda tashkil etilsin.
Yoshlarda milliy g'urur va vatanparvarlik tuyg'usini oshirishga qaratilgan tadbirlar davom ettirilsin.
Muzey eksponatlariga ehtiyotkorona munosabatda bo'lish yuzasidan talabalar ogohlantirilsin.
"""


def _context(data: dict, hint: str | None = None) -> str:
    lines = [
        f"Oliygoh: {data.get('university', '')}",
        f"Fakultet: {data.get('faculty', '')}",
        f"Tadbir nomi: {data.get('event_name', '')}",
        f"Tadbir turi: {data.get('event_type', '')}",
        f"Sana: {data.get('date', '')}, soat {data.get('time', '')}",
        f"Shahar: {data.get('city', '')}",
        f"O'tkazish joyi: {data.get('venue', '')}",
        f"Ishtirokchilar: {data.get('participants', '')}",
        f"Ishtirokchilar soni: {data.get('count', '')} nafar",
    ]
    if data.get("agenda"):
        lines.append("Kun tartibi:\n" + "\n".join(
            f"{i}. {a}" for i, a in enumerate(data["agenda"], 1)))
    if data.get("heard"):
        lines.append("Eshitildi:\n" + "\n\n".join(data["heard"]))
    if hint:
        lines.append(f"Foydalanuvchi izohi (tadbirda nimalar bo'ldi): {hint}")
    return "\n".join(lines)


_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=120)
    return _client


async def _ask(prompt: str) -> str:
    if not settings.ai_enabled:
        raise AIWriterError("AI sozlanmagan (ANTHROPIC_API_KEY yo'q).")
    try:
        response = await _get_client().beta.messages.create(
            model=settings.ai_model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": settings.ai_effort},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        log.error("Anthropic kalit xato: %s", e)
        raise AIWriterError("AI kaliti noto'g'ri sozlangan.") from e
    except anthropic.RateLimitError as e:
        log.warning("Anthropic rate limit: %s", e)
        raise AIWriterError("AI hozir band. Birozdan keyin qayta urinib ko'ring.") from e
    except anthropic.APIStatusError as e:
        log.error("Anthropic API xatosi %s: %s", e.status_code, e.message)
        raise AIWriterError("AI xizmatida xatolik yuz berdi.") from e
    except anthropic.APIConnectionError as e:
        log.error("Anthropic bilan aloqa yo'q: %s", e)
        raise AIWriterError("AI xizmatiga ulanib bo'lmadi.") from e

    if response.stop_reason == "refusal":
        log.warning("AI rad etdi: %s", response.stop_details)
        raise AIWriterError("AI bu so'rovga javob bermadi.")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise AIWriterError("AI bo'sh javob qaytardi.")
    return text.replace("**", "")


async def generate_agenda(data: dict) -> list[str]:
    prompt = (
        f"{_context({**data, 'agenda': None, 'heard': None})}\n\n"
        "Ushbu tadbir bayonnomasi uchun KUN TARTIBI bandlarini yoz: 2–4 ta band. "
        "Har bir band alohida qatorda, raqamsiz, nuqta bilan tugasin."
    )
    items = split_lines(await _ask(prompt))
    if not items:
        raise AIWriterError("AI kun tartibini yoza olmadi.")
    return items


async def generate_heard(data: dict, hint: str | None = None) -> list[str]:
    prompt = (
        f"{_context({**data, 'heard': None}, hint)}\n\n"
        "Ushbu tadbir bayonnomasi uchun ESHITILDI bo'limi matnini yoz: 2–4 xatboshi, "
        "har biri 2–4 gapdan iborat. Xatboshilar orasida bitta bo'sh qator qoldir. "
        "Kun tartibidagi barcha masalalar yoritilsin. O'tgan zamonda, uchinchi shaxsda yoz."
    )
    paragraphs = split_paragraphs(await _ask(prompt))
    if not paragraphs:
        raise AIWriterError("AI matn yoza olmadi.")
    return paragraphs


async def generate_decisions(data: dict) -> list[str]:
    n = len(data.get("agenda") or []) or 3
    prompt = (
        f"{_context(data)}\n\n"
        f"Ushbu tadbir bayonnomasi uchun QAROR QILINDI bandlarini yoz: {n} ta band, "
        "kun tartibining har bir bandiga mos tartibda bittadan qaror. "
        "Har bir band buyruq maylida tugasin (masalan: \"...tashkil etilsin\", "
        "\"...ta'minlansin\", \"...ogohlantirilsin\"). Har bir band alohida qatorda, raqamsiz."
    )
    items = split_lines(await _ask(prompt))
    if not items:
        raise AIWriterError("AI qarorlarni yoza olmadi.")
    return items
