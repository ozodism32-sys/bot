"""Sozlamalar .env faylidan o'qiladi."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _int_list(value: str) -> list[int]:
    result = []
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            result.append(int(part))
    return result


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BASE_DIR / p


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: list[int] = field(default_factory=lambda: _int_list(os.getenv("ADMIN_IDS", "")))

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "claude-opus-5-5")
    ai_effort: str = os.getenv("AI_EFFORT", "medium")

    storage_dir: Path = _path(os.getenv("STORAGE_DIR", "storage"))
    db_path: Path = _path(os.getenv("DB_PATH", "data/bot.db"))

    soffice_path: str = os.getenv("SOFFICE_PATH", "soffice")
    pdf_concurrency: int = int(os.getenv("PDF_CONCURRENCY", "2"))
    pdf_timeout: int = int(os.getenv("PDF_TIMEOUT", "120"))

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
