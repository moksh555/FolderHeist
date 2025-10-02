# FolderHeist — Google Drive auto-filer (webhook + AI routing)

Drop files into an **Inbox** folder. FolderHeist reads the content, picks the **best destination folder** (Gemini or heuristics), and moves the file—automatically. It uses Google Drive **Change Notifications** (watch channels) + a small Flask webhook.

---

## Features
- 🔔 Real-time Drive watch channel (no polling)
- 🧭 AI routing with Gemini 2.5 Flash (optional) + safe keyword heuristics fallback
- 🗂️ CSV-driven taxonomy (`folders.csv`) — missing folders auto-created; IDs written back
- 🛡️ Safe: skips folders, exports Docs/Sheets properly, webhook always returns 200
- 🌐 ngrok-ready HTTPS for local development
- 🧱 Modular codebase with `.env` configuration

---

## Project layout
```
.
├─ app.py
├─ config.py
├─ ai_router.py
├─ state.py
├─ services/
│  ├─ drive_client.py
│  ├─ folder_catalog.py
│  ├─ notifications.py
│  ├─ processing.py
│  └─ labels.py
├─ folders.csv                 # taxonomy (IDs auto-filled)
├─ requirements.txt
├─ .env.example  # this is were you will set everything like Gemini API key your folder Id which you will watch for any changes and many other thngs, everything is exaplined down below.
└─ client_secret.json         # secret from Google cloud paltform
```

---

## Prerequisites
- Python 3.10+ (3.11/3.12/3.13 OK)
- A Google account
- ngrok (for a public HTTPS URL)
- Gemini API key (Google AI Studio)

---

## 1) Install
~~~bash
git clone <REPO_URL> drivesherpa
cd drivesherpa

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
~~~

---

## 2) Google Cloud setup (Drive API + OAuth)

**We will use google cloud paltform to get the the clients_secret.json.

1. Open **Google Cloud Console** and create/select a project.  
2. **Enable API**: “APIs & Services → Library” → search **Google Drive API** → **Enable**.  
3. **OAuth consent screen**:  
   - User type: **External**  
   - App name: e.g., *FolderHeist*  
   - Add your email; **Save**  
   - Add all other necessary details 
