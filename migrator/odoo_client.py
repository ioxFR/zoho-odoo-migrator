from __future__ import annotations

import logging
import xmlrpc.client
from typing import Any

from migrator.config import Config

logger = logging.getLogger(__name__)


class OdooClient:
    def __init__(self, config: Config):
        self.config = config
        base = config.odoo_url.rstrip("/")
        self._common = xmlrpc.client.ServerProxy(f"{base}/xmlrpc/2/common", allow_none=True)
        self._object = xmlrpc.client.ServerProxy(f"{base}/xmlrpc/2/object", allow_none=True)
        self.uid: int | None = None

    def authenticate(self) -> None:
        try:
            uid = self._common.authenticate(
                self.config.odoo_db,
                self.config.odoo_username,
                self.config.odoo_password,
                {},
            )
        except Exception as exc:
            raise RuntimeError(f"Odoo authentication request failed: {exc}") from exc
        if not uid:
            raise RuntimeError("Odoo authentication failed. Check ODOO_URL, ODOO_DB, ODOO_USERNAME, and ODOO_PASSWORD")
        self.uid = int(uid)

    def _exec(self, model: str, method: str, *args: Any, **kwargs: Any) -> Any:
        if self.uid is None:
            self.authenticate()
        return self._object.execute_kw(
            self.config.odoo_db,
            self.uid,
            self.config.odoo_password,
            model,
            method,
            list(args),
            kwargs,
        )

    def search(self, model: str, domain: list[list[Any]], limit: int | None = None) -> list[int]:
        kwargs: dict[str, Any] = {}
        if limit is not None:
            kwargs["limit"] = limit
        return self._exec(model, "search", domain, **kwargs)

    def search_read(
        self,
        model: str,
        domain: list[list[Any]],
        fields: list[str],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"fields": fields}
        if limit is not None:
            kwargs["limit"] = limit
        return self._exec(model, "search_read", domain, **kwargs)

    def create(self, model: str, values: dict[str, Any]) -> int:
        return int(self._exec(model, "create", values))

    def write(self, model: str, record_id: int, values: dict[str, Any]) -> bool:
        return bool(self._exec(model, "write", [record_id], values))

    def exists(self, model: str, record_id: int) -> bool:
        ids = self.search(model, [["id", "=", record_id]], limit=1)
        return bool(ids)
