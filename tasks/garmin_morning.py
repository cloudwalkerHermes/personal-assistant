#!/usr/bin/env python3
"""
tasks/garmin_morning.py
-----------------------
Fetches yesterday's Garmin metrics: sleep score, body battery,
steps, resting heart rate, and avg stress. Persists to garmin_daily
table and appends 7-day trend arrows to the Telegram report.

FIRST RUN: authenticates with credentials and caches OAuth tokens
           to .garmin_tokens/. If MFA is enabled, you'll be prompted
           once — never again after that.

DAILY RUNS (cron): silently refreshes the cached token. No credentials
                   sent, no IP ban risk.

Run from personal-assistant/:
    .venv/bin/python3 tasks/garmin_morning.py
"""

import os
import sys
from datetime import date, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from dotenv import load_dotenv
load_dotenv()

from garminconnect import Garmin, GarminConnectAuthenticationError
from integrations.telegram import send as telegram_send
from core.db import get_conn, init_db

GARMIN_EMAIL    = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
TOKEN_STORE     = os.path.join(_ROOT, ".garmin_tokens")

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TODAY     = date.today().isoformat()


# ── AUTH ──────────────────────────────────────────────────────────────────────

def get_client() -> Garmin:
    client = Garmin(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)
    try:
        client.login(TOKEN_STORE)
        print("Garmin: token loaded from cache.")
    except (FileNotFoundError, GarminConnectAuthenticationError, Exception):
        print("Garmin: no cached token — performing full login (MFA prompt if enabled)...")
        client.login()
        client.garth.dump(TOKEN_STORE)
        print(f"Garmin: tokens cached to {TOKEN_STORE}")
    return client


# ── PARSERS ───────────────────────────────────────────────────────────────────

def parse_sleep(data: dict) -> dict:
    if not data:
        return {}
    dto = data.get("dailySleepDTO", {})
    scores = dto.get("sleepScores", {})
    overall = scores.get("overall", {})
    return {
        "score":     overall.get("value"),
        "qualifier": overall.get("qualifierKey", ""),
        "total_h":   round(dto.get("sleepTimeSeconds", 0) / 3600, 1),
        "deep_h":    round(dto.get("deepSleepSeconds", 0) / 3600, 1),
        "rem_h":     round(dto.get("remSleepSeconds", 0) / 3600, 1),
        "light_h":   round(dto.get("lightSleepSeconds", 0) / 3600, 1),
        "awake_h":   round(dto.get("awakeSleepSeconds", 0) / 3600, 1),
    }


def parse_body_battery(data: list) -> dict:
    """
    Returns charged (sleep gain yesterday), drained (day loss yesterday),
    and peak waking level (highest reading in today's entry).
    """
    out = {"charged": None, "drained": None, "waking_peak": None}
    if not data:
        return out
    try:
        yesterday_entry = next((d for d in data if d.get("date") == YESTERDAY), None)
        today_entry     = next((d for d in data if d.get("date") == TODAY),     None)
        if yesterday_entry:
            out["charged"] = yesterday_entry.get("charged")
            out["drained"] = yesterday_entry.get("drained")
        if today_entry:
            vals = [v[1] for v in today_entry.get("bodyBatteryValuesArray", []) if v[1] is not None]
            out["waking_peak"] = max(vals) if vals else None
    except Exception as e:
        print(f"  [!] body battery parse: {e}")
    return out


def parse_stats(data: dict) -> dict:
    if not data:
        return {}
    active_secs = data.get("highlyActiveSeconds", 0) + data.get("activeSeconds", 0)
    return {
        "steps":          data.get("totalSteps"),
        "resting_hr":     data.get("restingHeartRate"),
        "avg_hr":         data.get("averageHeartRate"),
        "avg_stress":     data.get("averageStressLevel"),
        "max_stress":     data.get("maxStressLevel"),
        "active_minutes": active_secs // 60,
        "calories":       data.get("totalKilocalories"),
    }


# ── FETCH ─────────────────────────────────────────────────────────────────────

