from flask import Flask
from config import APP_URL, PORT, require_env
from services.notifications import register_routes

from services.drive_client import get_drive
from services.labels import hydrate_labels

app = Flask(__name__)
register_routes(app)

if __name__ == "__main__":
    print(APP_URL)
    require_env()

    try:
        drive = get_drive()
        hydrate_labels(drive)
    except Exception as e:
        print(f"[BOOT] Label preload failed: {e}")

    app.run(host="0.0.0.0", port=PORT)
