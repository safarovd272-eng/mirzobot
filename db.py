# db.py — Ma'lumotlar bazasi
import sqlite3
from config import DB_FILE
from datetime import datetime


def init_db():
    """Jadvallarni yaratish"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Uchrashuvlar jadvali
    c.execute("""
        CREATE TABLE IF NOT EXISTS uchrashuvlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sana TEXT,
            matn TEXT,
            yaratildi TEXT
        )
    """)

    # Vazifalar jadvali
    c.execute("""
        CREATE TABLE IF NOT EXISTS vazifalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uchrashuv_id INTEGER,
            xodim TEXT,
            vazifa TEXT,
            deadline TEXT,
            holat TEXT DEFAULT 'kutilmoqda',
            yuborildi INTEGER DEFAULT 0,
            yaratildi TEXT
        )
    """)

    conn.commit()
    conn.close()


def saqlash_uchrashuv(matn: str) -> int:
    """Uchrashuv matnini saqlash, ID qaytaradi"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO uchrashuvlar (sana, matn, yaratildi) VALUES (?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), matn, datetime.now().isoformat())
    )
    uchrashuv_id = c.lastrowid
    conn.commit()
    conn.close()
    return uchrashuv_id


def saqlash_vazifa(uchrashuv_id: int, xodim: str, vazifa: str, deadline: str):
    """Vazifani bazaga saqlash"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """INSERT INTO vazifalar 
           (uchrashuv_id, xodim, vazifa, deadline, yaratildi) 
           VALUES (?, ?, ?, ?, ?)""",
        (uchrashuv_id, xodim, vazifa, deadline, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def holat_yangilash(vazifa_id: int, holat: str):
    """Vazifa holatini yangilash"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE vazifalar SET holat=? WHERE id=?", (holat, vazifa_id))
    conn.commit()
    conn.close()


def eslatma_kerak_vazifalar() -> list:
    """Ertaga deadline bo'lgan, eslatma yuborilmagan vazifalar"""
    from datetime import timedelta
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    ertaga = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    c.execute("""
        SELECT id, xodim, vazifa, deadline 
        FROM vazifalar 
        WHERE deadline=? AND yuborildi=0 AND holat='kutilmoqda'
    """, (ertaga,))
    rows = c.fetchall()
    conn.close()
    return rows


def yuborildi_belgilash(vazifa_id: int):
    """Eslatma yuborildi deb belgilash"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE vazifalar SET yuborildi=1 WHERE id=?", (vazifa_id,))
    conn.commit()
    conn.close()


def haftalik_vazifalar() -> list:
    """Bu hafta yaratilgan barcha vazifalar"""
    from datetime import timedelta
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    bir_hafta_oldin = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("""
        SELECT xodim, vazifa, deadline, holat 
        FROM vazifalar 
        WHERE yaratildi >= ?
        ORDER BY xodim, deadline
    """, (bir_hafta_oldin,))
    rows = c.fetchall()
    conn.close()
    return rows
