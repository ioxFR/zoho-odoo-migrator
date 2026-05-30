from __future__ import annotations

import logging
from typing import Any

from migrator.config import Config
from migrator.mappers.products import map_zoho_item_to_odoo_product
from migrator.odoo_client import OdooClient
from migrator.state_store import StateStore
from migrator.zoho_client import ZohoClient

logger = logging.getLogger(__name__)


def _find_existing_product(odoo: OdooClient, mapped_id: int | None, values: dict[str, Any]) -> int | None:
    if mapped_id and odoo.exists("product.template", mapped_id):
        return mapped_id

    default_code = values.get("default_code")
    if default_code:
        by_default_code = odoo.search_read(
            "product.template",
            [["default_code", "=", default_code]],
            ["id"],
            limit=1,
        )
        if by_default_code:
            return int(by_default_code[0]["id"])

    name = values.get("name")
    if name:
        by_name = odoo.search_read("product.template", [["name", "=", name]], ["id"], limit=1)
        if by_name:
            return int(by_name[0]["id"])

    return None


def sync_products(
    config: Config,
    zoho: ZohoClient,
    odoo: OdooClient,
    state: StateStore,
    dry_run: bool,
    limit: int | None = None,
) -> dict[str, int]:
    summary = {"processed": 0, "created": 0, "updated": 0, "skipped": 0}

    for item in zoho.list_items(limit=limit):
        summary["processed"] += 1
        zoho_id = str(item.get("item_id") or "")
        if not zoho_id:
            logger.warning("Skipping item without item_id: %s", item)
            summary["skipped"] += 1
            continue

        values = map_zoho_item_to_odoo_product(item)
        existing_id = _find_existing_product(odoo, state.get_product_mapping(zoho_id), values)

        if existing_id:
            if not dry_run:
                state.set_product_mapping(zoho_id, existing_id)

            if config.sync_products_update_existing:
                if dry_run:
                    logger.info("[DRY-RUN] Would update item %s -> product.template(%s)", zoho_id, existing_id)
                else:
                    odoo.write("product.template", existing_id, values)
                    logger.info("Updated item %s -> product.template(%s)", zoho_id, existing_id)
                summary["updated"] += 1
            else:
                logger.info("Skipping update for item %s (updates disabled)", zoho_id)
                summary["skipped"] += 1
            continue

        if not config.sync_products_create_missing:
            logger.info("Skipping create for item %s (creates disabled)", zoho_id)
            summary["skipped"] += 1
            continue

        if dry_run:
            logger.info("[DRY-RUN] Would create product.template from item %s", zoho_id)
            summary["created"] += 1
            continue

        new_id = odoo.create("product.template", values)
        state.set_product_mapping(zoho_id, new_id)
        logger.info("Created product.template(%s) from item %s", new_id, zoho_id)
        summary["created"] += 1

    return summary
