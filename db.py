"""SQLite (aiosqlite) bilan ishlash."""
import json
from datetime import datetime

import aiosqlite

from config import settings

PROFILE_FIELDS = (
    "universitet", "fakultet", "tasdiqlovchi_lavozim",
    "tasdiqlovchi_fio", "kotib_fio", "shahar",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    universitet TEXT,
    fakultet TEXT,
    tasdiqlovchi_lavozim TEXT,
    tasdiqlovchi_fio TEXT,
    kotib_fio TEXT,
    shahar TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS protocols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    data TEXT NOT NULL,
    docx_path TEXT,
    pdf_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_protocols_user ON protocols(user_id, id DESC);
"""


def _connect():
    return aiosqlite.connect(settings.db_path)


async def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    async with _connect() as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def ensure_user(user_id: int) -> None:
    async with _connect() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
            (user_id, datetime.now().isoformat(timespec="seconds")),
        )
        await db.commit()


async def get_profile(user_id: int) -> dict:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
    return {k: row[k] for k in PROFILE_FIELDS} if row else {k: None for k in PROFILE_FIELDS}


async def update_profile(user_id: int, **fields) -> None:
    fields = {k: v for k, v in fields.items() if k in PROFILE_FIELDS and v}
    if not fields:
        return
    await ensure_user(user_id)
    cols = ", ".join(f"{k} = ?" for k in fields)
    async with _connect() as db:
        await db.execute(f"UPDATE users SET {cols} WHERE user_id = ?", (*fields.values(), user_id))
        await db.commit()


async def create_protocol(user_id: int, data: dict) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO protocols (user_id, created_at, data) VALUES (?, ?, ?)",
            (user_id, datetime.now().isoformat(timespec="seconds"),
             json.dumps(data, ensure_ascii=False)),
        )
        await db.commit()
        return cur.lastrowid


async def update_protocol(protocol_id: int, *, data: dict | None = None,
                          docx_path: str | None = None, pdf_path: str | None = None) -> None:
    sets, params = [], []
    if data is not None:
        sets.append("data = ?")
        params.append(json.dumps(data, ensure_ascii=False))
    if docx_path is not None:
        sets.append("docx_path = ?")
        params.append(docx_path)
    if pdf_path is not None:
        sets.append("pdf_path = ?")
        params.append(pdf_path)
    if not sets:
        return
    async with _connect() as db:
        await db.execute(f"UPDATE protocols SET {', '.join(sets)} WHERE id = ?", (*params, protocol_id))
        await db.commit()


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"], "user_id": row["user_id"], "created_at": row["created_at"],
        "data": json.loads(row["data"]), "docx_path": row["docx_path"], "pdf_path": row["pdf_path"],
    }


async def list_protocols(user_id: int, limit: int = 10) -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM protocols WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
        )
        rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_protocol(protocol_id: int, user_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM protocols WHERE id = ? AND user_id = ?", (protocol_id, user_id)
        )
        row = await cur.fetchone()
    return _row_to_dict(row) if row else None


async def stats() -> dict:
    async with _connect() as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        protocols = (await (await db.execute("SELECT COUNT(*) FROM protocols")).fetchone())[0]
        today = datetime.now().date().isoformat()
        today_cnt = (await (await db.execute(
            "SELECT COUNT(*) FROM protocols WHERE created_at >= ?", (today,)
        )).fetchone())[0]
    return {"users": users, "protocols": protocols, "today": today_cnt}
