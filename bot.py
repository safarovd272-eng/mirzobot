# bot.py — Mirzo AI Kotib — asosiy bot
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import TELEGRAM_TOKEN, XODIMLAR, TADBIRKOR_ID
from db import init_db, saqlash_uchrashuv, saqlash_vazifa, holat_yangilash
from ai import ovoz_dan_matn, matndan_vazifalar
from scheduler import schedulerni_boshlash

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# KOMANDALAR
# ──────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Bot boshlanishi"""
    xabar = (
        "👋 Salom! Men *Mirzo* — AI kotibingizman.\n\n"
        "Menga qila olasiz:\n"
        "🎙 Ovozli xabar → Uchrashuv yozing\n"
        "✍️ Matn → Vazifa qo'ying\n"
        "📊 /hisobot → Haftalik holat\n"
        "❓ /yordam → Barcha komandalar"
    )
    await update.message.reply_text(xabar, parse_mode="Markdown")


async def yordam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Yordam"""
    xabar = (
        "📖 *Mirzo Bot — Komandalar*\n\n"
        "🎙 *Ovozli xabar* — uchrashuv yoki topshiriq ayting\n"
        "✍️ *Matn* — yozib yuboring\n"
        "📊 /hisobot — haftalik hisobot\n"
        "👥 /xodimlar — xodimlar ro'yxati\n"
        "ℹ️ /yordam — bu sahifa\n\n"
        "_Misol: 'Jasurga ertaga soat 5 gacha taqdimot tayyor qilsin'_"
    )
    await update.message.reply_text(xabar, parse_mode="Markdown")


async def xodimlar_royxati(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Xodimlar ro'yxatini ko'rsatish"""
    lines = ["👥 *Xodimlar ro'yxati:*\n"]
    for ism in XODIMLAR:
        lines.append(f"• {ism}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def hisobot_komanda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Haftalik hisobot so'rash"""
    from scheduler import haftalik_hisobot
    await haftalik_hisobot(ctx.bot)


# ──────────────────────────────────────────────
# MATN XABARI — asosiy mantiq
# ──────────────────────────────────────────────

async def matn_qabul(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Matn xabarini qayta ishlash"""
    matn = update.message.text

    # /bajarildi_ID komandasi
    if matn.startswith("/bajarildi_"):
        try:
            vazifa_id = int(matn.split("_")[1])
            holat_yangilash(vazifa_id, "bajarildi")
            await update.message.reply_text("✅ Vazifa bajarildi deb belgilandi!")
        except Exception:
            await update.message.reply_text("❌ Xato vazifa ID.")
        return

    await update.message.reply_text("⏳ Tahlil qilinmoqda...")
    await vazifalarni_qayta_ishlash(update, ctx, matn)


# ──────────────────────────────────────────────
# OVOZLI XABAR
# ──────────────────────────────────────────────

async def ovoz_qabul(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Ovozli xabarni qayta ishlash"""
    xabar = await update.message.reply_text("🎙 Ovoz qabul qilindi. Transkripsiya qilinmoqda...")

    # Ovoz faylini yuklab olish
    voice = update.message.voice
    fayl = await ctx.bot.get_file(voice.file_id)
    fayl_yoli = f"/tmp/{voice.file_id}.ogg"
    await fayl.download_to_drive(fayl_yoli)

    try:
        # Whisper bilan matnга aylantirish
        matn = await ovoz_dan_matn(fayl_yoli)
        await xabar.edit_text(f"📝 *Tanilgan matn:*\n_{matn}_\n\n⏳ Vazifalar aniqlanmoqda...",
                              parse_mode="Markdown")
        await vazifalarni_qayta_ishlash(update, ctx, matn)

    except Exception as e:
        logger.error(f"Ovoz xatosi: {e}")
        await xabar.edit_text("❌ Ovozni qayta ishlashda xato. Qayta urinib ko'ring.")
    finally:
        if os.path.exists(fayl_yoli):
            os.remove(fayl_yoli)


# ──────────────────────────────────────────────
# ASOSIY MANTIQ — vazifalarni ajratish va yuborish
# ──────────────────────────────────────────────

async def vazifalarni_qayta_ishlash(update: Update, ctx: ContextTypes.DEFAULT_TYPE, matn: str):
    """Claude bilan tahlil qilish va xodimlarga yuborish"""
    try:
        # Claude tahlili
        natija = await matndan_vazifalar(matn)
        xulosa = natija.get("xulosa", "Uchrashuv qayd etildi")
        vazifalar = natija.get("vazifalar", [])

        if not vazifalar:
            await update.message.reply_text(
                f"📋 *Xulosa:* {xulosa}\n\n"
                "ℹ️ Aniq vazifa topilmadi. Iltimos, kimga nima qilish kerakligini ayting.",
                parse_mode="Markdown"
            )
            return

        # Bazaga saqlash
        uchrashuv_id = saqlash_uchrashuv(matn)

        # Tadbirkorga tasdiq so'rash
        vazifalar_matni = [f"📋 *Xulosa:* {xulosa}\n\n*Aniqlangan vazifalar:*"]
        for i, v in enumerate(vazifalar, 1):
            vazifalar_matni.append(
                f"\n{i}. 👤 *{v['xodim']}*\n"
                f"   📌 {v['vazifa']}\n"
                f"   📅 Deadline: `{v['deadline']}`"
            )
        vazifalar_matni.append("\n\nYuborilsinmi?")

        # Kontekstga saqlash
        ctx.user_data["kutilayotgan_vazifalar"] = vazifalar
        ctx.user_data["uchrashuv_id"] = uchrashuv_id

        tugmalar = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Ha, yubor", callback_data="tasdiqlash"),
                InlineKeyboardButton("❌ Bekor qil", callback_data="bekor"),
            ]
        ])

        await update.message.reply_text(
            "\n".join(vazifalar_matni),
            parse_mode="Markdown",
            reply_markup=tugmalar
        )

    except Exception as e:
        logger.error(f"Tahlil xatosi: {e}")
        await update.message.reply_text("❌ Tahlilda xato yuz berdi. Qayta urinib ko'ring.")


