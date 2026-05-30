from __future__ import annotations

from typing import Any


def _clean(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v not in (None, "")}


def map_zoho_contact_to_odoo_partner(contact: dict[str, Any]) -> dict[str, Any]:
    contact_persons = contact.get("contact_persons") or []
    first_person = contact_persons[0] if contact_persons else {}

    values = {
        "name": contact.get("contact_name") or contact.get("company_name") or "Unnamed contact",
        "email": contact.get("email") or first_person.get("email"),
        "phone": contact.get("phone") or first_person.get("phone"),
        "mobile": contact.get("mobile") or first_person.get("mobile"),
        "street": contact.get("billing_address", {}).get("address"),
        "street2": contact.get("billing_address", {}).get("street2"),
        "city": contact.get("billing_address", {}).get("city"),
        "zip": contact.get("billing_address", {}).get("zip"),
    }

    country = contact.get("billing_address", {}).get("country")
    country_code = contact.get("billing_address", {}).get("country_code")
    if country:
        values["_country_name"] = country
    if country_code:
        values["_country_code"] = country_code

    contact_type = (contact.get("contact_type") or "").lower()
    if contact_type == "customer":
        values["customer_rank"] = 1
    elif contact_type == "vendor":
        values["supplier_rank"] = 1

    return _clean(values)
