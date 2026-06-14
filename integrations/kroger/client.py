import time
import base64
import requests
from core.config import KROGER_CLIENT_ID, KROGER_CLIENT_SECRET

BASE_URL = "https://api.kroger.com/v1"


class KrogerClient:
    def __init__(self):
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        credentials = base64.b64encode(
            f"{KROGER_CLIENT_ID}:{KROGER_CLIENT_SECRET}".encode()
        ).decode()

        resp = requests.post(
            f"{BASE_URL}/connect/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": "product.compact"},
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"]
        return self._token

    def _get(self, path: str, params: dict = None) -> dict:
        resp = requests.get(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def find_store(self, zip_code: str) -> dict | None:
        data = self._get("/locations", {
            "filter.zipCode": zip_code,
            "filter.radiusInMiles": "10",
            "filter.limit": "1",
        })
        locations = data.get("data", [])
        return locations[0] if locations else None

    def search_products(self, term: str, location_id: str, limit: int = 10) -> list[dict]:
        data = self._get("/products", {
            "filter.term": term,
            "filter.locationId": location_id,
            "filter.limit": limit,
        })
        return data.get("data", [])
