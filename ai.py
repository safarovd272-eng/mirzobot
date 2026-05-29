# ai.py — Whisper (ovoz→matn) va Claude (tahlil) integratsiyasi
import json
import httpx
from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, XODIMLAR


# ──────────────────────────────────────────────
# 1. WHISPER — ovoz faylini o'zbek matnga aylantirish
# ──────────────────────────────────────────────
async def ovoz_dan_matn(fayl_yoli: str) -> str:
    """
    OGG/MP3 fayl → o'zbek matni
    OpenAI Whisper API ishlatiladi
    """
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    with open(fayl_yoli, "rb") as f:
        files = {
            "file": (fayl_yoli, f, "audio/ogg"),
            "model": (None, "whisper-1"),
            "language": (None, "uz"),        # o'zbek tili
            "response_format": (None, "text"),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, files=files)
            resp.raise_for_status()
            return resp.text.strip()


# ──────────────────────────────────────────────
# 2. CLAUDE — matndan vazifalarni ajratib olish
# ──────────────────────────────────────────────
TIZIM_XABARI = """Sen o'zbek tilida ishlaydigan aqlli kotibsan.
Tadbirkor uchrashuv yoki topshiriqlar haqida gapiradi.
Sening vazifang: gapdan kim uchun qanday vazifa va deadline bor ekanini aniqlab, 
faqat JSON formatida qaytarish.

Xodimlar ro'yxati: {xodimlar}

Qoidalar:
- Faqat JSON qaytaradi, boshqa hech narsa yozma
- Agar xodim nomi aniq aytilmasa, "Umumiy" deb yoz
- Deadline aniq aytilmasa, 3 kun keyingi sanani yoz (YYYY-MM-DD formatida)
- Bugungi sana: {bugun}

Qaytariladigan format:
{{
  "xulosa": "Uchrashuv haqida 1-2 gaplik xulosa",
  "vazifalar": [
    {{
      "xodim": "Xodim ismi",
      "vazifa": "Nima qilish kerak — aniq va qisqa",
      "deadline": "YYYY-MM-DD"
    }}
  ]
}}"""


async def matndan_vazifalar(matn: str) -> dict:
    """
    Uchrashuv matni → vazifalar dict
    Claude API ishlatiladi
    """
    from datetime import datetime

    bugun = datetime.now().strftime("%Y-%m-%d")
    xodimlar_list = ", ".join(XODIMLAR.keys())

    tizim = TIZIM_XABARI.format(xodimlar=xodimlar_list, bugun=bugun)

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": tizim,
        "messages": [
            {"role": "user", "content": matn}
        ]
    }

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()

    # JSON ni tozalab parse qilish
    javob = data["content"][0]["text"].strip()
    # Markdown kod blokini olib tashlash (```json ... ```)
    if javob.startswith("```"):
        javob = javob.split("```")[1]
        if javob.startswith("json"):
            javob = javob[4:]
    return json.loads(javob.strip())
