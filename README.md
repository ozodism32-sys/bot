# Bayonnoma Telegram boti

Telegram bot savollar orqali ma'lumot yig'adi va rasmiy **BAYONNOMA** hujjatini
(Word va/yoki PDF) namunadagi formatda yaratadi. "Kun tartibi", "Eshitildi" va
"Qaror qilindi" matnlarini Claude AI yozib berishi mumkin.

## Imkoniyatlar

- 📝 18 qadamli savol-javob (aiogram 3 FSM). Har qadamda «⬅️ Orqaga» va «❌ Bekor qilish» bor.
- Avval saqlangan qiymatlar «✅ Avvalgisini ishlatish» tugmasi bilan taklif qilinadi.
- 🤖 AI matn yozadi: «✅ Qabul qilish / 🔄 Qayta yozish / ✍️ O'zim tahrirlayman».
  AI ishlamasa, xato xabari chiqadi va qo'lda yozish taklif qilinadi.
- 🖼 0–6 ta rasm (photo yoki fayl ko'rinishida). Hujjatda ikkitadan yonma-yon, balandligi bir xil.
- 📋 Oxirida xulosa: istalgan maydonni alohida tahrirlash mumkin.
- 📄 PDF / 📝 DOCX / 📦 ikkalasi. Fayl nomi: `Bayonnoma_Arxeologiya_muzeyi_18.09.2026.pdf`.
- 🔁 Avvalgi bayonnoma nusxasidan yangisini yaratish.
- 📂 Oxirgi 10 ta bayonnomani qayta yuklab olish.
- ⚙️ Doimiy ma'lumotlar (universitet, fakultet, tasdiqlovchi, kotib, shahar).
- 📊 Admin uchun `/stats`.

## Fayl tuzilishi

```
bot.py               — ishga tushirish nuqtasi
config.py            — .env sozlamalari
states.py            — FSM holatlari
steps.py             — qadamlar tartibi, savol matnlari
keyboards.py         — tugmalar
handlers/
  common.py          — /start, /cancel, /help, /stats, global xato ushlagich
  protocol.py        — yangi bayonnoma (FSM), AI, rasmlar, xulosa, format
  history.py         — mening bayonnomalarim, nusxa olish
  settings.py        — doimiy ma'lumotlar
  helpers.py         — xabarlarni bo'lish, xulosa matni
docx_builder.py      — build_protocol(data, images, out_path) — botsiz ishlaydi
pdf_converter.py     — DOCX → PDF (LibreOffice, asinxron)
ai_writer.py         — Claude API bilan matn yozish
protocol_service.py  — fayllarni yaratish va saqlash
db.py                — SQLite (aiosqlite)
utils.py             — sana (o'zbekcha oy nomlari), o‘/g‘ normalizatsiyasi, fayl nomi
test_build.py        — docx_builder ni namuna ma'lumotlar bilan test qilish
```

Fayllar `storage/{user_id}/{protocol_id}/` papkasida, baza `data/bot.db` da saqlanadi.

## O'rnatish (Ubuntu 22.04 / 24.04)

### 1. Tizim paketlari

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# LibreOffice (PDF uchun). Faqat writer yetarli:
sudo apt install -y --no-install-recommends libreoffice-writer libreoffice-core

# Shriftlar: Times New Roman (PDF hujjatda to'g'ri chiqishi uchun)
sudo apt install -y ttf-mscorefonts-installer fonts-liberation
sudo fc-cache -f
```

> `ttf-mscorefonts-installer` o'rnatishda litsenziyani qabul qilish so'raladi.
> U o'rnatilmasa, LibreOffice Times New Roman o'rniga metrik jihatdan bir xil
> **Liberation Serif** shriftidan foydalanadi (sahifalash o'zgarmaydi).

Tekshirish: `soffice --version`

### 2. Loyiha

```bash
git clone <repo-url> /opt/bayonnoma-bot
cd /opt/bayonnoma-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env        # BOT_TOKEN, ADMIN_IDS, ANTHROPIC_API_KEY ni yozing
```

`.env` dagi asosiy sozlamalar:

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | @BotFather bergan token |
| `ADMIN_IDS` | `/stats` ishlata oladigan Telegram ID lar (vergul bilan) |
| `ANTHROPIC_API_KEY` | Claude API kaliti (bo'sh bo'lsa AI o'chiq, faqat qo'lda yoziladi) |
| `AI_MODEL` | Standart: `claude-opus-5-5` |
| `AI_EFFORT` | `low` / `medium` / `high` — AI qanchalik chuqur o'ylashi |
| `SOFFICE_PATH` | LibreOffice buyrug'i (standart `soffice`) |
| `PDF_CONCURRENCY` | Bir vaqtda nechta PDF konvertatsiya (standart 2) |

> ⚠️ `.env` faylini hech qachon git'ga qo'shmang (u `.gitignore` da).
> Agar token biror joyda ochiq e'lon qilingan bo'lsa, @BotFather → `/revoke` orqali yangilang.

### 3. Test

```bash
python test_build.py          # test_output/ ichida DOCX
python test_build.py --pdf    # DOCX + PDF
```

### 4. Ishga tushirish

```bash
python bot.py
```

## systemd orqali doimiy ishlatish

Alohida foydalanuvchi yaratish (tavsiya etiladi):

```bash
sudo useradd -r -m -d /opt/bayonnoma-bot -s /usr/sbin/nologin botuser
sudo chown -R botuser:botuser /opt/bayonnoma-bot
```

`/etc/systemd/system/bayonnoma-bot.service`:

```ini
[Unit]
Description=Bayonnoma Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=botuser
Group=botuser
WorkingDirectory=/opt/bayonnoma-bot
ExecStart=/opt/bayonnoma-bot/.venv/bin/python bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
# LibreOffice vaqtinchalik profillari uchun
Environment=HOME=/opt/bayonnoma-bot

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bayonnoma-bot
sudo systemctl status bayonnoma-bot
journalctl -u bayonnoma-bot -f      # loglar
```

Loglar shuningdek `data/bot.log` faylida yoziladi (5 MB dan aylanadi).

## Eslatmalar

- FSM holati xotirada (`MemoryStorage`) saqlanadi: bot qayta ishga tushsa, chala qolgan
  bayonnoma yo'qoladi (saqlangan bayonnomalar va doimiy ma'lumotlar bazada qoladi).
  Ko'p foydalanuvchili muhitda `aiogram.fsm.storage.redis.RedisStorage` ga almashtirish mumkin.
- PDF konvertatsiya `asyncio` subprocess orqali, har biri alohida LibreOffice profilida va
  semafor bilan cheklangan holda ishlaydi — bot bir vaqtda bir nechta foydalanuvchiga xizmat qiladi.
- DOCX yaratish ham alohida thread'da (`asyncio.to_thread`) bajariladi.
- Hujjatda o' / g' harflari avtomatik `o‘ / g‘` ga, boshqa apostroflar `’` ga almashtiriladi.
- Kun tartibi va qarorlarning raqamlari kod tomonidan ketma-ket qo'yiladi (1, 2, 3, …).
