from dataclasses import dataclass
from integrations.kroger.client import KrogerClient


@dataclass
class SaleItem:
    name: str
    brand: str
    regular_price: float | None
    sale_price: float | None
    savings: float | None
    size: str
    upc: str

    def savings_pct(self) -> float | None:
        if self.regular_price and self.sale_price:
            return round((1 - self.sale_price / self.regular_price) * 100, 1)
        return None

    def format_line(self) -> str:
        price_str = f"${self.sale_price:.2f}"
        if self.regular_price:
            price_str += f" (was ${self.regular_price:.2f}"
            pct = self.savings_pct()
            if pct:
                price_str += f", {pct}% off"
            price_str += ")"
        return f"• {self.brand} {self.name} {self.size} — {price_str}"


def _extract_sale(product: dict) -> SaleItem | None:
    items = product.get("items", [])
    if not items:
        return None

    item = items[0]
    price = item.get("price", {})
    regular = price.get("regular")
    promo = price.get("promo")

    if not promo or promo == regular:
        return None

    return SaleItem(
        name=product.get("description", ""),
        brand=product.get("brand", ""),
        regular_price=regular,
        sale_price=promo,
        savings=round(regular - promo, 2) if regular else None,
        size=item.get("size", ""),
        upc=product.get("upc", ""),
    )


def find_sales_for_items(item_names: list[str], location_id: str) -> list[SaleItem]:
    client = KrogerClient()
    sales = []
    seen_upcs = set()

    for name in item_names:
        products = client.search_products(name, location_id, limit=5)
        for product in products:
            upc = product.get("upc")
            if upc in seen_upcs:
                continue
            seen_upcs.add(upc)
            sale = _extract_sale(product)
            if sale:
                sales.append(sale)

    return sorted(sales, key=lambda s: s.savings_pct() or 0, reverse=True)
