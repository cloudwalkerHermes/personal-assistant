#!/usr/bin/env python3
"""
tasks/garmin_fitness.py
-----------------------
Weekly pull of Garmin fitness age and its component metrics.
Persists to garmin_fitness table. Designed to run Monday mornings
so the weekly summary lands alongside the daily report.

Fitness age components tracked:
  - chronological_age vs fitness_age vs achievable_age
  - vigorous activity (days/week, minutes/week rolling avg)
  - resting HR
  - BMI (if measured; Garmin gets it from Garmin Index scale or manual entry)

Run from personal-assistant/:
    .venv/bin/python3 tasks/garmin_fitness.py
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

TODAY = date.today().isoformat()


# ── AUTH ──────────────────────────────────────────────────────────────────────

def get_client() -> Garmin:
    client = Garmin(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)
    try:
        client.login(TOKEN_STORE)
        print("Garmin: token loaded from cache.")
    except (FileNotFoundError, GarminConnectAuthenticationError, Exception):
        print("Garmin: no cached token — performing full login...")
        client.login()
        client.garth.dump(TOKEN_STORE)
        print(f"Garmin: tokens cached to {TOKEN_STORE}")
    return client


def safe(label: str, fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        print(f"  [!] {label}: {e}")
        return None


# ── PARSE ─────────────────────────────────────────────────────────────────────

def parse_fitness_age(data: dict) -> dict:
    """
    Parses the response from get_fitness_age().
    Expected keys (may vary by garminconnect version):
      chronologicalAge, biologicalAge, achievableAge, previousBiologicalAge,
      vigorousActivityDaysAverage, vigorousActivityMinutesAverage,
      restingHeartRate, bmi, idealBmi, bmiLastMeasured
    """
    if not data:
        return {}

    out = {
        "chronological_age":    data.get("chronologicalAge"),
        "fitness_age":          data.get("biologicalAge"),
        "achievable_age":       data.get("achievableAge"),
        "previous_fitness_age": data.get("previousBiologicalAge"),
        "vigorous_days_avg":    data.get("vigorousActivityDaysAverage"),
        "vigorous_minutes_avg": data.get("vigorousActivityMinutesAverage"),
        "rhr":                  data.get("restingHeartRate"),
        "bmi":                  data.get("bmi"),
        "bmi_target":           data.get("idealBmi"),
        "bmi_last_measured":    data.get("bmiLastMeasured"),
    }
    return out


# ── PERSISTENCE ───────────────────────────────────────────────────────────────

def save_fitness(parsed: dict):
    init_db()
    conn = get_conn()
    with conn:
        conn.execute("""
            INSERT INTO garmin_fitness (
                date, chronological_age, fitness_age, achievable_age,
                previous_fitness_age, vigorous_days_avg, vigorous_minutes_avg,
                rhr, bmi, bmi_target, bmi_last_measured
            ) VALUES (
                :date, :chronological_age, :fitness_age, :achievable_age,
                :previous_fitness_age, :vigorous_days_avg, :vigorous_minutes_avg,
                :rhr, :bmi, :bmi_target, :bmi_last_measured
            )
            ON CONFLICT(date) DO UPDATE SET
                chronological_age    = excluded.chronological_age,
                fitness_age          = excluded.fitness_age,
                achievable_age       = excluded.achievable_age,
                previous_fitness_age = excluded.previous_fitness_age,
                vigorous_days_avg    = excluded.vigorous_days_avg,
                vigorous_minutes_avg = excluded.vigorous_minutes_avg,
                rhr                  = excluded.rhr,
                bmi                  = excluded.bmi,
                bmi_target           = excluded.bmi_target,
                bmi_last_measured    = excluded.bmi_last_measured
        """, {"date": TODAY, **parsed})
    conn.close()
    print(f"garmin_fitness: upserted row for {TODAY}")


# ── TREND ─────────────────────────────────────────────────────────────────────

def get_fitness_trend(current_age: float | None) -> str:
    """Compare fitness age to the reading 4 weeks ago."""
    if current_age is None:
        return ""
    conn = get_conn()
    cutoff = (date.today() - timedelta(days=35)).isoformat()
    row = conn.execute("""
        SELECT fitness_age FROM garmin_fitness
        WHERE date > :cutoff AND date < :today
        ORDER BY date ASC LIMIT 1
    """, {"cutoff": cutoff, "today": TODAY}).fetchone()
    conn.close()

    if not row or row["fitness_age"] is None:
        return ""
    diff = current_age - row["fitness_age"]
    if abs(diff) < 0.1:
        return " →"
    return f" {'↓' if diff < 0 else '↑'} ({abs(diff):.1f} vs 4wk ago)"


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not GARMIN_EMAIL or not GARMIN_PASSWORD:
        print("[!] GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env")
        return

    client = get_client()

    raw = safe("fitness age", client.get_fitness_age)
    if not raw:
        print("[!] No fitness age data returned — skipping.")
        return

    parsed = parse_fitness_age(raw)
    print(parsed)

    save_fitness(parsed)

    trend = get_fitness_trend(parsed.get("fitness_age"))

    chron = parsed.get("chronological_age")
    fit   = parsed.get("fitness_age")
    best  = parsed.get("achievable_age")
    prev  = parsed.get("previous_fitness_age")
    vig_d = parsed.get("vigorous_days_avg")
    vig_m = parsed.get("vigorous_minutes_avg")
    bmi   = parsed.get("bmi")
    bmi_t = parsed.get("bmi_target")

    lines = [f"🧬 Garmin Fitness Age — {TODAY}"]
    lines.append(f"  Age: {chron} chrono → {fit} fitness{trend}")
    if best:
        lines.append(f"  Achievable: {best}  (gap: {round(fit - best, 1) if fit and best else '?'} yrs)")
    if prev:
        delta = round(fit - prev, 1) if fit and prev else None
        arrow = ("↓" if delta < 0 else "↑") if delta is not None else ""
        lines.append(f"  vs last week: {prev} → {fit}  {arrow}")
    if vig_d is not None:
        lines.append(f"  Vigorous activity: {vig_d:.1f} days/wk  {vig_m:.0f} min/wk avg" if vig_m else f"  Vigorous days/wk: {vig_d:.1f}")
    if bmi:
        bmi_note = f"  (target {bmi_t})" if bmi_t else ""
        lines.append(f"  BMI: {bmi:.1f}{bmi_note}")
    if not any([fit, bmi, vig_d]):
        lines.append("  (no component data returned — may need Garmin Index scale)")

    telegram_send("\n".join(lines))


if __name__ == "__main__":
    main()
