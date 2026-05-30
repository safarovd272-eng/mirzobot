import json
import httpx
from config import GROQ_API_KEY, XODIMLAR


async def ovoz_dan_matn(fayl_yoli: str) -> str:
    """Groq Whisper — ovozni matnga aylantirish"""
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    with open(fayl_yoli, "rb") as f:
        files = {
            "file": ("audio.ogg", f, "audio/ogg"),
            "model": (None, "whisper-large-v3"),
            "language": (None, "uz"),
            "response_format": (None, "text"),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, files=files)
            resp.raise_for_status()
            return resp.text.strip()


TIZIM_XABARI = """Sen o'zbek tilida ishlaydigan aqlli kotibsan.
Tadbirkor uchrashuv yoki topshiriqlar haqida gapiradi.
Sening vazifang: gapdan kim uchun qanday vazifa va deadline bor ekanini aniqlab,
FAQAT JSON formatida qaytarish. Boshqa hech narsa yozma.

Xodimlar: {xodimlar}
Bugun: {bugun}

Agar deadline aytilmasa, 3 kun keyingi sana.
Agar xodim aytilmasa, "Umumiy" yoz.

JSON format:
{{"xulosa":"...","vazifalar":[{{"xodim":"...","vazifa":"...","deadline":"YYYY-MM-DD"}}]}}"""


async def matndan_vazifalar(matn: str) -> dict:
    from datetime import datetime
    bugun = datetime.now().strftime("%Y-%m-%d")
    xodimlar_list = ", ".join(XODIMLAR.keys())

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": TIZIM_XABARI.format(xodimlar=xodimlar_list, bugun=bugun)
            },
            {
                "role": "user",
                "content": matn
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()

    javob = data["choices"][0]["message"]["content"].strip()
    if javob.startswith("```"):
        javob = javob.split("```")[1]
        if javob.startswith("json"):
            javob = javob[4:]
    return json.loads(javob.strip())
