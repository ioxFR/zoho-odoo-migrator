from __future__ import annotations

import logging
from typing import Any, Iterator

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from migrator.config import Config

logger = logging.getLogger(__name__)


class ZohoClient:
    def __init__(self, config: Config):
        self.config = config
        self.access_token: str | None = None
        self.api_base_url = config.zoho_api_base_url.rstrip("/")

        self.session = requests.Session()
        retry = Retry(
            total=config.http_retry_total,
            connect=config.http_retry_total,
            read=config.http_retry_total,
            status=config.http_retry_total,
            backoff_factor=config.http_retry_backoff_factor,
            allowed_methods=frozenset({"GET", "POST"}),
            status_forcelist=(429, 500, 502, 503, 504),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    @staticmethod
    def _safe_json(response: Response, context: str) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:
            body = (response.text or "").strip()
            snippet = body[:500]
            raise RuntimeError(
                f"{context}: expected JSON response but got status={response.status_code}, body={snippet!r}"
            ) from exc

    def refresh_access_token(self) -> None:
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.config.zoho_client_id,
            "client_secret": self.config.zoho_client_secret,
            "refresh_token": self.config.zoho_refresh_token,
        }
        response = self.session.post(
            self.config.zoho_accounts_url,
            data=payload,
            timeout=self.config.http_timeout_seconds,
        )
        data = self._safe_json(response, "Zoho OAuth refresh failed")
        if response.status_code >= 400 or "access_token" not in data:
            raise RuntimeError(f"Zoho OAuth refresh failed ({response.status_code}): {data}")

        self.access_token = data["access_token"]
        api_domain = data.get("api_domain")
        if api_domain:
            self.api_base_url = f"{api_domain.rstrip('/')}/books/v3"

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            self.refresh_access_token()
        return {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        params = dict(params)
        params["organization_id"] = self.config.zoho_organization_id
        url = f"{self.api_base_url}/{path.lstrip('/')}"
        response = self.session.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=self.config.http_timeout_seconds,
        )

        if response.status_code == 401:
            logger.info("Zoho token expired, refreshing and retrying once")
            self.refresh_access_token()
            response = self.session.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self.config.http_timeout_seconds,
            )

        data = self._safe_json(response, f"Zoho API request failed for {path}")
        if response.status_code >= 400:
            raise RuntimeError(f"Zoho API request failed ({response.status_code}) for {path}: {data}")
        return data

    def _paginate(self, path: str, key: str, limit: int | None = None) -> Iterator[dict[str, Any]]:
        page = 1
        yielded = 0

        while True:
            payload = self._get(
                path,
                {
                    "page": page,
                    "per_page": self.config.zoho_page_size,
                },
            )
            items = payload.get(key, [])
            for item in items:
                yield item
                yielded += 1
                if limit is not None and yielded >= limit:
                    return

            page_context = payload.get("page_context") or {}
            has_more = bool(page_context.get("has_more_page"))
            if not has_more:
                return
            page += 1

    def list_contacts(self, limit: int | None = None) -> Iterator[dict[str, Any]]:
        return self._paginate("contacts", "contacts", limit=limit)

    def list_items(self, limit: int | None = None) -> Iterator[dict[str, Any]]:
        return self._paginate("items", "items", limit=limit)
