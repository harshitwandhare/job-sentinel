# Telegram Bot Setup Guide

This guide walks you through creating your Telegram bot and getting the
credentials needed for Job Sentinel.

---

## Step 1 — Create the bot

1. Open Telegram on your phone or desktop
2. Search for **[@BotFather](https://t.me/BotFather)** and open the chat
3. Send `/newbot`
4. BotFather will ask for:
   - **Name**: e.g. `My Job Sentinel`  (shown as the bot's display name)
   - **Username**: e.g. `myjobsentinel_bot`  (must end in `bot`)
5. BotFather replies with your **bot token**:
   ```
   Use this token to access the HTTP API:
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
6. Copy this token → paste into `TELEGRAM_BOT_TOKEN` in your `.env`

---

## Step 2 — Get your Chat ID

1. Search for your new bot by its username and open the chat
2. Send any message (e.g. `/start` or `hello`)
3. Open this URL in your browser (replace `<TOKEN>` with your actual token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
4. You'll see a JSON response. Find `message.chat.id`:
   ```json
   {
     "result": [{
       "message": {
         "chat": {
           "id": 123456789,   ← this is your chat ID
           ...
         }
       }
     }]
   }
   ```
5. Copy this number → paste into `TELEGRAM_CHAT_ID` in your `.env`

> **Note:** If `result` is empty, send another message to the bot first,
> then refresh the URL.

---

## Step 3 — Verify

```bash
# Test that the credentials work:
uv run python -c "
import httpx, os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat  = os.getenv('TELEGRAM_CHAT_ID')
r = httpx.post(
    f'https://api.telegram.org/bot{token}/sendMessage',
    json={'chat_id': chat, 'text': '✅ Job Sentinel credentials work!'}
)
print(r.json())
"
```

If you receive the message in Telegram, you're all set.

---

## Step 4 — Run the bot

```bash
uv run job-sentinel run
```

Open Telegram, send `/start` to your bot, and you'll see the command menu.
