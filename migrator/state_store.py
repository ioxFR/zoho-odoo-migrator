from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return {"partners": {}, "products": {}}
        with self.file_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        data.setdefault("partners", {})
        data.setdefault("products", {})
        return data

    def save(self) -> None:
        tmp_path = self.file_path.with_suffix(f"{self.file_path.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        tmp_path.replace(self.file_path)

    def get_partner_mapping(self, zoho_contact_id: str) -> int | None:
        value = self._data["partners"].get(str(zoho_contact_id))
        return int(value) if value is not None else None

    def set_partner_mapping(self, zoho_contact_id: str, odoo_partner_id: int) -> None:
        self._data["partners"][str(zoho_contact_id)] = int(odoo_partner_id)

    def get_product_mapping(self, zoho_item_id: str) -> int | None:
        value = self._data["products"].get(str(zoho_item_id))
        return int(value) if value is not None else None

    def set_product_mapping(self, zoho_item_id: str, odoo_product_id: int) -> None:
        self._data["products"][str(zoho_item_id)] = int(odoo_product_id)
