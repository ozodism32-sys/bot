"""DOCX -> PDF konvertatsiya (LibreOffice headless, asinxron)."""
import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from config import settings

log = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None


class PdfConversionError(Exception):
    pass


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(max(1, settings.pdf_concurrency))
    return _semaphore


async def convert_to_pdf(docx_path: str, pdf_path: str | None = None) -> str:
    """DOCX faylni PDF ga o'giradi. Bot event-loop'ini bloklamaydi.

    Har bir konvertatsiya alohida LibreOffice profilida ishlaydi, shuning uchun
    bir nechta jarayon parallel ishlaganda bir-biriga xalaqit bermaydi.
    """
    src = Path(docx_path).resolve()
    dst = Path(pdf_path).resolve() if pdf_path else src.with_suffix(".pdf")

    async with _get_semaphore():
        with tempfile.TemporaryDirectory(prefix="lo_") as tmp:
            tmp_path = Path(tmp)
            profile = tmp_path / "profile"
            out_dir = tmp_path / "out"
            out_dir.mkdir()
            cmd = [
                settings.soffice_path,
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless", "--norestore", "--nolockcheck",
                "--convert-to", "pdf", "--outdir", str(out_dir), str(src),
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as e:
                raise PdfConversionError(
                    f"LibreOffice topilmadi ({settings.soffice_path}). README'ga qarang."
                ) from e
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=settings.pdf_timeout
                )
            except asyncio.TimeoutError as e:
                proc.kill()
                await proc.wait()
                raise PdfConversionError("PDF konvertatsiya vaqti tugadi") from e

            produced = out_dir / (src.stem + ".pdf")
            if proc.returncode != 0 or not produced.exists():
                log.error("soffice xatosi (%s): %s %s", proc.returncode,
                          stdout.decode(errors="ignore"), stderr.decode(errors="ignore"))
                raise PdfConversionError("LibreOffice PDF yarata olmadi")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(produced), dst)
    log.info("PDF yaratildi: %s", dst)
    return str(dst)
