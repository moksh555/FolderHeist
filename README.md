# 🗂️ FolderHeist — AI-Powered Google Drive File Organizer

FolderHeist is a Flask-based webhook service that automatically classifies and organizes files dropped into a Google Drive folder. It listens for Drive change notifications, reads each new file, and uses **Google Gemini AI** (with a keyword-based fallback) to route files into the correct category subfolder.

## ✨ Features

- **Google Drive webhook listener** — registers a Drive push-notification channel and receives real-time change events via an HTTPS webhook
- **Automatic file classification** — uses Google Gemini (`genai`) to analyze file content and name, then assigns it a category label (e.g., Invoices, Academics, IDs, Tax Docs, Healthcare, Work)
- **Keyword heuristic fallback** — if Gemini is unavailable or confidence is below the threshold (default 0.55), a regex-based keyword matcher handles routing
- **PDF text extraction** — extracts readable text from PDF files via PyPDF2 for AI context
- **Google Docs/Sheets support** — exports Google Workspace files to plain text/CSV before classification
- **CSV-driven folder catalog** — category-to-folder mappings are defined in `folders.csv` (editable without code changes)
- **Label hydration on startup** — pre-loads folder labels from Drive on boot for fast lookups

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3 |
| Web Framework | Flask |
| AI Classification | Google Gemini (`google-genai`) |
| Drive Integration | Google Drive API v3 (`google-api-python-client`) |
| PDF Parsing | PyPDF2 |
| Config | `python-dotenv` |
| Deployment | Any HTTPS-accessible server (required for Drive webhooks) |

## 🚀 Setup & Installation

**Prerequisites:** Python 3.10+, a Google Cloud project with Drive API enabled, a public HTTPS URL (e.g., via ngrok or a cloud host)

```bash
# 1. Clone the repository
git clone https://github.com/moksh555/FolderHeist.git
cd FolderHeist

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with:
#   APP_URL=https://your-public-url.com
#   DRIVE_FOLDER_ID=<ID of the Drive folder to watch>
#   DRIVE_PARENT_ID=<ID of parent folder containing category subfolders>
#   GEMINI_API_KEY=<your Gemini API key>

# 4. Add Google OAuth credentials
# Place client_secret.json in the project root

# 5. Configure folders.csv with your category labels and folder IDs
# label,folder_id,description
# Invoices,1abc...,Bills and receipts

# 6. Run the server
python app.py
```

## ▶️ Usage

Once running, FolderHeist:
1. Authenticates with Google Drive and registers a webhook for change notifications
2. On each notification, fetches changed files in the watched folder
3. Downloads and reads file content (PDF text, Google Docs export, raw text)
4. Sends filename + content to Gemini for classification
5. Moves the file to the appropriate category subfolder in Google Drive

## 🏗️ Architecture

```
Google Drive ──(push notification)──► Flask Webhook (app.py)
                                            │
                                    services/processing.py
                                            │
                               ┌────────────┴────────────┐
                        PDF/text extraction         Gemini AI (ai_router.py)
                                                          │
                                              Keyword fallback (if needed)
                                                          │
                                                  move_file() → Drive subfolder
```

**Key modules:**
- `services/notifications.py` — registers Drive watch channels and handles webhook payloads
- `services/processing.py` — orchestrates file download, text extraction, and routing
- `ai_router.py` — wraps Gemini API and keyword heuristics for label selection
- `services/folder_catalog.py` — reads and caches the `folders.csv` mapping
- `state.py` — in-memory store for label→folder ID mappings
