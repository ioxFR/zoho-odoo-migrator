from __future__ import annotations

import logging
from typing import Any

from migrator.config import Config
from migrator.mappers.partners import map_zoho_contact_to_odoo_partner
from migrator.odoo_client import OdooClient
from migrator.state_store import StateStore
from migrator.zoho_client import ZohoClient

logger = logging.getLogger(__name__)


def _find_existing_partner(odoo: OdooClient, mapped_id: int | None, values: dict[str, Any]) -> int | None:
    if mapped_id and odoo.exists("res.partner", mapped_id):
        return mapped_id

    email = values.get("email")
    if email:
        by_email = odoo.search_read("res.partner", [["email", "=ilike", email]], ["id"], limit=1)
        if by_email:
            return int(by_email[0]["id"])

    name = values.get("name")
    if name:
        by_name = odoo.search_read("res.partner", [["name", "=", name]], ["id"], limit=1)
        if by_name:
            return int(by_name[0]["id"])

    return None


def _resolve_country_id(odoo: OdooClient, values: dict[str, Any]) -> int | None:
    country_code = values.pop("_country_code", None)
    country_name = values.pop("_country_name", None)

    if country_code:
        rows = odoo.search_read("res.country", [["code", "=", country_code]], ["id"], limit=1)
        if rows:
            return int(rows[0]["id"])

    if country_name:
        rows = odoo.search_read("res.country", [["name", "=", country_name]], ["id"], limit=1)
        if rows:
            return int(rows[0]["id"])

    return None


def sync_contacts(
    config: Config,
    zoho: ZohoClient,
    odoo: OdooClient,
    state: StateStore,
    dry_run: bool,
    limit: int | None = None,
) -> dict[str, int]:
    summary = {"processed": 0, "created": 0, "updated": 0, "skipped": 0}

    for contact in zoho.list_contacts(limit=limit):
        summary["processed"] += 1
        zoho_id = str(contact.get("contact_id") or "")
        if not zoho_id:
            logger.warning("Skipping contact without contact_id: %s", contact)
            summary["skipped"] += 1
            continue

        values = map_zoho_contact_to_odoo_partner(contact)
        country_id = _resolve_country_id(odoo, values)
        if country_id:
            values["country_id"] = country_id

        existing_id = _find_existing_partner(odoo, state.get_partner_mapping(zoho_id), values)

        if existing_id:
            if not dry_run:
                state.set_partner_mapping(zoho_id, existing_id)

            if config.sync_contacts_update_existing:
                if dry_run:
                    logger.info("[DRY-RUN] Would update contact %s -> res.partner(%s)", zoho_id, existing_id)
                else:
                    odoo.write("res.partner", existing_id, values)
                    logger.info("Updated contact %s -> res.partner(%s)", zoho_id, existing_id)
                summary["updated"] += 1
            else:
                logger.info("Skipping update for contact %s (updates disabled)", zoho_id)
                summary["skipped"] += 1
            continue

        if not config.sync_contacts_create_missing:
            logger.info("Skipping create for contact %s (creates disabled)", zoho_id)
            summary["skipped"] += 1
            continue

        if dry_run:
            logger.info("[DRY-RUN] Would create res.partner from contact %s", zoho_id)
            summary["created"] += 1
            continue

        new_id = odoo.create("res.partner", values)
        state.set_partner_mapping(zoho_id, new_id)
        logger.info("Created res.partner(%s) from contact %s", new_id, zoho_id)
        summary["created"] += 1

    return summary
