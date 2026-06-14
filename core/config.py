import os
from dotenv import load_dotenv

load_dotenv()

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")

KROGER_SHOPPING_EMAIL = os.getenv("KROGER_SHOPPING_EMAIL")
KROGER_SHOPPING_PASSWORD = os.getenv("KROGER_SHOPPING_PASSWORD")

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

KROGER_CLIENT_ID = os.getenv("KROGER_CLIENT_ID")
KROGER_CLIENT_SECRET = os.getenv("KROGER_CLIENT_SECRET")

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

DB_PATH = os.getenv("DB_PATH", "personal-assistant.db")
