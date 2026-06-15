#!/usr/bin/env python3
"""
tasks/money_status.py
---------------------
Syncs latest transactions, pulls live Plaid balances, and projects
total cash 14 days out using recurring bills + Google Calendar events.

Run from personal-assistant/:
    .venv/bin/python3 tasks/money_status.py
"""

import os
import re
import sys
import calendar as cal_mod
from datetime import date, datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)  # token.json, .env, and DB_PATH all resolve from here

from dotenv import load_dotenv
load_dotenv()

from core.db import get_conn, init_db
from integrations.plaid.client import get_client
from integrations.google.calendar import get_service
from integrations.telegram import send as telegram_send
from tasks.sync_transactions import run as sync_transactions

from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest

TODAY   = date.today()
HORIZON = TODAY + timedelta(days=14)
LOOKBACK_DAYS = 30
BILLS_CAL_NAME = "Bills & Recurring"


# ── BALANCES ──────────────────────────────────────────────────────────────────

def fetch_balances() -> tuple[dict, float]:
    """Returns ({institution: [account dicts]}, total_available)."""
    conn = get_conn()
    items = conn.execute(
        "SELECT access_token, institution_name FROM plaid_items"
    ).fetchall()
    conn.close()

    client = get_client()
    result = {}
    total = 0.0

    for item in items:
        inst = item["institution_name"] or "Unknown"
        try:
            resp = client.accounts_balance_get(
                AccountsBalanceGetRequest(access_token=item["access_token"])
            )
            accounts = []
            for acct in resp["accounts"]:
                b = acct["balances"]
                avail = b.get("available")
                curr  = b.get("current")
                accounts.append({
                    "name":      acct["name"],
                    "type":      str(acct["type"]),
                    "available": avail,
                    "current":   curr,
                })
                total += avail if avail is not None else (curr or 0.0)
            result[inst] = accounts
        except Exception as e:
            print(f"  [!] Balance fetch failed for {inst}: {e}")

    return result, total


