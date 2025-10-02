import csv
from config import FOLDER_MIME
from googleapiclient.errors import HttpError

def _q_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")

def _search_folder_by_name(drive, name: str, parent_id: str):
    safe = _q_escape(name)
    q = (
        f"name = '{safe}' and "
        f"'{parent_id}' in parents and "
        f"mimeType = '{FOLDER_MIME}' and trashed = false"
    )
    resp = drive.files().list(
        q=q, fields="files(id,name)",
        includeItemsFromAllDrives=True, supportsAllDrives=True
    ).execute()
    files = resp.get("files", [])
    return files[0] if files else None

def _create_folder(drive, name: str, parent_id: str) -> str:
    meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
    created = drive.files().create(
        body=meta, fields="id", supportsAllDrives=True
    ).execute()
    return created["id"]

def ensure_folder(drive, label: str, existing_id: str | None, parent_id: str) -> str:
    if existing_id:
        try:
            meta = drive.files().get(
                fileId=existing_id, fields="id,name,mimeType,trashed,parents",
                supportsAllDrives=True
            ).execute()
            if meta.get("trashed") or meta.get("mimeType") != FOLDER_MIME:
                existing_id = None
        except HttpError:
            existing_id = None

    if not existing_id:
        found = _search_folder_by_name(drive, label, parent_id)
        if found:
            return found["id"]
        new_id = _create_folder(drive, label, parent_id)
        print(f"[FOLDER] Created '{label}' -> {new_id}")
        return new_id

    return existing_id

def ensure_folders_from_csv(drive, csv_path: str, parent_id: str):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        assert "label" in r.fieldnames and "folder_id" in r.fieldnames, \
            "CSV must have 'label' and 'folder_id' headers."
        for row in r:
            label = (row.get("label") or "").strip()
            if not label: continue
            current_id = (row.get("folder_id") or "").strip() or None
            folder_id = ensure_folder(drive, label, current_id, parent_id)
            row["folder_id"] = folder_id
            row["description"] = (row.get("description") or "").strip()
            rows.append(row)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["label", "folder_id", "description"])
        w.writeheader(); w.writerows(rows)

    label_to_id = {r["label"].strip(): r["folder_id"].strip() for r in rows}
    label_desc = {r["label"].strip(): r["description"] for r in rows if r.get("description")}
    allowed = [r["label"].strip() for r in rows]
    return label_to_id, label_desc, allowed
