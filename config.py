import os
from dotenv import load_dotenv

load_dotenv()

# Web
APP_URL = os.getenv("APP_URL", "").rstrip("/")
WEBHOOK_ENDPOINT = os.getenv("WEBHOOK_ENDPOINT", "/drive/notifications")
PORT = int(os.getenv("PORT", "8080"))

# Google
SCOPES = [os.getenv("SCOPES", "https://www.googleapis.com/auth/drive")]
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")           # watched folder (incoming)
DRIVE_PARENT_ID = os.getenv("DRIVE_PARENT_ID", "")           # parent where label folders live

# Files
WATCH_ID_FILE = os.getenv("WATCH_ID_FILE", "watch_channel.json")
TOKEN_FILE = os.getenv("TOKEN_FILE", "token.json")
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", "client_secret.json")
START_TOKEN_FILE = os.getenv("START_TOKEN_FILE", "start_page_token.txt")
FOLDER_CATALOG_CSV = os.getenv("FOLDER_CATALOG_CSV", "folders.csv")

# Router
CONF_THRESHOLD = float(os.getenv("ROUTER_CONF_THRESHOLD", "0.55"))

# Misc
FOLDER_MIME = "application/vnd.google-apps.folder"

def require_env():
    if not APP_URL:
        raise RuntimeError("Set APP_URL in .env (your public HTTPS base URL).")
    if not DRIVE_FOLDER_ID:
        raise RuntimeError("Set DRIVE_FOLDER_ID (the folder to watch).")
    if not DRIVE_PARENT_ID:
        raise RuntimeError("Set DRIVE_PARENT_ID (where label folders should be created).")
