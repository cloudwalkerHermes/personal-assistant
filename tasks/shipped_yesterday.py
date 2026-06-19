#!/usr/bin/env python3
"""
tasks/shipped_yesterday.py
---------------------------
Early-AM positive digest: what actually shipped (git commits) in
personal-assistant yesterday. Always posts — no issues-only filter,
this is a deliberate daily affirmation, not an alert.

Run from personal-assistant/:
    .venv/bin/python3 tasks/shipped_yesterday.py
"""

import os
import sys
import subprocess
import requests
from datetime import date, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HEALTH_CHAT_ID      = os.getenv("TELEGRAM_HEALTH_CHAT_ID")


def get_yesterdays_commits() -> list[str]:
    yesterday = date.today() - timedelta(days=1)
    today     = date.today()

    result = subprocess.run(
        ["git", "log",
         f"--since={yesterday.isoformat()} 00:00:00",
         f"--until={today.isoformat()} 00:00:00",
         "--pretty=format:%s"],
        capture_output=True, text=True, cwd=_ROOT,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def build_message(commits: list[str]) -> str:
    yesterday = date.today() - timedelta(days=1)
    lines = [f"🚀 ArcusHermes — Shipped ({yesterday:%a %b %-d})", ""]

    if not commits:
        lines.append("Quiet day on the build side. That's fine too.")
        return "\n".join(lines)

    for c in commits:
        lines.append(f"  • {c}")

    lines.append("")
    lines.append(f"{len(commits)} commit{'s' if len(commits) != 1 else ''}. Keep building.")
    return "\n".join(lines)


def main():
    if not TELEGRAM_BOT_TOKEN or not HEALTH_CHAT_ID:
        print("[!] TELEGRAM_BOT_TOKEN or TELEGRAM_HEALTH_CHAT_ID not set in .env")
        return

    commits = get_yesterdays_commits()
    msg = build_message(commits)
    print(msg)

    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": HEALTH_CHAT_ID, "text": msg},
        timeout=10,
    )
    if r.status_code != 200:
        print(f"[!] Telegram send failed: {r.status_code} {r.text[:200]}")


if __name__ == "__main__":
    main()
