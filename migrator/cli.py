from __future__ import annotations

import argparse
import logging
from typing import Iterable

from migrator.config import load_config
from migrator.logging_utils import configure_logging
from migrator.odoo_client import OdooClient
from migrator.state_store import StateStore
from migrator.sync.partners import sync_contacts
from migrator.sync.products import sync_products
from migrator.zoho_client import ZohoClient

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-shot Zoho Books -> Odoo migrator")
    parser.add_argument(
        "--module",
        choices=["contacts", "products", "all"],
        default="all",
        help="Migration module to run",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview operations without writing to Odoo/state")
    parser.add_argument("--limit", type=int, default=None, help="Max records per module")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    parser.add_argument(
        "--dotenv-path",
        default=None,
        help="Optional custom path to .env file",
    )
    return parser.parse_args()


def _run_modules(selected_module: str) -> Iterable[str]:
    if selected_module == "all":
        return ("contacts", "products")
    return (selected_module,)


def main() -> int:
    args = _parse_args()
    configure_logging(args.log_level)

    try:
        config = load_config(dotenv_path=args.dotenv_path)
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        return 2

    try:
        zoho = ZohoClient(config)
        odoo = OdooClient(config)
        odoo.authenticate()
        state = StateStore(config.state_file_path)

        logger.info("Starting migration: module=%s dry_run=%s limit=%s", args.module, args.dry_run, args.limit)

        for module_name in _run_modules(args.module):
            if module_name == "contacts":
                summary = sync_contacts(config, zoho, odoo, state, dry_run=args.dry_run, limit=args.limit)
            elif module_name == "products":
                summary = sync_products(config, zoho, odoo, state, dry_run=args.dry_run, limit=args.limit)
            else:
                raise ValueError(f"Unsupported module: {module_name}")

            logger.info("%s sync summary: %s", module_name, summary)

        if not args.dry_run:
            state.save()
            logger.info("State saved to %s", config.state_file_path)
        else:
            logger.info("Dry-run mode enabled: state file was not modified")

        return 0
    except KeyboardInterrupt:
        logger.error("Migration interrupted by user")
        return 130
    except Exception as exc:
        logger.exception("Migration failed: %s", exc)
        return 1
