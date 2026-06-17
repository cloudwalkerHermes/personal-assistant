#!/usr/bin/env python3
"""
tasks/system_health.py
-----------------------
Every 4 hours: reads `crontab -l` as the source of truth for each job's
expected schedule, compares it against that job's log file mtime (a proxy
for "did it actually run"), and flags any job more than ~10 minutes late
relative to its most recent scheduled fire time.

Issues-only: posts to the System Health Telegram channel ONLY when a
mismatch is found. Silent otherwise — no noise on a healthy system.

Run from personal-assistant/:
    .venv/bin/python3 tasks/system_health.py
"""

import os
import re
import sys
import subprocess
import requests
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from dotenv import load_dotenv
load_dotenv()

from croniter import croniter

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HEALTH_CHAT_ID      = os.getenv("TELEGRAM_HEALTH_CHAT_ID")

TOLERANCE_MIN = 10
SELF_NAME     = "system_health.py"

# Long-running daemon-style jobs that only log at sparse events (market open/
# close, trades) rather than on every invocation. Log mtime isn't a reliable
# "did it run" signal for these — exclude them.
EXCLUDED = {"checkmark_scanner.py"}


# ── CRONTAB PARSING ───────────────────────────────────────────────────────────

def get_crontab_entries() -> list[dict]:
    """Parse `crontab -l`, extracting schedule + log file path per job."""
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return []

    entries = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        schedule = " ".join(parts[:5])
        command  = parts[5]

        log_match = re.search(r">>\s*(\S+\.log)", command)
        if not log_match:
            continue
        log_path = log_match.group(1)

        script_match = re.search(r"([\w_]+\.py)", command)
        label = script_match.group(1) if script_match else command[:40]

        if label == SELF_NAME or label in EXCLUDED:
            continue

        entries.append({"schedule": schedule, "log_path": log_path, "label": label})

    return entries


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────

def check_job(entry: dict, now: datetime) -> str | None:
    """Returns a problem description, or None if healthy."""
    schedule = entry["schedule"]
    log_path = entry["log_path"]
    label    = entry["label"]

    try:
        cron = croniter(schedule, now)
        expected_last = cron.get_prev(datetime)
    except Exception as e:
        return f"{label}: couldn't parse schedule \"{schedule}\" ({e})"

    if not os.path.exists(log_path):
        return f"{label}: expected run {expected_last:%a %H:%M} — log file missing entirely"

    mtime = datetime.fromtimestamp(os.path.getmtime(log_path))
    drift_min = (expected_last - mtime).total_seconds() / 60

    if drift_min > TOLERANCE_MIN:
        return (f"{label}: expected run {expected_last:%a %H:%M}, "
                f"log last touched {mtime:%a %H:%M} ({int(drift_min)}m overdue)")

    return None


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_BOT_TOKEN or not HEALTH_CHAT_ID:
        print("[!] TELEGRAM_BOT_TOKEN or TELEGRAM_HEALTH_CHAT_ID not set in .env")
        return

    now = datetime.now()
    entries = get_crontab_entries()

    if not entries:
        print("No crontab entries found — skipping check.")
        return

    problems = []
    for entry in entries:
        issue = check_job(entry, now)
        if issue:
            problems.append(issue)

    if not problems:
        print(f"[{now:%Y-%m-%d %H:%M}] All {len(entries)} jobs healthy — no message sent.")
        return

    lines = ["🚨 Arcus — System Health (schedule mismatch)", ""]
    for p in problems:
        lines.append(f"  • {p}")

    msg = "\n".join(lines)
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
