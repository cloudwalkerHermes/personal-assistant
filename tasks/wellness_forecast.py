#!/usr/bin/env python3
"""
tasks/wellness_forecast.py
--------------------------
7:15 AM M-F morning briefing. Combines:
  - Mike wellness composite score + 3-day trend + forecast label
  - Physical weather for Paris TX

Writes a flag file if 3-day avg is below anomaly threshold so
wellness_check.py knows to fire a midday check-in.

Run from personal-assistant/:
    .venv/bin/python3 tasks/wellness_forecast.py
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

from integrations.telegram import send as telegram_send
from core.db import get_conn, init_db

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_ZIP     = os.getenv("OPENWEATHER_ZIP", "75460")
OPENWEATHER_COUNTRY = os.getenv("OPENWEATHER_COUNTRY", "US")

TODAY          = date.today().isoformat()
ANOMALY_FLAG   = os.path.join(_ROOT, ".wellness_anomaly")
ANOMALY_THRESH = 50  # 3-day avg below this → midday voice check fires


# ── COMPOSITE ─────────────────────────────────────────────────────────────────

def _rhr_score(rhr) -> float:
    if rhr is None:
        return 50.0
    return max(0.0, min(100.0, (80 - rhr) / 30 * 100))


def composite_score(row) -> float | None:
    sleep_h = row["sleep_total_h"]
    sleep_s = row["sleep_score"]
    battery = row["battery_waking"]
    rhr     = row["resting_hr"]
    if sleep_h is None and sleep_s is None and battery is None:
        return None
    sleep_pct = min((sleep_h or 0) / 9.0 * 100, 100)
    return round(
        (sleep_pct + (sleep_s or 0) + (battery or 0) + _rhr_score(rhr) * 0.5) / 3.5,
        1,
    )


def get_last_n(n: int = 3) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT date, sleep_score, sleep_total_h, battery_waking, resting_hr
        FROM garmin_daily ORDER BY date DESC LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    return list(reversed(rows))


# ── MIKE FORECAST ─────────────────────────────────────────────────────────────

def mike_forecast(avg, trend_dir: str) -> tuple[str, str]:
    if avg is None:
        return "🌫️", "No data yet — building baseline"
    if avg >= 70:
        return ("☀️", "Clear skies — peak productivity window") if trend_dir != "down" \
               else ("🌤️", "Good day — watch the trend")
    if avg >= 55:
        return ("⛅", "Partly cloudy — solid but not peak") if trend_dir != "down" \
               else ("🌧️", "Headwinds — pace yourself today")
    if avg >= 40:
        return "🌧️", "Rough weather — rest when you can"
    return "⛈️", "Storm warning — possible naders"


# ── REAL WEATHER ──────────────────────────────────────────────────────────────

OWM_EMOJI = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️", "Drizzle": "🌦️",
    "Thunderstorm": "⛈️", "Snow": "❄️", "Mist": "🌫️",
    "Fog": "🌫️", "Haze": "🌫️", "Smoke": "🌫️",
}

def _owm_params() -> dict:
    return {
        "zip":   f"{OPENWEATHER_ZIP},{OPENWEATHER_COUNTRY}",
        "appid": OPENWEATHER_API_KEY,
        "units": "imperial",
    }

def fetch_current() -> dict | None:
    if not OPENWEATHER_API_KEY:
        return None
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params=_owm_params(), timeout=8,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def fetch_highlow() -> tuple:
    if not OPENWEATHER_API_KEY:
        return None, None
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params=_owm_params(), timeout=8,
        )
        if r.status_code != 200:
            return None, None
        entries = [
            e["main"]["temp"]
            for e in r.json().get("list", [])
            if e.get("dt_txt", "").startswith(TODAY)
        ]
        return (max(entries), min(entries)) if entries else (None, None)
    except Exception:
        return None, None

def build_weather_lines(w, hi, lo) -> list[str]:
    if not w:
        return ["🌍 Weather unavailable (key activating — check back tomorrow)"]
    main  = w.get("weather", [{}])[0].get("main", "")
    desc  = w.get("weather", [{}])[0].get("description", "").capitalize()
    temp  = w.get("main", {}).get("temp")
    feels = w.get("main", {}).get("feels_like")
    hum   = w.get("main", {}).get("humidity")
    wind  = w.get("wind", {}).get("speed")
    city  = w.get("name", "Paris TX")
    emoji = OWM_EMOJI.get(main, "🌡️")

    line1 = f"{emoji} {city}  {temp:.0f}°F" if temp else f"{emoji} {city}"
    if feels:
        line1 += f"  feels {feels:.0f}°"
    line2_parts = []
    if hi and lo:
        line2_parts.append(f"H {hi:.0f}° L {lo:.0f}°")
    if hum:
        line2_parts.append(f"humidity {hum}%")
    if wind:
        line2_parts.append(f"wind {wind:.0f} mph")
    lines = [line1]
    if line2_parts:
        lines.append("   " + "  ".join(line2_parts))
    if desc:
        lines.append(f"   {desc}")
    return lines


# ── ANOMALY FLAG ──────────────────────────────────────────────────────────────

def write_flag(avg):
    if avg is not None and avg < ANOMALY_THRESH:
        with open(ANOMALY_FLAG, "w") as f:
            json.dump({"date": TODAY, "three_day_avg": round(avg, 1)}, f)
    elif os.path.exists(ANOMALY_FLAG):
        os.remove(ANOMALY_FLAG)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    init_db()
    rows = get_last_n(3)

    scored = [(r["date"], composite_score(r), r) for r in rows]
    valid_scores = [c for _, c, _ in scored if c is not None]
    avg_3d = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

    trend_dir = "flat"
    if len(valid_scores) >= 2:
        diff = valid_scores[-1] - valid_scores[0]
        trend_dir = "up" if diff > 3 else ("down" if diff < -3 else "flat")

    trend_arrow = "↑" if trend_dir == "up" else ("↓" if trend_dir == "down" else "→")
    trend_str   = " → ".join(str(int(c)) if c is not None else "?" for _, c, _ in scored)

    forecast_emoji, forecast_label = mike_forecast(avg_3d, trend_dir)

    latest_row  = rows[-1] if rows else None
    latest_comp = scored[-1][1] if scored else None

    if latest_row:
        sleep_h  = int(round(latest_row["sleep_total_h"] or 0))
        sleep_s  = latest_row["sleep_score"] or "?"
        battery  = latest_row["battery_waking"] or "?"
        c_disp   = int(latest_comp) if latest_comp is not None else "?"
        glance   = f"🧠 {c_disp}   😴 {sleep_h}   💤 {sleep_s}   🔋 {battery}"
    else:
        glance = "🧠 —   (no garmin data yet — run garmin_morning first)"

    w_raw     = fetch_current()
    hi, lo    = fetch_highlow()
    w_lines   = build_weather_lines(w_raw, hi, lo)

    write_flag(avg_3d)

    day_label = date.today().strftime("%A  %b %-d")

    msg_lines = [f"🗓️  {day_label}", ""]
    msg_lines += w_lines
    msg_lines += [
        "",
        f"{forecast_emoji} Mike forecast: {forecast_label}",
        glance,
    ]
    if len(valid_scores) >= 2:
        msg_lines.append(f"📊 3-day: {trend_str}  {trend_arrow}  avg {int(avg_3d)}")
    if avg_3d is not None and avg_3d < ANOMALY_THRESH:
        msg_lines.append("⚠️  Trending low — midday check incoming")

    telegram_send("\n".join(msg_lines))


if __name__ == "__main__":
    main()
