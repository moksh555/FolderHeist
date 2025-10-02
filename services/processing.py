import io
from googleapiclient.http import MediaIoBaseDownload
from config import FOLDER_MIME, CONF_THRESHOLD
from state import LABEL_TO_ID, LABEL_DESC, ALLOWED
from ai_router import choose_folder_with_gemini

def try_extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join([(p.extract_text() or "") for p in reader.pages])
    except Exception as e:
        print("[PDF] extraction failed:", e)
        return ""

def handle_text(filename, text):   # simple demo hook
    print(f"[TEXT] {filename}: {len(text)} chars")

def handle_binary(filename, blob): # simple demo hook
    print(f"[BINARY] {filename}: {len(blob)} bytes")

def move_file(drive, file_id: str, target_folder_id: str):
    meta = drive.files().get(fileId=file_id, fields="parents").execute()
    parents = meta.get("parents", [])
    if target_folder_id in parents:
        return
    prev_parents = ",".join(parents) if parents else ""
    drive.files().update(
        fileId=file_id,
        addParents=target_folder_id,
        removeParents=prev_parents,
        fields="id,parents",
    ).execute()

def process_file(drive, file_meta):
    file_id = file_meta["id"]
    name = file_meta.get("name", "")
    mime = file_meta.get("mimeType", "")

    print(f"[PROCESS] {name} ({file_id}) type={mime}")

    if mime == FOLDER_MIME:
        print(f"[SKIP] Not a file: folder '{name}'")
        return

    text, content, is_binary = "", None, False

    if mime == "application/vnd.google-apps.document":
        data = drive.files().export(fileId=file_id, mimeType="text/plain").execute()
        text = data.decode("utf-8", errors="ignore")

    elif mime == "application/vnd.google-apps.spreadsheet":
        data = drive.files().export(fileId=file_id, mimeType="text/csv").execute()
        text = data.decode("utf-8", errors="ignore")

    else:
        buf = io.BytesIO()
        req = drive.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        content = buf.getvalue()

        if mime == "application/pdf":
            text = try_extract_pdf_text(content)
        elif mime.startswith("text/"):
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                is_binary = True
        else:
            is_binary = True

    if text:
        handle_text(name, text)
    elif is_binary and content is not None:
        handle_binary(name, content)

    result = choose_folder_with_gemini(
        filename=name,
        text=text or "",
        allowed_labels=ALLOWED,
        label_desc=LABEL_DESC,
    )
    label = (result or {}).get("label")
    conf = float((result or {}).get("confidence") or 0.0)

    if label not in LABEL_TO_ID or conf < CONF_THRESHOLD:
        low = name.lower()
        if "invoice" in low or "receipt" in low:
            label = "Invoices" if "Invoices" in LABEL_TO_ID else label
        elif any(k in low for k in ["transcript", "grade", "gpa"]):
            label = "Academics" if "Academics" in LABEL_TO_ID else label
        elif any(k in low for k in ["passport", "license", " id "]):
            label = "IDs" if "IDs" in LABEL_TO_ID else label

        if label not in LABEL_TO_ID:
            fallback = "Misc" if "Misc" in LABEL_TO_ID else next(iter(ALLOWED), None)
            label = fallback

    if not label or label not in LABEL_TO_ID:
        print(f"[WARN] No valid label for {name}; ALLOWED={len(ALLOWED)}. Skipping move.")
        return


    target_id = LABEL_TO_ID[label]
    move_file(drive, file_id, target_id)
    print(f"[ROUTE] {name} -> {label} ({target_id}) @ conf={conf:.2f}")
