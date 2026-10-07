"""docx_builder.py ni botsiz test qilish.

    python test_build.py            # faqat DOCX
    python test_build.py --pdf      # DOCX + PDF (LibreOffice kerak)

Natija: test_output/ papkasida.
"""
import asyncio
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from docx_builder import build_protocol
from utils import protocol_filename

OUT_DIR = Path(__file__).parent / "test_output"

SAMPLE_DATA = {
    "approver_position": "Iqtisodiyot fakulteti dekani",
    "approver_name": "A.Turakulov",
    "university": "Termiz davlat universiteti",
    "faculty": "Iqtisodiyot fakulteti",
    "event_name": "Arxeologiya muzeyi",
    "event_type": "Tashrif",
    "number": "12",
    "date": "18.09.2026",
    "city": "Termiz",
    "participants": "Fakultet tyutorlari, 1-bosqich talaba yoshlari",
    "venue": "Termiz arxeologiya muzeyi",
    "count": 30,
    "time": "10:00",
    "agenda": [
        "Talaba yoshlarni Surxon vohasining qadimiy tarixi va moddiy-madaniy merosi bilan tanishtirish.",
        "Yoshlarda milliy g'urur, vatanparvarlik va tarixiy xotirani yuksaltirish.",
        "Muzey eksponatlarini asrab-avaylash madaniyatini shakllantirish.",
    ],
    "heard": [
        "Tadbirda fakultet tyutorlari talaba yoshlarga Termiz arxeologiya muzeyining tashkil "
        "topish tarixi, unda saqlanayotgan noyob eksponatlar hamda Surxon vohasida olib borilgan "
        "arxeologik tadqiqotlar haqida batafsil ma'lumot berdilar.",
        "Muzey xodimlari tomonidan Fayoztepa, Qoratepa, Dalvarzintepa kabi qadimiy yodgorliklardan "
        "topilgan ashyolar namoyish etildi va ularning jahon sivilizatsiyasidagi o'rni haqida "
        "so'zlab berildi.",
        "Tadbir so'ngida talaba yoshlarning savollariga javob berildi, ular o'z taassurotlari "
        "bilan o'rtoqlashdilar.",
    ],
    "decisions": [
        "Talaba yoshlar uchun tarixiy-madaniy obidalarga sayohatlar muntazam tashkil etilsin.",
        "Yoshlarda milliy g'urur va vatanparvarlik tuyg'usini oshirishga qaratilgan tadbirlar davom ettirilsin.",
        "Muzey eksponatlariga ehtiyotkorona munosabatda bo'lish yuzasidan talabalar ogohlantirilsin.",
    ],
    "secretary": "D.Normatova",
    "signers": [{"position": "Yig'ilish raisi", "name": "B.Karimov"}],
}


def make_sample_images(n: int = 3) -> list[str]:
    img_dir = OUT_DIR / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    sizes = [(1600, 1200), (1200, 1600), (1920, 1080), (1000, 1000)]
    colors = [(70, 130, 180), (205, 133, 63), (60, 179, 113), (147, 112, 219)]
    paths = []
    for i in range(n):
        w, h = sizes[i % len(sizes)]
        im = Image.new("RGB", (w, h), colors[i % len(colors)])
        d = ImageDraw.Draw(im)
        d.rectangle([20, 20, w - 20, h - 20], outline=(255, 255, 255), width=12)
        d.text((w // 2 - 40, h // 2), f"Rasm {i + 1}", fill=(255, 255, 255))
        p = img_dir / f"sample_{i + 1}.jpg"
        im.save(p, "JPEG")
        paths.append(str(p))
    return paths


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    images = make_sample_images(3)
    docx_path = OUT_DIR / protocol_filename(SAMPLE_DATA, "docx")
    build_protocol(SAMPLE_DATA, images, str(docx_path))
    print(f"DOCX: {docx_path}")

    if "--pdf" in sys.argv:
        from pdf_converter import convert_to_pdf
        pdf_path = asyncio.run(convert_to_pdf(str(docx_path)))
        print(f"PDF:  {pdf_path}")


if __name__ == "__main__":
    main()
