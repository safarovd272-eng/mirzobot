import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]

XODIMLAR = {
    "Diyor":    int(os.environ.get("XODIM_DIYOR",    "0")),
    "Diyorjon": int(os.environ.get("XODIM_DIYORJON", "0")),
}

TADBIRKOR_ID = int(os.environ["TADBIRKOR_ID"])

DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_FILE = os.path.join(DATA_DIR, "mirzo.db")