# ──────────────────────────────────────────────
# TUGMA BOSILGANDA
# ──────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Inline tugmalar uchun handler"""
    query = update.callback_query
    await query.answer()

    if query.data == "bekor":
        await query.edit_message_text("❌ Bekor qilindi.")
        ctx.user_data.clear()
        return

    if query.data == "tasdiqlash":
        vazifalar = ctx.user_data.get("kutilayotgan_vazifalar", [])
        uchrashuv_id = ctx.user_data.get("uchrashuv_id")

        if not vazifalar:
            await query.edit_message_text("❌ Vazifalar topilmadi.")
            return

        muvaffaqiyat = []
        xato = []

        for v in vazifalar:
            xodim = v["xodim"]
            vazifa_matni = v["vazifa"]
            deadline = v["deadline"]

            # Bazaga saqlash
            saqlash_vazifa(uchrashuv_id, xodim, vazifa_matni, deadline)

            # Xodimga yuborish
            user_id = XODIMLAR.get(xodim)
            if user_id:
                try:
                    xodim_xabari = (
                        f"📬 *Yangi vazifa!*\n\n"
                        f"Salom, {xodim}!\n\n"
                        f"📌 *Vazifa:* {vazifa_matni}\n"
                        f"📅 *Deadline:* `{deadline}`\n\n"
                        f"Bajargandan so'ng xabar bering."
                    )
                    await ctx.bot.send_message(
                        chat_id=user_id,
                        text=xodim_xabari,
                        parse_mode="Markdown"
                    )
                    muvaffaqiyat.append(xodim)
                except Exception as e:
                    logger.error(f"{xodim} ga yuborishda xato: {e}")
                    xato.append(xodim)
            else:
                xato.append(f"{xodim} (ID topilmadi)")

        # Natija
        natija_satırlar = ["✅ *Vazifalar yuborildi!*\n"]
        if muvaffaqiyat:
            natija_satırlar.append("📨 Yuborildi: " + ", ".join(muvaffaqiyat))
        if xato:
            natija_satırlar.append("⚠️ Xato: " + ", ".join(xato))

        await query.edit_message_text("\n".join(natija_satırlar), parse_mode="Markdown")
        ctx.user_data.clear()


# ──────────────────────────────────────────────
# BOTNI ISHGA TUSHIRISH
# ──────────────────────────────────────────────

def main():
    init_db()
    print("✅ Ma'lumotlar bazasi tayyor")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Komandalar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yordam", yordam))
    app.add_handler(CommandHandler("xodimlar", xodimlar_royxati))
    app.add_handler(CommandHandler("hisobot", hisobot_komanda))

    # Xabarlar
    app.add_handler(MessageHandler(filters.VOICE, ovoz_qabul))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, matn_qabul))

    # Tugmalar
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Scheduler
    schedulerni_boshlash(app.bot)
    print("⏰ Eslatmalar jadvali yoqildi")

    print("🤖 Mirzo Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
