# scheduler.py — Kunlik eslatmalar va haftalik hisobot
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from config import TELEGRAM_TOKEN, XODIMLAR, TADBIRKOR_ID
from db import eslatma_kerak_vazifalar, yuborildi_belgilash, haftalik_vazifalar


async def kunlik_eslatmalar(bot: Bot):
    """
    Har kuni ertalab 9:00 da ishlaydi.
    Ertaga deadline bo'lgan xodimlarga eslatma yuboradi.
    """
    vazifalar = eslatma_kerak_vazifalar()

    if not vazifalar:
        return

    for vazifa_id, xodim, vazifa, deadline in vazifalar:
        user_id = XODIMLAR.get(xodim)
        if not user_id:
            continue

        xabar = (
            f"⏰ *Eslatma!*\n\n"
            f"Salom, {xodim}!\n"
            f"Ertaga deadline:\n\n"
            f"📌 *{vazifa}*\n"
            f"📅 Muddat: `{deadline}`\n\n"
            f"Bajarildi? /bajarildi_{vazifa_id}"
        )
        try:
            await bot.send_message(
                chat_id=user_id,
                text=xabar,
                parse_mode="Markdown"
            )
            yuborildi_belgilash(vazifa_id)
        except Exception as e:
            print(f"Eslatma yuborishda xato ({xodim}): {e}")


async def haftalik_hisobot(bot: Bot):
    """
    Har dushanba 10:00 da tadbirkorga haftalik hisobot yuboradi.
    """
    vazifalar = haftalik_vazifalar()

    if not vazifalar:
        await bot.send_message(
            chat_id=TADBIRKOR_ID,
            text="📊 Bu hafta hech qanday vazifa qo'yilmagan."
        )
        return

    # Xodim bo'yicha guruhlash
    guruhlar = {}
    for xodim, vazifa, deadline, holat in vazifalar:
        guruhlar.setdefault(xodim, []).append((vazifa, deadline, holat))

    satırlar = ["📊 *Haftalik hisobot*\n"]
    for xodim, v_list in guruhlar.items():
        satırlar.append(f"\n👤 *{xodim}*")
        for vazifa, deadline, holat in v_list:
            emoji = "✅" if holat == "bajarildi" else "🔲"
            satırlar.append(f"  {emoji} {vazifa} — `{deadline}`")

    bajarildi = sum(1 for _, _, h in vazifalar if h == "bajarildi")
    jami = len(vazifalar)
    satırlar.append(f"\n📈 Jami: {bajarildi}/{jami} bajarildi")

    await bot.send_message(
        chat_id=TADBIRKOR_ID,
        text="\n".join(satırlar),
        parse_mode="Markdown"
    )


def schedulerni_boshlash(bot: Bot):
    """Barcha vazifalarni jadvalga qo'shish"""
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    # Har kuni 09:00 da eslatmalar
    scheduler.add_job(
        kunlik_eslatmalar,
        trigger="cron",
        hour=9, minute=0,
        args=[bot]
    )

    # Har dushanba 10:00 da hisobot
    scheduler.add_job(
        haftalik_hisobot,
        trigger="cron",
        day_of_week="mon",
        hour=10, minute=0,
        args=[bot]
    )

    scheduler.start()
    return scheduler
