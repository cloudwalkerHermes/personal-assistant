from integrations.kroger.client import KrogerClient

c = KrogerClient()
store = c.find_store("75460")
if store:
    print(store["name"], store["locationId"])
else:
    print("No store found")
