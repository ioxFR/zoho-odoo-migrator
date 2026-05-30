from __future__ import annotations

from typing import Any


def _clean(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v not in (None, "")}


def map_zoho_item_to_odoo_product(item: dict[str, Any]) -> dict[str, Any]:
    product_type = (item.get("product_type") or "").lower()
    detailed_type = "service" if product_type == "service" else "product"

    values = {
        "name": item.get("name") or item.get("item_name") or "Unnamed item",
        "default_code": item.get("sku"),
        "description_sale": item.get("description"),
        "list_price": item.get("rate") if item.get("rate") is not None else item.get("sales_rate"),
        "standard_price": item.get("purchase_rate"),
        "detailed_type": detailed_type,
        "sale_ok": True,
        "purchase_ok": True,
    }

    return _clean(values)
