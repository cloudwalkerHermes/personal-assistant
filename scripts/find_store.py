from integrations.kroger.client import KrogerClient

c = KrogerClient()
data = c._get("/locations", {
    "filter.zipCode": "75460",
    "filter.radiusInMiles": "25",
    "filter.limit": "10",
})
for store in data.get("data", []):
    addr = store.get("address", {})
    print(f"{store['locationId']}  {store['name']}  {addr.get('addressLine1')}  {addr.get('city')}, {addr.get('state')}")
