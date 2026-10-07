"""Bayonnoma fayllarini (DOCX/PDF) yaratish va saqlash."""
import asyncio
import logging
import shutil
from pathlib import Path

import db
from config import settings
from docx_builder import build_protocol
from pdf_converter import convert_to_pdf
from steps import STEP_KEYS
from utils import protocol_filename

log = logging.getLogger(__name__)

DATA_KEYS = set(STEP_KEYS) | {"heard_hint"}


def clean_data(data: dict) -> dict:
    """FSM ma'lumotlaridan faqat hujjatga tegishli maydonlarni ajratadi."""
    return {k: v for k, v in data.items() if k in DATA_KEYS}


def protocol_dir(user_id: int, protocol_id: int) -> Path:
    return settings.storage_dir / str(user_id) / str(protocol_id)


def draft_dir(user_id: int, draft_id: str) -> Path:
    return settings.storage_dir / str(user_id) / "drafts" / draft_id


def _copy_images(images: list[str], dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    result = []
    for i, src in enumerate(images, 1):
        src_path = Path(src)
        if not src_path.exists():
            log.warning("Rasm topilmadi: %s", src)
            continue
        target = dest / f"{i}{src_path.suffix.lower() or '.jpg'}"
        if src_path.resolve() != target.resolve():
            shutil.copyfile(src_path, target)
        result.append(str(target))
    return result


async def create_and_build(user_id: int, data: dict, want_pdf: bool) -> dict:
    """Yangi bayonnoma yozuvini yaratadi, DOCX (va kerak bo'lsa PDF) quradi."""
    data = clean_data(data)
    protocol_id = await db.create_protocol(user_id, data)
    pdir = protocol_dir(user_id, protocol_id)
    data["photos"] = await asyncio.to_thread(_copy_images, data.get("photos") or [], pdir / "images")
    await db.update_protocol(protocol_id, data=data)
    docx_path, pdf_path = await build_files(protocol_id, user_id, data, want_pdf)
    return {"id": protocol_id, "data": data, "docx_path": docx_path, "pdf_path": pdf_path}


async def build_files(protocol_id: int, user_id: int, data: dict, want_pdf: bool,
                      existing_docx: str | None = None) -> tuple[str, str | None]:
    pdir = protocol_dir(user_id, protocol_id)
    docx_path = existing_docx
    if not docx_path or not Path(docx_path).exists():
        docx_path = str(pdir / protocol_filename(data, "docx"))
        # python-docx sinxron — alohida thread'da, bot qotmasligi uchun
        await asyncio.to_thread(build_protocol, data, data.get("photos") or [], docx_path)
        await db.update_protocol(protocol_id, docx_path=docx_path)
    pdf_path = None
    if want_pdf:
        pdf_path = await convert_to_pdf(docx_path, str(pdir / protocol_filename(data, "pdf")))
        await db.update_protocol(protocol_id, pdf_path=pdf_path)
    return docx_path, pdf_path


async def ensure_files(protocol: dict, fmt: str) -> tuple[str | None, str | None]:
    """Tarixdan yuklab olish: yo'q fayllarni qayta yaratadi."""
    want_pdf = fmt in ("pdf", "both")
    pdf = protocol.get("pdf_path")
    if want_pdf and pdf and Path(pdf).exists() and fmt == "pdf":
        return None, pdf
    docx, new_pdf = await build_files(
        protocol["id"], protocol["user_id"], protocol["data"],
        want_pdf=want_pdf and not (pdf and Path(pdf).exists()),
        existing_docx=protocol.get("docx_path"),
    )
    pdf = new_pdf or (pdf if want_pdf else None)
    return (docx if fmt in ("docx", "both") else None), pdf
