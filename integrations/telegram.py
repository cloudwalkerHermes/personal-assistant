import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")


def send(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [!] Telegram not configured — skipping send.")
        return False
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    ok = True
    for chunk in chunks:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk},
                timeout=10,
            )
            if r.status_code != 200:
                print(f"  [!] Telegram {r.status_code}: {r.text[:100]}")
                ok = False
        except Exception as e:
            print(f"  [!] Telegram error: {e}")
            ok = False
    return ok