def safe(label: str, fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        print(f"  [!] {label}: {e}")
        return None


# ── PERSISTENCE ───────────────────────────────────────────────────────────────

def save_daily(sleep: dict, battery: dict, stats: dict):
    init_db()
    conn = get_conn()
    with conn:
        conn.execute("""
            INSERT INTO garmin_daily (
                date, sleep_score, sleep_qualifier,
                sleep_total_h, sleep_deep_h, sleep_rem_h, sleep_light_h, sleep_awake_h,
                battery_charged, battery_drained, battery_waking,
                steps, active_minutes, calories,
                resting_hr, avg_hr, avg_stress, max_stress
            ) VALUES (
                :date, :sleep_score, :sleep_qualifier,
                :sleep_total_h, :sleep_deep_h, :sleep_rem_h, :sleep_light_h, :sleep_awake_h,
                :battery_charged, :battery_drained, :battery_waking,
                :steps, :active_minutes, :calories,
                :resting_hr, :avg_hr, :avg_stress, :max_stress
            )
            ON CONFLICT(date) DO UPDATE SET
                sleep_score      = excluded.sleep_score,
                sleep_qualifier  = excluded.sleep_qualifier,
                sleep_total_h    = excluded.sleep_total_h,
                sleep_deep_h     = excluded.sleep_deep_h,
                sleep_rem_h      = excluded.sleep_rem_h,
                sleep_light_h    = excluded.sleep_light_h,
                sleep_awake_h    = excluded.sleep_awake_h,
                battery_charged  = excluded.battery_charged,
                battery_drained  = excluded.battery_drained,
                battery_waking   = excluded.battery_waking,
                steps            = excluded.steps,
                active_minutes   = excluded.active_minutes,
                calories         = excluded.calories,
                resting_hr       = excluded.resting_hr,
                avg_hr           = excluded.avg_hr,
                avg_stress       = excluded.avg_stress,
                max_stress       = excluded.max_stress
        """, {
            "date":            YESTERDAY,
            "sleep_score":     sleep.get("score"),
            "sleep_qualifier": sleep.get("qualifier"),
            "sleep_total_h":   sleep.get("total_h"),
            "sleep_deep_h":    sleep.get("deep_h"),
            "sleep_rem_h":     sleep.get("rem_h"),
            "sleep_light_h":   sleep.get("light_h"),
            "sleep_awake_h":   sleep.get("awake_h"),
            "battery_charged": battery.get("charged"),
            "battery_drained": battery.get("drained"),
            "battery_waking":  battery.get("waking_peak"),
            "steps":           stats.get("steps"),
            "active_minutes":  stats.get("active_minutes"),
            "calories":        stats.get("calories"),
            "resting_hr":      stats.get("resting_hr"),
            "avg_hr":          stats.get("avg_hr"),
            "avg_stress":      stats.get("avg_stress"),
            "max_stress":      stats.get("max_stress"),
        })
    conn.close()
    print(f"garmin_daily: upserted row for {YESTERDAY}")


# ── TRENDS ────────────────────────────────────────────────────────────────────

def _arrow(current, prev) -> str:
    """Single character direction arrow comparing current to prior average."""
    if current is None or prev is None:
        return ""
    diff = current - prev
    if abs(diff) < 0.5:
        return "→"
    return "↑" if diff > 0 else "↓"


def get_7d_trends(sleep: dict, battery: dict, stats: dict) -> dict:
    """
    Compare today's values against the 7-day average (excluding today).
    Returns dict of field → arrow string.
    """
    conn = get_conn()
    cutoff = (date.today() - timedelta(days=8)).isoformat()
    row = conn.execute("""
        SELECT
            AVG(sleep_score)     AS avg_sleep_score,
            AVG(sleep_total_h)   AS avg_sleep_total,
            AVG(battery_charged) AS avg_charged,
            AVG(battery_waking)  AS avg_waking,
            AVG(steps)           AS avg_steps,
            AVG(resting_hr)      AS avg_rhr,
            AVG(avg_stress)      AS avg_stress
        FROM garmin_daily
        WHERE date > :cutoff AND date < :today
    """, {"cutoff": cutoff, "today": YESTERDAY}).fetchone()
    conn.close()

    if not row or row["avg_sleep_score"] is None:
        return {}  # not enough history yet

    return {
        "sleep_score":  _arrow(sleep.get("score"),           row["avg_sleep_score"]),
        "sleep_total":  _arrow(sleep.get("total_h"),         row["avg_sleep_total"]),
        "charged":      _arrow(battery.get("charged"),        row["avg_charged"]),
        "waking":       _arrow(battery.get("waking_peak"),    row["avg_waking"]),
        "steps":        _arrow(stats.get("steps"),            row["avg_steps"]),
        "rhr":          _arrow(stats.get("resting_hr"),       row["avg_rhr"]),
        "stress":       _arrow(stats.get("avg_stress"),       row["avg_stress"]),
    }


# ── REPORT ────────────────────────────────────────────────────────────────────

def _score_bar(score: int | None) -> str:
    if score is None:
        return ""
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    return "poor"


def _stress_label(avg: int | None) -> str:
    if avg is None:
        return "n/a"
    if avg < 26:
        return f"{avg}  (rest/low)"
    if avg < 51:
        return f"{avg}  (low)"
    if avg < 76:
        return f"{avg}  (medium)"
    return f"{avg}  (high)"


def print_report(sleep: dict, battery: dict, stats: dict):
    W = 52
    print(f"\n{'─'*W}")
    print(f"  GARMIN MORNING REPORT  ({YESTERDAY})")
    print(f"{'─'*W}")

    score = sleep.get("score")
    qualifier = sleep.get("qualifier", "").replace("_", " ").lower()
    print(f"\n  SLEEP")
    print(f"    Score      {score if score else 'n/a'}  ({qualifier or _score_bar(score)})")
    print(f"    Total      {sleep.get('total_h', 'n/a')} h")
    print(f"    Deep       {sleep.get('deep_h', 'n/a')} h  |  "
          f"REM {sleep.get('rem_h', 'n/a')} h  |  "
          f"Light {sleep.get('light_h', 'n/a')} h")
    if sleep.get("awake_h"):
        print(f"    Awake      {sleep.get('awake_h')} h")

    print(f"\n  BODY BATTERY")
    print(f"    Charged last night  +{battery.get('charged', 'n/a')}")
    print(f"    Drained yesterday    {battery.get('drained', 'n/a')}")
    print(f"    Waking peak          {battery.get('waking_peak', 'n/a')}")

    print(f"\n  YESTERDAY")
    steps = stats.get("steps")
    print(f"    Steps      {steps:,}" if steps else "    Steps      n/a")
    rhr   = stats.get("resting_hr")
    avg_hr = stats.get("avg_hr")
    if rhr:
        hr_str = f"{rhr} bpm resting"
        if avg_hr:
            hr_str += f"  /  {avg_hr} avg"
        print(f"    Heart rate {hr_str}")
    print(f"    Stress     {_stress_label(stats.get('avg_stress'))}")
    active = stats.get("active_minutes")
    if active:
        print(f"    Active     {active} min")

    print(f"{'─'*W}\n")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not GARMIN_EMAIL or not GARMIN_PASSWORD:
        print("[!] GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env")
        return

    client = get_client()

    sleep_raw   = safe("sleep",        client.get_sleep_data,   YESTERDAY)
    battery_raw = safe("body battery", client.get_body_battery, YESTERDAY, TODAY)
    stats_raw   = safe("daily stats",  client.get_stats,        YESTERDAY)

    sleep   = parse_sleep(sleep_raw   or {})
    battery = parse_body_battery(battery_raw or {})
    stats   = parse_stats(stats_raw   or {})

    print_report(sleep, battery, stats)

    save_daily(sleep, battery, stats)

    trends = get_7d_trends(sleep, battery, stats)

    def t(key: str) -> str:
        return f" {trends[key]}" if trends.get(key) else ""

    score   = sleep.get("score")
    qual    = sleep.get("qualifier", "").replace("_", " ").lower() or _score_bar(score)
    total_h = sleep.get("total_h", "?")
    steps   = stats.get("steps")
    rhr     = stats.get("resting_hr")

    score = sleep.get("score")
    lines = [f"🏃 Garmin — {YESTERDAY}"]
    lines.append(f"😴 Sleep: {score or 'n/a'}{t('sleep_score')} ({qual}) — {total_h}h{t('sleep_total')}")
    lines.append(f"   Deep {sleep.get('deep_h','?')}h  REM {sleep.get('rem_h','?')}h  Light {sleep.get('light_h','?')}h")
    lines.append(f"🔋 Battery: +{battery.get('charged','?')}{t('charged')} charged / -{battery.get('drained','?')} drained / {battery.get('waking_peak','?')}{t('waking')} waking")
    lines.append(f"👟 Steps: {steps:,}{t('steps')}" if steps else "👟 Steps: n/a")
    lines.append(f"❤️ Resting HR: {rhr} bpm{t('rhr')}" if rhr else "❤️ HR: n/a")
    lines.append(f"😤 Stress: {_stress_label(stats.get('avg_stress'))}{t('stress')}")

    telegram_send("\n".join(lines))


if __name__ == "__main__":
    main()
