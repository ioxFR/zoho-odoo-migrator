from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    zoho_data_center: str
    zoho_client_id: str
    zoho_client_secret: str
    zoho_refresh_token: str
    zoho_organization_id: str
    zoho_accounts_url: str
    zoho_api_base_url: str
    zoho_page_size: int

    odoo_url: str
    odoo_db: str
    odoo_username: str
    odoo_password: str

    state_file_path: Path

    sync_contacts_create_missing: bool
    sync_contacts_update_existing: bool
    sync_products_create_missing: bool
    sync_products_update_existing: bool

    http_timeout_seconds: int
    http_retry_total: int
    http_retry_backoff_factor: float


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value for {name}: {value!r}")


def _default_zoho_accounts_url(data_center: str) -> str:
    return f"https://accounts.zoho.{data_center}/oauth/v2/token"


def _default_zoho_api_base_url(data_center: str) -> str:
    return f"https://www.zohoapis.{data_center}/books/v3"


def load_config(dotenv_path: str | None = None) -> Config:
    load_dotenv(dotenv_path=dotenv_path)

    data_center = os.getenv("ZOHO_DATA_CENTER", "eu").strip().lower()

    cfg = Config(
        zoho_data_center=data_center,
        zoho_client_id=os.getenv("ZOHO_CLIENT_ID", "").strip(),
        zoho_client_secret=os.getenv("ZOHO_CLIENT_SECRET", "").strip(),
        zoho_refresh_token=os.getenv("ZOHO_REFRESH_TOKEN", "").strip(),
        zoho_organization_id=os.getenv("ZOHO_ORGANIZATION_ID", "").strip(),
        zoho_accounts_url=os.getenv("ZOHO_ACCOUNTS_URL", _default_zoho_accounts_url(data_center)).strip(),
        zoho_api_base_url=os.getenv("ZOHO_API_BASE_URL", _default_zoho_api_base_url(data_center)).strip().rstrip("/"),
        zoho_page_size=int(os.getenv("ZOHO_PAGE_SIZE", "200")),
        odoo_url=os.getenv("ODOO_URL", "http://192.168.20.106:8069/").strip(),
        odoo_db=os.getenv("ODOO_DB", "odoo").strip(),
        odoo_username=os.getenv("ODOO_USERNAME", "").strip(),
        odoo_password=os.getenv("ODOO_PASSWORD", "").strip(),
        state_file_path=Path(os.getenv("STATE_FILE_PATH", "state/mappings.json")),
        sync_contacts_create_missing=_env_bool("SYNC_CONTACTS_CREATE_MISSING", True),
        sync_contacts_update_existing=_env_bool("SYNC_CONTACTS_UPDATE_EXISTING", True),
        sync_products_create_missing=_env_bool("SYNC_PRODUCTS_CREATE_MISSING", True),
        sync_products_update_existing=_env_bool("SYNC_PRODUCTS_UPDATE_EXISTING", True),
        http_timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", "30")),
        http_retry_total=int(os.getenv("HTTP_RETRY_TOTAL", "5")),
        http_retry_backoff_factor=float(os.getenv("HTTP_RETRY_BACKOFF_FACTOR", "1.0")),
    )

    missing = [
        name
        for name, value in (
            ("ZOHO_CLIENT_ID", cfg.zoho_client_id),
            ("ZOHO_CLIENT_SECRET", cfg.zoho_client_secret),
            ("ZOHO_REFRESH_TOKEN", cfg.zoho_refresh_token),
            ("ZOHO_ORGANIZATION_ID", cfg.zoho_organization_id),
            ("ODOO_USERNAME", cfg.odoo_username),
            ("ODOO_PASSWORD", cfg.odoo_password),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {joined}")

    if cfg.zoho_page_size < 1 or cfg.zoho_page_size > 200:
        raise ValueError("ZOHO_PAGE_SIZE must be between 1 and 200")
    if cfg.http_timeout_seconds < 1:
        raise ValueError("HTTP_TIMEOUT_SECONDS must be >= 1")
    if cfg.http_retry_total < 0:
        raise ValueError("HTTP_RETRY_TOTAL must be >= 0")

    return cfg
