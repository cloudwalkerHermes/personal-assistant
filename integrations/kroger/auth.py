import time
import base64
import requests
from core.db import get_conn
from core.config import KROGER_CLIENT_ID, KROGER_CLIENT_SECRET

BASE_URL = "https://api.kroger.com/v1"
REDIRECT_URI = "http://localhost:8000/callback"
SCOPES = "openid profile.compact cart.basic:write product.compact"


def get_auth_url() -> str:
    import urllib.parse
    params = urllib.parse.urlencode({
        "client_id": KROGER_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
    })
    return f"{BASE_URL}/connect/oauth2/authorize?{params}"


def _basic_header() -> str:
    return "Basic " + base64.b64encode(
        f"{KROGER_CLIENT_ID}:{KROGER_CLIENT_SECRET}".encode()
    ).decode()


def exchange_code(code: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/connect/oauth2/token",
        headers={
            "Authorization": _basic_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/connect/oauth2/token",
        headers={
            "Authorization": _basic_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    resp.raise_for_status()
    return resp.json()


def save_tokens(token_data: dict):
    conn = get_conn()
    conn.execute(
        """INSERT INTO oauth_tokens (service, access_token, refresh_token, expires_at)
           VALUES ('kroger', ?, ?, ?)
           ON CONFLICT(service) DO UPDATE SET
               access_token=excluded.access_token,
               refresh_token=excluded.refresh_token,
               expires_at=excluded.expires_at,
               updated_at=CURRENT_TIMESTAMP""",
        (
            token_data["access_token"],
            token_data.get("refresh_token"),
            int(time.time()) + token_data.get("expires_in", 1800),
        ),
    )
    conn.commit()
    conn.close()


def get_valid_token() -> str:
    conn = get_conn()
    row = conn.execute(
        "SELECT access_token, refresh_token, expires_at FROM oauth_tokens WHERE service='kroger'"
    ).fetchone()
    conn.close()

    if not row:
        raise RuntimeError("No Kroger token found. Run scripts/kroger_login.py first.")

    if time.time() < row["expires_at"] - 60:
        return row["access_token"]

    if row["refresh_token"]:
        token_data = refresh_access_token(row["refresh_token"])
        save_tokens(token_data)
        return token_data["access_token"]

    raise RuntimeError("Token expired and no refresh token. Run scripts/kroger_login.py again.")
