# Zoho Books -> Odoo 19 Community One-shot Migrator

Runnable Python package for one-shot migration from Zoho Books to a self-hosted Odoo 19 Community instance using direct API integration:

`Zoho Books API -> Python -> Odoo XML-RPC API`

## Features (V1)

- Zoho OAuth refresh-token authentication flow
- EU-friendly defaults (fully configurable)
- Odoo XML-RPC client abstraction (authenticate/search/create/update)
- Functional end-to-end sync for:
  - Contacts -> `res.partner`
  - Items/Products -> `product.template`
- Idempotency safeguards:
  - Local Zoho->Odoo ID mapping file
  - Existing-record matching rules before create
- Pagination for Zoho list APIs
- HTTP retry handling
- Dry-run mode
- Clear logging and validation errors
- Safe defaults (no destructive deletes)

Code structure keeps room for later invoice/estimate modules.

## Project structure

- `/requirements.txt`
- `/.env.example`
- `/main.py`
- `/migrator/config.py`
- `/migrator/logging_utils.py`
- `/migrator/state_store.py`
- `/migrator/zoho_client.py`
- `/migrator/odoo_client.py`
- `/migrator/mappers/partners.py`
- `/migrator/mappers/products.py`
- `/migrator/sync/partners.py`
- `/migrator/sync/products.py`

## Requirements

- Python 3.10+
- Network access from runner to:
  - Zoho Books endpoints
  - Odoo host (`http://192.168.20.106:8069/` or your override)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1. Copy example env file:

```bash
cp .env.example .env
```

2. Fill required variables in `.env`:

- `ZOHO_CLIENT_ID`
- `ZOHO_CLIENT_SECRET`
- `ZOHO_REFRESH_TOKEN`
- `ZOHO_ORGANIZATION_ID`
- `ODOO_USERNAME`
- `ODOO_PASSWORD`

Defaults already set for your context:

- `ZOHO_DATA_CENTER=eu`
- `ZOHO_ACCOUNTS_URL=https://accounts.zoho.eu/oauth/v2/token`
- `ZOHO_API_BASE_URL=https://www.zohoapis.eu/books/v3`
- `ODOO_URL=http://192.168.20.106:8069/`
- `ODOO_DB=odoo`

All values remain configurable.

> ⚠️ Security note: the default `ODOO_URL` uses `http://` to match your local self-hosted setup request. Use `https://` whenever traffic is not strictly confined to a trusted internal network.

## Usage

### Dry run contacts

```bash
python main.py --module contacts --dry-run --log-level DEBUG
```

### Dry run products with limit

```bash
python main.py --module products --dry-run --limit 50
```

### Run full one-shot sync (contacts + products)

```bash
python main.py --module all --log-level INFO
```

CLI options:

- `--module contacts|products|all`
- `--dry-run`
- `--limit N`
- `--log-level INFO|DEBUG|WARNING|ERROR`
- `--dotenv-path /path/to/.env`

## Matching and idempotency behavior

### Contacts

Matching order:

1. Existing local mapping (Zoho contact ID -> Odoo partner ID)
2. Odoo partner by email
3. Odoo partner by exact name

Then create or update according to flags:

- `SYNC_CONTACTS_CREATE_MISSING=true|false`
- `SYNC_CONTACTS_UPDATE_EXISTING=true|false`

### Products

Matching order:

1. Existing local mapping (Zoho item ID -> Odoo product ID)
2. Odoo product by `default_code` (SKU/internal reference)
3. Odoo product by exact name

Then create or update according to flags:

- `SYNC_PRODUCTS_CREATE_MISSING=true|false`
- `SYNC_PRODUCTS_UPDATE_EXISTING=true|false`

## State file

The state file stores mappings and is configurable with:

- `STATE_FILE_PATH` (default: `state/mappings.json`)

It is written only when not in dry-run mode.

## Notes

- No deletes are performed.
- V1 covers contacts and products only.
- The package is structured for later invoice/estimate sync modules.
- It is designed for Odoo 19 Community and should also work on nearby versions exposing the same XML-RPC models/fields.
