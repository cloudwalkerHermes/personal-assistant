import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from core.config import GOOGLE_CREDENTIALS_FILE

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_FILE = "token.json"


def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8766)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def get_or_create_calendar(service, name: str = "Bills & Recurring") -> str:
    """Returns calendar ID, creating it if it doesn't exist."""
    calendars = service.calendarList().list().execute().get("items", [])
    for cal in calendars:
        if cal["summary"] == name:
            return cal["id"]
    created = service.calendars().insert(body={"summary": name, "timeZone": "America/Chicago"}).execute()
    return created["id"]


def upsert_bill_event(service, calendar_id: str, bill: dict):
    """Creates or updates a recurring calendar event for a bill or income."""
    from datetime import date, timedelta
    import calendar as cal_mod

    amount   = bill["amount"]
    freq     = bill.get("frequency", "monthly")
    due_day  = bill["due_day"]
    today    = date.today()
    is_income = amount < 0

    if is_income:
        title = f"💰 {bill['name']} — +${abs(amount):.2f}"
    else:
        title = f"💳 {bill['name']} — ${amount:.2f}"

    # Build RRULE and start date based on frequency
    if freq == "monthly_2nd_wed":
        rrule = "RRULE:FREQ=MONTHLY;BYDAY=2WE"
        # Find next 2nd Wednesday
        def nth_wed(y, m):
            d = date(y, m, 1)
            d += timedelta(days=(2 - d.weekday()) % 7)  # first Wednesday
            return d + timedelta(weeks=1)                # second Wednesday
        year, month = today.year, today.month
        start_date = nth_wed(year, month)
        if start_date < today:
            month = month + 1 if month < 12 else 1
            year  = year if month > 1 else year + 1
            start_date = nth_wed(year, month)

    elif freq == "weekly":
        rrule = "RRULE:FREQ=WEEKLY"
        start_date = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

    else:  # monthly (default)
        rrule = f"RRULE:FREQ=MONTHLY;BYMONTHDAY={due_day}"
        year, month = today.year, today.month
        last_day = cal_mod.monthrange(year, month)[1]
        start_date = date(year, month, min(due_day, last_day))
        if start_date < today:
            month = month + 1 if month < 12 else 1
            year  = year if month > 1 else year + 1
            last_day = cal_mod.monthrange(year, month)[1]
            start_date = date(year, month, min(due_day, last_day))

    event_body = {
        "summary": title,
        "description": f"Recurring bill: {bill['name']}",
        "start": {"date": str(start_date)},
        "end": {"date": str(start_date)},
        "recurrence": [rrule],
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 1440}],  # 1 day before
        },
    }

    # Check if event already exists (search by title)
    existing = service.events().list(
        calendarId=calendar_id,
        q=bill["name"],
        singleEvents=False,
    ).execute().get("items", [])

    existing_match = next((e for e in existing if bill["name"].lower() in e.get("summary", "").lower()), None)

    if existing_match:
        service.events().update(
            calendarId=calendar_id,
            eventId=existing_match["id"],
            body=event_body,
        ).execute()
        return "updated"
    else:
        service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return "created"