# ── RECURRING PROJECTION ──────────────────────────────────────────────────────

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the nth occurrence of weekday (Mon=0) in the given month."""
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _months_in_window() -> list[tuple[int, int]]:
    months = set()
    d = TODAY
    while d <= HORIZON:
        months.add((d.year, d.month))
        d += timedelta(days=1)
    return list(months)


def hits_in_window(bills: list[dict]) -> list[dict]:
    """Bills/income expected between TODAY and HORIZON inclusive."""
    hits = []
    months = _months_in_window()

    for bill in bills:
        freq    = bill["frequency"]
        name    = bill["name"]
        amount  = bill["amount"]
        due_day = bill["due_day"]

        if freq == "monthly":
            for year, month in months:
                last = cal_mod.monthrange(year, month)[1]
                hit  = date(year, month, min(due_day, last))
                if TODAY <= hit <= HORIZON:
                    hits.append({"name": name, "amount": amount, "date": hit})

        elif freq == "monthly_2nd_wed":
            for year, month in months:
                hit = _nth_weekday(year, month, 2, 2)  # Wednesday = 2
                if TODAY <= hit <= HORIZON:
                    hits.append({"name": name, "amount": amount, "date": hit})

        elif freq == "weekly":
            # Expect 2 payments in any 14-day window
            for i in range(1, 3):
                hits.append({"name": name, "amount": amount,
                             "date": TODAY + timedelta(weeks=i)})

        elif freq == "quarterly":
            quarter_months = {1, 4, 7, 10}
            for year, month in months:
                if month in quarter_months:
                    last = cal_mod.monthrange(year, month)[1]
                    hit  = date(year, month, min(due_day, last))
                    if TODAY <= hit <= HORIZON:
                        hits.append({"name": name, "amount": amount, "date": hit})

    hits.sort(key=lambda x: x["date"])
    return hits


# ── VARIABLE SPEND ────────────────────────────────────────────────────────────

SPEND_BUCKETS = {
    "🛒 Food & Dining":  {"FOOD_AND_DRINK"},
    "🛍️ Shopping":       {"GENERAL_MERCHANDISE"},
    "🏥 Medical":        {"MEDICAL"},
    "⛽ Transport":      {"TRANSPORTATION"},
    "🎭 Entertainment":  {"ENTERTAINMENT"},
    "🔧 Services":       {"GENERAL_SERVICES", "HOME_IMPROVEMENT"},
    "📦 Other":          set(),  # catch-all for uncategorized
}

# Exclude these Plaid categories entirely from variable spend — already tracked in
# the recurring projection or are non-variable by nature.
EXCLUDE_CATEGORIES = {
    "TRANSFER_OUT", "TRANSFER_IN", "BANK_FEES",
    "RENT_AND_UTILITIES",  # utilities/rent — captured in recurring_bills
    "LOAN_PAYMENTS",       # car loan, etc. — captured in recurring_bills
}


def variable_spend_by_bucket(bills: list[dict]) -> dict:
    """
    Returns {bucket_label: {"total": float, "daily": float}} for the last
    LOOKBACK_DAYS, excluding transfers and known recurring merchants.
    """
    known = {b["plaid_merchant"].lower() for b in bills if b.get("plaid_merchant")}
    since = (TODAY - timedelta(days=LOOKBACK_DAYS)).isoformat()

    conn = get_conn()
    rows = conn.execute(
        "SELECT amount, name, merchant_name, category FROM transactions "
        "WHERE date >= ? AND pending = 0 AND amount > 0",
        (since,)
    ).fetchall()
    conn.close()

    buckets: dict[str, float] = {k: 0.0 for k in SPEND_BUCKETS}

    for row in rows:
        cat     = (row["category"] or "").upper()
        name_l  = (row["name"] or "").lower()
        merch_l = (row["merchant_name"] or "").lower()

        # Skip transfers and fees by category
        if cat in EXCLUDE_CATEGORIES:
            continue
        # Skip known recurring merchants
        if any(k in name_l or k in merch_l for k in known):
            continue

        # Assign to bucket
        assigned = False
        for label, categories in SPEND_BUCKETS.items():
            if categories and cat in categories:
                buckets[label] += row["amount"]
                assigned = True
                break
        if not assigned:
            buckets["📦 Other"] += row["amount"]

    result = {}
    for label, total in buckets.items():
        if total > 0:
            result[label] = {"total": round(total, 2), "daily": round(total / LOOKBACK_DAYS, 2)}
    return result


def avg_daily_variable(bills: list[dict]) -> float:
    """Total average daily variable spend across all buckets."""
    buckets = variable_spend_by_bucket(bills)
    return sum(b["daily"] for b in buckets.values())


# ── CALENDAR SCAN ─────────────────────────────────────────────────────────────

def calendar_money_events() -> list[dict]:
    """
    Scan all Google calendars except Bills & Recurring for events in the
    14-day window that contain a dollar amount in the title.
    """
    events = []
    try:
        service  = get_service()
        cal_list = service.calendarList().list().execute().get("items", [])

        time_min = datetime.combine(TODAY, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        time_max = datetime.combine(HORIZON + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()

        for cal in cal_list:
            if cal.get("summary") == BILLS_CAL_NAME:
                continue

            result = service.events().list(
                calendarId=cal["id"],
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            for ev in result.get("items", []):
                title = ev.get("summary", "")
                match = re.search(r'\$([0-9,]+(?:\.[0-9]{1,2})?)', title)
                if not match:
                    continue
                amount = float(match.group(1).replace(",", ""))
                start  = ev["start"].get("date") or ev["start"].get("dateTime", "")[:10]
                events.append({
                    "name":   title,
                    "amount": amount,
                    "date":   date.fromisoformat(start),
                })
    except Exception as e:
        print(f"  [!] Calendar scan failed: {e}")

    return events


# ── REPORT ────────────────────────────────────────────────────────────────────

def print_report(balances: dict, total_avail: float, recurring_hits: list[dict],
                 cal_events: list[dict], avg_daily: float, buckets: dict):
    W = 60

    print(f"\n{'─'*W}")
    print(f"  CURRENT BALANCES  ({TODAY})")
    print(f"{'─'*W}")
    for inst, accounts in balances.items():
        print(f"  {inst}")
        for acct in accounts:
            avail = acct["available"]
            curr  = acct["current"]
            avail_str = f"${avail:>9,.2f}" if avail is not None else "       n/a"
            curr_str  = f"${curr:>9,.2f}"  if curr  is not None else "       n/a"
            print(f"    {acct['name']:<28}  avail {avail_str}  curr {curr_str}")
    print(f"  {'TOTAL AVAILABLE':<28}        ${total_avail:>9,.2f}")

    income_hits  = [h for h in recurring_hits if h["amount"] < 0]
    expense_hits = [h for h in recurring_hits if h["amount"] >= 0]
    variable_14  = avg_daily * 14

    print(f"\n{'─'*W}")
    print(f"  14-DAY OUTLOOK  ({TODAY} → {HORIZON})")
    print(f"{'─'*W}")

    if income_hits:
        print("\n  INCOME EXPECTED")
        for h in income_hits:
            note = "  (est.)" if "Ben Williams" in h["name"] else ""
            print(f"    {h['date']}  {h['name']:<26}  +${abs(h['amount']):>8,.2f}{note}")

    if expense_hits:
        print("\n  BILLS DUE")
        for h in expense_hits:
            print(f"    {h['date']}  {h['name']:<26}   ${h['amount']:>8,.2f}")

    if cal_events:
        print("\n  CALENDAR (one-off)")
        for e in cal_events:
            print(f"    {e['date']}  {e['name']:<26}   ${e['amount']:>8,.2f}")

    print(f"\n  VARIABLE SPEND  (${avg_daily:.2f}/day × 14 = ${variable_14:,.2f})")
    for label, data in buckets.items():
        print(f"    {label:<22} ${data['daily']:>6.2f}/day   (${data['total']:>8,.2f}/30d)")

    recurring_net = sum(h["amount"] for h in recurring_hits)
    cal_net       = sum(e["amount"] for e in cal_events)
    projected     = total_avail - recurring_net - variable_14 - cal_net

    print(f"\n{'─'*W}")
    print(f"  Projected balance in 14 days              ${projected:>9,.2f}")
    print(f"{'─'*W}\n")

    if projected < 200:
        print("  ⚠️  Low — consider Zelle transfer between accounts.\n")


def build_telegram_message(balances: dict, total_avail: float, recurring_hits: list[dict],
                           cal_events: list[dict], avg_daily: float, buckets: dict) -> str:
    lines = [f"💰 Money Status — {TODAY}"]
    for inst, accounts in balances.items():
        for acct in accounts:
            avail = acct["available"]
            curr  = acct["current"]
            val   = avail if avail is not None else curr
            lines.append(f"  {inst} / {acct['name']}: ${val:,.2f}")
    lines.append(f"  Total available: ${total_avail:,.2f}")

    income_hits  = [h for h in recurring_hits if h["amount"] < 0]
    expense_hits = [h for h in recurring_hits if h["amount"] >= 0]
    variable_14  = avg_daily * 14

    if income_hits:
        lines.append("\n📥 Income (14 days):")
        for h in income_hits:
            note = " (est.)" if "Ben Williams" in h["name"] else ""
            lines.append(f"  {h['date']}  {h['name']}: +${abs(h['amount']):,.2f}{note}")

    if expense_hits:
        lines.append("\n📤 Bills due:")
        for h in expense_hits:
            lines.append(f"  {h['date']}  {h['name']}: ${h['amount']:,.2f}")

    if cal_events:
        lines.append("\n📅 Calendar:")
        for e in cal_events:
            lines.append(f"  {e['date']}  {e['name']}: ${e['amount']:,.2f}")

    lines.append(f"\n📊 Variable spend (${avg_daily:.2f}/day avg):")
    for label, data in buckets.items():
        lines.append(f"  {label}  ${data['daily']:.2f}/day")

    recurring_net = sum(h["amount"] for h in recurring_hits)
    cal_net       = sum(e["amount"] for e in cal_events)
    projected     = total_avail - recurring_net - variable_14 - cal_net

    lines.append(f"\n  14d variable est: ${variable_14:,.2f}")
    lines.append(f"📈 Projected in 14 days: ${projected:,.2f}")

    if projected < 200:
        lines.append("⚠️ Low balance — consider Zelle transfer.")

    return "\n".join(lines)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    init_db()

    print("Syncing latest transactions...")
    sync_transactions()

    # Stale data check — warn if newest transaction is more than 2 days old
    conn = get_conn()
    latest = conn.execute("SELECT MAX(date) FROM transactions").fetchone()[0]
    conn.close()
    if latest:
        days_old = (TODAY - date.fromisoformat(latest)).days
        if days_old > 2:
            print(f"\n  ⚠️  STALE DATA: most recent transaction is {days_old} days old ({latest}).")
            print("      Plaid may need re-auth. Run: .venv/bin/python3 scripts/plaid_link.py\n")

    print("\nFetching live balances...")
    balances, total_avail = fetch_balances()

    conn = get_conn()
    bills = [dict(r) for r in conn.execute(
        "SELECT * FROM recurring_bills WHERE active = 1"
    ).fetchall()]
    conn.close()

    recurring_hits = hits_in_window(bills)
    cal_events     = calendar_money_events()
    buckets        = variable_spend_by_bucket(bills)
    avg_daily      = sum(b["daily"] for b in buckets.values())

    print_report(balances, total_avail, recurring_hits, cal_events, avg_daily, buckets)
    msg = build_telegram_message(balances, total_avail, recurring_hits, cal_events, avg_daily, buckets)
    telegram_send(msg)


if __name__ == "__main__":
    main()
