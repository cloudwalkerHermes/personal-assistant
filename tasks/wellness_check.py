#!/usr/bin/env python3
"""
tasks/wellness_check.py
-----------------------
1:00 PM M-F conditional midday wellness check.

Reads the anomaly flag written by wellness_forecast.py.
If today's 3-day composite average was below threshold, has Voicebox
speak a check-in through the Rory Cochrane voice clone, played locally
through the Windows desktop's speakers.

Local-only by design for now — if that stops fitting (more time away
from the desktop), revisit and route this back through Telegram voice
the way it used to work.

Exits silently on good days — zero noise when you're doing well.

Run from personal-assistant/:
    .venv/bin/python3 tasks/wellness_check.py
"""

import os
import sys
import json
import requests
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID")
ANOMALY_FLAG        = os.path.join(_ROOT, ".wellness_anomaly")
TODAY               = date.today().isoformat()

VOICEBOX_URL  = "http://192.168.1.3:17493"
RORY_PROFILE  = "35b05941-2681-441f-97d4-905cd7a2d5e4"  # Rory Cochrane
RORY_ENGINE   = "qwen"
CHECKIN_TEXT  = "Hey Mike, it's your pal Slater... just like checking up on ya, man."


# ── FLAG ──────────────────────────────────────────────────────────────────────

def read_flag() -> dict | None:
    if not os.path.exists(ANOMALY_FLAG):
        return None
    try:
        with open(ANOMALY_FLAG) as f:
            data = json.load(f)
        return data if data.get("date") == TODAY else None
    except Exception:
        return None


# ── VOICE ─────────────────────────────────────────────────────────────────────

def send_voice() -> bool:
    try:
        r = requests.post(
            f"{VOICEBOX_URL}/speak",
            json={"text": CHECKIN_TEXT, "profile": RORY_PROFILE, "engine": RORY_ENGINE},
            timeout=30,
        )
        ok = r.status_code == 200
        if not ok:
            print(f"[!] Voicebox /speak failed: {r.status_code} {r.text[:120]}")
        return ok
    except Exception as e:
        print(f"[!] Voicebox unreachable: {e}")
        return False


def send_text(message: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=10,
        )
    except Exception as e:
        print(f"[!] Telegram text error: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    flag = read_flag()
    if not flag:
        print("No anomaly today — Arcus stands down.")
        return

    avg = flag.get("three_day_avg", "?")
    print(f"Anomaly active: 3-day avg {avg}. Sending check-in.")

    sent = send_voice()
    if not sent:
        send_text(f"🎸 Slater was gonna check up on ya, Mike, but couldn't reach the booth.\n3-day wellness avg: {avg} / 100")
        print("Fell back to text.")

    print("Check-in sent.")


if __name__ == "__main__":
    main()
