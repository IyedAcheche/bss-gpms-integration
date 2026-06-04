"""OpenAPI / Swagger metadata for the Brazos GPMS Integration API."""

API_DESCRIPTION = """
## Overview

Brazos GPMS Integration is a **PostgreSQL-backed cache** of GPMS Foresight data for Brazos Safety Systems analysts.

- **Background jobs** poll GPMS every **10 minutes** (configurable) for **mapped** GPMS asset IDs only (`gpms_asset_mappings`, `is_active=true`).
- **Read endpoints** return cached Postgres data — **not** live GPMS (except `POST .../ingest`).
- The **operator portal** at [GET /](/) uses the same REST API; it does not call GPMS directly.

This service does **not** discover or poll all aircraft in your GPMS account — only tails you map to Brazos.

## Two poll pipelines

### HUMS (health)

- **GPMS:** `GET /user/assets/{id}` per mapped asset
- **Stores:** `hums_status_current` (latest), `hums_status_snapshots` (append-only history; no read API yet)
- **Fields:** MD/RTB status, mdmax, rtbhealth, last operation date, asset name

Does **not** fetch operations or exportstates CSV.

### FDM (flights + exportstates)

- **Backfill** (first time per asset): `GET .../operations?limit=` up to `FDM_OPERATIONS_FETCH_LIMIT` (default 500)
- **Incremental** (after backfill): `GET .../newimports?start=` from `fdm_ingest_cursors`
- **Per new operation:** `GET .../exportstates/{operationId}` → `fdm_operations.raw_csv` + parsed `fdm_state_samples`

Already-ingested operations are skipped. Does **not** re-list all operations every poll.

## Mapping scope

Only aircraft in `gpms_asset_mappings` with `is_active=true` are polled and returned by
`/api/hums`, `/api/aircraft`, `/api/fdm/*`, and `/api/events/critical`.

Unmapped GPMS asset IDs return **404** on FDM routes.

## Data model

| Area | Tables |
|------|--------|
| Scope | `gpms_asset_mappings`, `customers` |
| Auth | `gpms_auth_tokens` |
| HUMS | `hums_status_current`, `hums_status_snapshots` |
| FDM | `fdm_operations`, `fdm_state_samples`, `fdm_ingest_cursors` |

## Analyst integration notes

- Use **GET** routes for dashboards and tools (cached, fast, no GPMS credentials needed on the client).
- Use **POST** `/api/fdm/aircraft/{asset_id}/operations/{operation_id}/ingest` to pull one flight from GPMS on demand (idempotent).
- Customer-scoped routes require `customers.uses_gpms=true`.
- **No API authentication** is implemented — protect the deployment at the network layer.

## Timestamps

All datetimes are **UTC** (JSON uses `Z` suffix).

## Interactive docs

- **Swagger UI:** [GET /docs](/docs)
- **ReDoc:** [GET /redoc](/redoc)
- **OpenAPI JSON:** [GET /openapi.json](/openapi.json)
"""

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Service and PostgreSQL connectivity (no GPMS call).",
    },
    {
        "name": "mappings",
        "description": "Active GPMS ↔ Brazos tail mappings — defines poll and API scope.",
    },
    {
        "name": "aircraft",
        "description": "Mapped aircraft summary from Postgres: cached HUMS + ingested FDM operation count.",
    },
    {
        "name": "hums",
        "description": "Health and Usage Monitoring (MD/RTB) from `hums_status_current`. Poll: GET /user/assets/{id}.",
    },
    {
        "name": "events",
        "description": "Critical HUMS alarms (MD or RTB status = `alarm`) for all mapped aircraft.",
    },
    {
        "name": "fdm",
        "description": "Flight Data Monitoring from Postgres: operations, parsed exportstates, raw CSV. Poll ingests via exportstates.",
    },
    {
        "name": "admin",
        "description": "Customers, mappings CRUD, GPMS enablement. No auth — dev/admin use only unless protected externally.",
    },
    {
        "name": "hums-customer",
        "description": "HUMS filtered by customer (`uses_gpms` required).",
    },
    {
        "name": "events-customer",
        "description": "Critical events filtered by customer.",
    },
    {
        "name": "portal",
        "description": "Static operator dashboard at GET / — reads cached API only.",
    },
]
