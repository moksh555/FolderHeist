from .folder_catalog import ensure_folders_from_csv
from config import FOLDER_CATALOG_CSV, DRIVE_PARENT_ID
from state import LABEL_TO_ID, LABEL_DESC, ALLOWED, LABEL_FOLDER_IDS

def hydrate_labels(drive) -> None:
    """Load CSV→Drive folder map into in-memory globals (mutates, no rebinding)."""
    label_to_id, label_desc, allowed = ensure_folders_from_csv(drive, FOLDER_CATALOG_CSV, DRIVE_PARENT_ID)
    LABEL_TO_ID.clear(); LABEL_TO_ID.update(label_to_id)
    LABEL_DESC.clear(); LABEL_DESC.update(label_desc)
    ALLOWED.clear(); ALLOWED.extend(allowed)
    LABEL_FOLDER_IDS.clear(); LABEL_FOLDER_IDS.update(LABEL_TO_ID.values())
    print(f"[HYDRATE] labels={len(ALLOWED)} folders={len(LABEL_FOLDER_IDS)}")
