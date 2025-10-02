import uuid
from datetime import datetime, timezone
from flask import request, make_response
from config import (
    APP_URL, WEBHOOK_ENDPOINT, FOLDER_MIME,
    DRIVE_FOLDER_ID, FOLDER_CATALOG_CSV, DRIVE_PARENT_ID
)
from state import LABEL_TO_ID, LABEL_DESC, ALLOWED, LABEL_FOLDER_IDS
from .drive_client import (
    get_drive, read_start_page_token, write_start_page_token,
    save_watch_info, load_watch_info
)
from .processing import process_file
from .folder_catalog import ensure_folders_from_csv
from .labels import hydrate_labels

def register_routes(app):
    @app.route("/drive/start-watch", methods=["POST"])
    def start_watch():
        drive = get_drive()
        hydrate_labels(drive)
        # Ensure label folders exist & cache their IDs
        global LABEL_TO_ID, LABEL_DESC, ALLOWED, LABEL_FOLDER_IDS
        label_to_id, label_desc, allowed = ensure_folders_from_csv(drive, FOLDER_CATALOG_CSV, DRIVE_PARENT_ID)
        LABEL_TO_ID.clear(); LABEL_TO_ID.update(label_to_id)
        LABEL_DESC.clear(); LABEL_DESC.update(label_desc)
        ALLOWED.clear(); ALLOWED.extend(allowed)
        LABEL_FOLDER_IDS.clear(); LABEL_FOLDER_IDS.update(LABEL_TO_ID.values())

        channel_id = str(uuid.uuid4())
        address = f"{APP_URL}{WEBHOOK_ENDPOINT}"
        body = {"id": channel_id, "type": "web_hook", "address": address}
        resp = drive.changes().watch(
            body=body,
            pageToken=read_start_page_token(drive),
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()

        info = {
            "id": resp["id"],
            "resourceId": resp["resourceId"],
            "expiration": resp.get("expiration"),
            "address": address,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        save_watch_info(info)
        return {"status": "watching", "channel": info}, 200

    @app.route("/drive/stop-watch", methods=["POST"])
    def stop_watch():
        info = load_watch_info()
        if not info:
            return {"status": "no-active-channel"}, 200
        drive = get_drive()
        drive.channels().stop(body={"id": info["id"], "resourceId": info["resourceId"]}).execute()
        save_watch_info({})
        return {"status": "stopped"}, 200

    @app.route(WEBHOOK_ENDPOINT, methods=["POST"])
    def drive_notifications():
        if not ALLOWED or not LABEL_TO_ID:
            hydrate_labels(drive)
        try:
            info = load_watch_info()
            if not info:
                return "No channel", 200
            if request.headers.get("X-Goog-Channel-ID") != info.get("id"):
                return "Mismatched channel", 200
            if request.headers.get("X-Goog-Resource-ID") != info.get("resourceId"):
                return "Mismatched resource", 200

            drive = get_drive()
        except Exception as e:
            print(f"[AUTH] Drive not ready ({e}). Ack to prevent retries.")
            return "OK", 200

        page_token = read_start_page_token(drive)
        while page_token:
            resp = drive.changes().list(
                pageToken=page_token,
                fields="nextPageToken,newStartPageToken,changes(fileId,file,removed,time)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()

            for ch in resp.get("changes", []):
                if ch.get("removed"):
                    continue
                file = ch.get("file") or {}
                fid = file.get("id")
                mime = file.get("mimeType", "")
                name = file.get("name", "")
                if not fid:
                    continue

                if fid in LABEL_FOLDER_IDS:
                    print(f"[SKIP] Label folder change: {name} ({fid})"); continue
                if mime == FOLDER_MIME:
                    print(f"[SKIP] Folder item: {name} ({fid})"); continue

                # only handle items inside the watched folder
                parents = file.get("parents", [])
                if DRIVE_FOLDER_ID and DRIVE_FOLDER_ID not in parents:
                    continue

                if mime.startswith("application/vnd.google-apps.") and mime not in {
                    "application/vnd.google-apps.document",
                    "application/vnd.google-apps.spreadsheet",
                }:
                    print(f"[SKIP] Non-exportable Google item: {name} ({mime})")
                    continue

                try:
                    process_file(drive, file)
                except Exception as e:
                    print(f"[WARN] Processing error for {fid}: {e}")
                    continue

            page_token = resp.get("nextPageToken")
            if not page_token:
                new_start = resp.get("newStartPageToken")
                if new_start:
                    write_start_page_token(new_start)
                break

        return make_response("OK", 200)

    @app.route("/drive/ensure-folders", methods=["POST"])
    def http_ensure_folders():
        drive = get_drive()
        global LABEL_TO_ID, LABEL_DESC, ALLOWED, LABEL_FOLDER_IDS
        label_to_id, label_desc, allowed = ensure_folders_from_csv(drive, FOLDER_CATALOG_CSV, DRIVE_PARENT_ID)
        LABEL_TO_ID.clear(); LABEL_TO_ID.update(label_to_id)
        LABEL_DESC.clear(); LABEL_DESC.update(label_desc)
        ALLOWED.clear(); ALLOWED.extend(allowed)
        LABEL_FOLDER_IDS.clear(); LABEL_FOLDER_IDS.update(LABEL_TO_ID.values())
        return {"ok": True, "labels": ALLOWED, "count": len(ALLOWED)}, 200
