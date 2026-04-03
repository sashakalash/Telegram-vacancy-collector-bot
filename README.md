# Telegram Vacancies Collector

Monitors Telegram channels for job postings matching your keywords. Filters noise via exclude keywords, writes matches to Google Sheets, and sends a Telegram notification instantly. Channels and keywords are managed in Google Sheets — no code changes needed. Keywords and channels are hot-reloaded every 30 minutes.

## Project Structure

```
├── main.py           # Entry point, Telethon listener
├── config.py         # Env var bindings
├── filter.py         # Keyword filtering logic
├── sheets.py         # Google Sheets read/write
├── notifier.py       # Telegram bot notifications
├── Procfile          # Railway worker process
├── requirements.txt
├── .env              # Secrets — do not commit
└── credentials.json  # Google Service Account — do not commit
```

## Google Sheets Structure

- Sheet `channels` — columns: `handle`, `channel_id`
- Sheet `keywords` — columns: `keyword`, `type` (`include` / `exclude`)

Edit the sheet; changes are picked up automatically within 30 minutes (no restart needed).

## Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_API_ID` | Telethon app ID (from my.telegram.org) |
| `TELEGRAM_API_HASH` | Telethon app hash |
| `TELEGRAM_BOT_TOKEN` | Bot token for notifications (from @BotFather) |
| `TELEGRAM_CHAT_ID` | Your personal chat ID — where notifications are sent |
| `SESSION_STRING` | Base64 Telethon session string (see below) |
| `GOOGLE_CREDENTIALS_FILE` | Path to service account JSON (default: `credentials.json`) |
| `GOOGLE_SPREADSHEET_ID` | Google Sheets spreadsheet ID |
| `Collector` | Sheet tab name for dedup log (default: `dedup_log`) |

## Railway Deployment

The bot runs as a Railway **worker** (persistent process, no HTTP port).

### 1. Generate SESSION_STRING (once, locally)

Railway has no interactive terminal for first auth, so generate the session string locally first:

```bash
python3 -m venv venv && source venv/bin/activate
pip install telethon python-dotenv
python3 - <<'EOF'
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os, getpass

api_id = int(input("API_ID: "))
api_hash = input("API_HASH: ")

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\nSESSION_STRING =", client.session.save())
EOF
```

Copy the printed string and set it as `SESSION_STRING` in Railway environment variables.

### 2. Deploy

```bash
# Push to the repo connected to Railway — deploy triggers automatically
git push origin main
```

Railway reads `Procfile` and runs `worker: python main.py` as a persistent background process.

### 3. Logs

In the Railway dashboard → your service → **Logs** tab.

Or via CLI:

```bash
railway logs
```

## Local Development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your values
python main.py
```

On first run without `SESSION_STRING`, Telethon will prompt for your phone number and auth code and save `monitor_session.session` locally.