4. **Create credentials → OAuth client ID**:  
   - Application type: **Web app**  
   - Name: *FolderHeist*
   - Authorized redirect URIs: [http://localhost:8081/, http://127.0.0.1:8081/] Add this two links.
   - **Download JSON** and save at repo root as **`client_secret.json`** (exact name)
5. **Publish App**
   - Under Audience
   - Click Pulish App
---

## 3) ngrok (to get `APP_URL`)
~~~bash
# macOS (Homebrew)
brew install ngrok
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>

# Run in a separate terminal
ngrok http 8080
~~~
Copy the **HTTPS** URL shown, e.g. `https://blue-cat-1234.ngrok-free.app`.  
This is your `APP_URL`. (If ngrok restarts, the URL changes—update `.env` and restart the watch channel.)

---

## 4) Configure environment
~~~bash
cp .env.example .env
~~~

Edit `.env`:
~~~ini
# Public base URL from ngrok (must be HTTPS)
APP_URL=https://blue-cat-1234.ngrok-free.app #please change this to match whatever you got from ngrok.

# Webhook path (leave default unless you change routes)
WEBHOOK_ENDPOINT=/drive/notifications

# Flask port
PORT=8080

# Drive folders
# DRIVE_FOLDER_ID: the "Inbox" you DROP files into (the watched folder)
# DRIVE_PARENT_ID: the parent under which label folders (Invoices, etc.) should live
DRIVE_FOLDER_ID=1abcDEF...InboxID
DRIVE_PARENT_ID=1xyzUVW...LabelsParentID

# Permissions: full Drive while developing (needed to create/move)
SCOPES=https://www.googleapis.com/auth/drive

# Local files
WATCH_ID_FILE=watch_channel.json
TOKEN_FILE=token.json
CLIENT_SECRET_FILE=client_secret.json
START_TOKEN_FILE=start_page_token.txt
FOLDER_CATALOG_CSV=folders.csv

# AI routing
ROUTER_CONF_THRESHOLD=0.55
GEMINI_API_KEY= iuhfuierq...........qv (Please set this your Gemini AP which could be reterived from Google AI Studio)
~~~

**How to find folder IDs**: open the folder in Drive and copy the long string in the URL.  
Recommended: create a dedicated **Inbox** folder for `DRIVE_FOLDER_ID`. Your label folders will be created under `DRIVE_PARENT_ID`.
For example: https://.....com/drive/folders/sdhjfshj7gfwbjfwHGHJjsbdvs -> "sdhjfshj7gfwbjfwHGHJjsbdvs" this part is your folder ID

---

## 5) Prepare `folders.csv`
IDs may be left empty — the app will create folders and fill them in.
~~~csv
label,folder_id,description
Invoices,,Vendor invoices and receipts
Academics,,Transcripts, GPA, assignments
IDs,,Government IDs
Photos,,Personal photos and scanned images
Tax Docs,,Tax forms and returns
Offers & Letters,,Offer letters, LORs, HR docs
Healthcare,,Medical reports and prescriptions
Work,,Work docs, resumes, portfolios
Misc,,Catch-all
~~~
Add/remove labels any time. Sync with the endpoint below. This is just anexample which I have been working with but you can add any number of labels, but make sure you describe each folder very precisely, and you dont need any folderID you can leave it blank code will help to create that you just have to work with CSV file if you want to add, remove or update any folder name, description.

---

## 6) Run the server
~~~bash
source .venv/bin/activate
python3 app.py
~~~
On first run you’ll see a Google URL in the console — open it and approve.  
If you need to force a fresh refresh token, delete `token.json` and run again (we use `prompt=consent&access_type=offline`).

---

## 7) Start the Drive watch
With the server running and `APP_URL` set:
~~~bash
curl -X POST "$APP_URL/drive/start-watch" **please replace APP_URL with your APP_URL"
~~~
You should get `{ "status": "watching", ... }`.  
Drop a file into the **Inbox** (`DRIVE_FOLDER_ID`) and watch logs like:
```
[PROCESS] AI.pdf (...) type=application/pdf
[TEXT] AI.pdf: 1772 chars
[ROUTE] AI.pdf -> Invoices (1AbC...) @ conf=0.82
```
> Files added directly into subfolders (e.g., Invoices) are **ignored by design**. Flow = **Inbox → classify → move**.

---

## 8) Useful endpoints
~~~bash
# Create/refresh label folders from CSV + cache their IDs
curl -X POST "$APP_URL/drive/ensure-folders"

# Start a new watch channel (also hydrates labels)
curl -X POST "$APP_URL/drive/start-watch"

# Stop the current watch channel
curl -X POST "$APP_URL/drive/stop-watch"

# Health check
curl "$APP_URL/healthz"
~~~

---

## 9) Troubleshooting

**`redirect_uri_mismatch`**  
Make Sure you have added these two [http://localhost:8081/, http://127.0.0.1:8081/] links under Authorized redirect URIs during your client creation.

**`Error 403: access_denied`**  
Add your Google account under **OAuth consent → Test users**.

**`missing fields refresh_token`**  
Delete `token.json` and re-auth; Desktop flow uses `prompt=consent&access_type=offline`.

**403 “Only files with binary content can be downloaded. Use Export …”**  
That event was a **folder** or non-exportable Google editor type. Folders are skipped; Docs/Sheets are exported via `files.export`.

**Nothing happens on upload**  
- Ensure you uploaded **into the Inbox** (`DRIVE_FOLDER_ID`), not a subfolder  
- Confirm `APP_URL` matches your current ngrok URL  
- Re-start the watch: `curl -X POST "$APP_URL/drive/start-watch"`

**ngrok URL changed**  
Update `APP_URL` in `.env`, restart the server, and start the watch again.

---

---

## 10) Clean reset
~~~bash
rm -f token.json watch_channel.json start_page_token.txt
python3 app.py                 # re-auth in browser
curl -X POST "$APP_URL/drive/start-watch"
~~~

---

## License
Moksh AshishKumar Vaghasia @2025
