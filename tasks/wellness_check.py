#!/usr/bin/env python3
"""
tasks/wellness_check.py
-----------------------
1:00 PM M-F conditional midday wellness check.

Reads the anomaly flag written by wellness_forecast.py.
If today's 3-day composite average was below threshold, sends
a voice message to Telegram: "Hey Mike."

Exits silently on good days — zero noise when you're doing well.

Run from personal-assistant/:
    .venv/bin/python3 tasks/wellness_check.py
"""

import os
import sys
import json
import tempfile
import subprocess
import requests
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
ANOMALY_FLAG       = os.path.join(_ROOT, ".wellness_anomaly")
TODAY              = date.today().isoformat()


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

def send_voice(text: str) -> bool:
    try:
        from gtts import gTTS
    except ImportError:
        print("[!] gTTS not installed")
        return False

    mp3_path = ogg_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name
        gTTS(text=text, lang="en", slow=False).save(mp3_path)

        ogg_path = mp3_path.replace(".mp3", ".ogg")
        proc = subprocess.run(
            [
                "ffmpeg", "-i", mp3_path,
                "-c:a", "libopus", "-b:a", "24k",
                "-vbr", "on", ogg_path, "-y", "-loglevel", "quiet",
            ],
            capture_output=True,
        )
        if proc.returncode != 0:
            print("[!] ffmpeg failed")
            return False

        with open(ogg_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice",
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={"voice": ("arcus.ogg", f, "audio/ogg")},
                timeout=15,
            )
        ok = r.status_code == 200
        if not ok:
            print(f"[!] sendVoice failed: {r.status_code} {r.text[:120]}")
        return ok

    except Exception as e:
        print(f"[!] voice error: {e}")
        return False
    finally:
        for p in [mp3_path, ogg_path]:
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


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

    sent = send_voice("Hey Mike.")
    if not sent:
        send_text(f"Hey Mike. 👀\n3-day wellness avg: {avg} / 100")
        print("Fell back to text.")

    print("Check-in sent.")


if __name__ == "__main__":
    main()
