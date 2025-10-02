import os, json
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config import SCOPES, TOKEN_FILE, CLIENT_SECRET_FILE, WATCH_ID_FILE, START_TOKEN_FILE

def get_drive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(
                port=8081, access_type="offline", prompt="consent"
            )
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

def read_start_page_token(drive):
    if os.path.exists(START_TOKEN_FILE):
        with open(START_TOKEN_FILE, "r") as f:
            tok = f.read().strip()
            if tok: return tok
    tok = drive.changes().getStartPageToken().execute()["startPageToken"]
    with open(START_TOKEN_FILE, "w") as f:
        f.write(tok)
    return tok

def write_start_page_token(tok: str):
    with open(START_TOKEN_FILE, "w") as f:
        f.write(tok)

def save_watch_info(data: dict):
    with open(WATCH_ID_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_watch_info():
    if not os.path.exists(WATCH_ID_FILE):
        return None
    with open(WATCH_ID_FILE, "r") as f:
        return json.load(f)
