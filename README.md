# Brazos GPMS Integration

Mapping-scoped **PostgreSQL cache** for [GPMS Foresight](https://apimx.gpms-vt.com): background jobs poll GPMS for **active mapped** aircraft only, store HUMS health and FDM exportstates, and expose **read-mostly REST** for Brazos analysts and the operator portal.

**This service does not poll all GPMS fleet aircraft** — only GPMS asset IDs in `gpms_asset_mappings` where `is_active = true`.

## What it does

| Layer | Behavior |
|-------|----------|
| **Background jobs** | Two independent polls every **10 minutes** (default): HUMS health per mapped asset; FDM incremental flight ingest + CSV parse |
| **PostgreSQL** | Cache for mappings, HUMS current + snapshots, FDM operations (raw CSV), parsed state samples, ingest cursors, GPMS JWT |
| **REST API** | Serves cached data to analysts/tools; **no live GPMS** on GET (except optional manual ingest POST) |
| **Portal** | Static UI at `/` — calls this API only, never GPMS directly |

## Architecture

```
gpms_asset_mappings (is_active=true)
        │
        ├─► HUMS poll (every 10m)
        │     GET /user/assets/{id}  per mapped ID
        │     → hums_status_current, hums_status_snapshots
        │
        └─► FDM poll (every 10m; also once at scheduler start)
              First run: GET .../operations?limit=500  (backfill)
              Later:     GET .../newimports?start=...  (incremental)
              Per new op: GET .../exportstates/{opId} → raw_csv + fdm_state_samples
              → fdm_operations, fdm_state_samples, fdm_ingest_cursors

PostgreSQL  →  GET /api/hums, /api/aircraft, /api/fdm/..., /api/events/critical
Portal /    →  same REST paths (cached reads)
```

### HUMS vs FDM (separate pipelines)

- **HUMS** — MD/RTB status, mdmax, rtbhealth, last operation date. Does **not** download flights or CSV.
- **FDM** — Flight operations + exportstates CSV, parsed into ~36 columns per sample row. Does **not** re-fetch all operations every cycle after backfill.

### FDM ingest strategy

1. **Backfill** (until `fdm_ingest_cursors.backfill_complete`): list up to `FDM_OPERATIONS_FETCH_LIMIT` (default **500**) operations per mapped asset.
2. **Incremental**: `GET /user/assets/{id}/newimports` since `last_checked_at`.
3. **Per operation**: skip if already in `fdm_operations`; else download CSV, store `raw_csv`, parse into `fdm_state_samples`.

### Startup sequence

On `uvicorn app.main:app`:

1. Alembic migrations (`init_db`)
2. Idempotent seed (`app/seed.py` — default mapping 223 → N407NW)
3. Ensure GPMS JWT (`gpms_auth_tokens`)
4. **One immediate HUMS poll**
5. APScheduler: HUMS + FDM every 10m; FDM **also runs immediately**; token renewal weekly

Manual one-shot polls: `python scripts/run_poll_once.py`

## Local setup

### Option A — Docker Postgres (recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set GPMS_EMAIL and GPMS_PASSWORD

chmod +x scripts/setup_local_postgres.sh
./scripts/setup_local_postgres.sh

uvicorn app.main:app --reload --port 8080
```

`docker-compose.yml` runs Postgres 16:

| Setting | Value |
|---------|--------|
| Host | `localhost:5432` |
| Database | `brazos_gpms` |
| User / password | `brazos` / `brazos` |

`DATABASE_URL` in `.env`:

```text
postgresql+psycopg2://brazos:brazos@localhost:5432/brazos_gpms
```

### Option B — Homebrew Postgres

```bash
brew install postgresql@16
brew services start postgresql@16
createdb brazos_gpms

# In .env, e.g.:
# DATABASE_URL=postgresql+psycopg2://$(whoami)@localhost:5432/brazos_gpms

alembic upgrade head
python scripts/seed_mappings.py
uvicorn app.main:app --reload --port 8080
```

Migrations also run automatically on app startup.

## Default mapping

| gpms_asset_id | brazos_tail_number |
|---------------|-------------------|
| 223 | N407NW |

Add more in `app/seed.py`, `python scripts/seed_mappings.py`, or `POST /api/admin/mappings`.

## Database tables

| Table | Purpose |
|-------|---------|
| `customers` | Multi-tenant customers; `uses_gpms` gates customer-scoped routes |
| `gpms_asset_mappings` | GPMS asset ID ↔ Brazos tail; **poll scope** |
| `gpms_auth_tokens` | Cached GPMS JWT (single row) |
| `hums_status_current` | Latest HUMS per mapped asset |
| `hums_status_snapshots` | Append-only history on each HUMS poll (**no read API yet**) |
| `fdm_operations` | Ingested flights + `raw_csv` |
| `fdm_state_samples` | Parsed exportstates rows (~2s samples) |
| `fdm_ingest_cursors` | Per-asset backfill / incremental poll state |

## REST API (analyst integration)

**Read endpoints use Postgres only** — safe for dashboards and integrations without hitting GPMS rate limits.

**Live GPMS** is used by: background jobs, `POST .../ingest`, and token refresh.

There is **no API authentication** in the current build; protect at the network/reverse-proxy layer in production.

### Interactive docs

| URL | Description |
|-----|-------------|
| [http://localhost:8080/](http://localhost:8080/) | Operator portal (HTML) |
| [http://localhost:8080/docs](http://localhost:8080/docs) | Swagger UI |
| [http://localhost:8080/redoc](http://localhost:8080/redoc) | ReDoc |
| [http://localhost:8080/openapi.json](http://localhost:8080/openapi.json) | OpenAPI 3 schema |

### Routes

| Method | Path | Source | Description |
|--------|------|--------|-------------|
| GET | `/health` | — | API + DB connectivity |
| GET | `/api/mappings` | DB | Active GPMS ↔ Brazos mappings |
| GET | `/api/aircraft` | DB | Mapped aircraft: HUMS fields + ingested flight count |
| GET | `/api/aircraft/{asset_id}` | DB | One mapped aircraft |
| GET | `/api/hums` | DB | HUMS for all active mappings (`pending` if never polled) |
| GET | `/api/customers/{id}/hums` | DB | HUMS for one customer (`uses_gpms` required) |
| GET | `/api/events/critical` | DB | MD or RTB `alarm` for mapped aircraft |
| GET | `/api/customers/{id}/events/critical` | DB | Critical events for one customer |
| GET | `/api/fdm/aircraft` | DB | Same summary as `/api/aircraft` |
| GET | `/api/fdm/aircraft/{id}` | DB | Mapped aircraft detail |
| GET | `/api/fdm/aircraft/{id}/operations` | DB | Ingested flights, newest first |
| GET | `/api/fdm/aircraft/{id}/operations/{opId}/exportstates` | DB | Parsed rows + CSV metadata |
| GET | `/api/fdm/aircraft/{id}/operations/{opId}/exportstates/raw` | DB | Full stored CSV text |
| GET | `/api/fdm/aircraft/{id}/operations/{opId}/states` | DB | Paginated samples (`full=true` for 36 cols) |
| POST | `/api/fdm/aircraft/{id}/operations/{opId}/ingest` | **GPMS** | On-demand ingest (idempotent) |
| POST | `/api/admin/customers` | DB | Create customer |
| PATCH | `/api/admin/customers/{id}/gpms` | DB | Enable/disable GPMS for customer |
| GET | `/api/admin/mappings` | DB | All mappings (incl. inactive) |
| GET | `/api/admin/customers/{id}/mappings` | DB | Mappings for customer |
| POST | `/api/admin/mappings` | DB | Create mapping |

Unmapped `asset_id` values return **404** on FDM routes.

## Operator portal

Served at `/` (`app/static/`). Loads:

- Critical events → `GET /api/events/critical`
- Mappings → `GET /api/mappings`
- HUMS table → `GET /api/hums` (+ operation counts from `/api/fdm/aircraft`)
- FDM explorer → `/api/fdm/aircraft/{id}`, operations, `exportstates`, raw CSV download

Click a HUMS row to drill into FDM for that asset. All times shown as **UTC**.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GPMS_BASE_URL` | `https://apimx.gpms-vt.com` | GPMS API base |
| `GPMS_EMAIL` / `GPMS_PASSWORD` | — | Required for polls and ingest |
| `DATABASE_URL` | local Postgres URL | **PostgreSQL only** (no SQLite) |
| `HUMS_POLL_INTERVAL_SECONDS` | `600` | HUMS background job |
| `FDM_POLL_INTERVAL_SECONDS` | `600` | FDM background job |
| `GPMS_TOKEN_RENEWAL_DAYS` | `7` | Proactive JWT refresh interval |
| `FDM_OPERATIONS_FETCH_LIMIT` | `500` | Max operations per asset on first FDM backfill |
| `GPMS_PORTAL_ASSET_URL` | empty | Optional `format(asset_id=...)` link in HUMS JSON |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_local_postgres.sh` | Docker Postgres + migrations + seed |
| `scripts/seed_mappings.py` | Idempotent mapping seed |
| `scripts/run_poll_once.py` | Run HUMS + FDM poll once (no scheduler wait) |

## Inspect data

```bash
docker compose exec postgres psql -U brazos -d brazos_gpms -c \
  "SELECT gpms_asset_id, brazos_tail_number, is_active FROM gpms_asset_mappings;"
```

```sql
-- HUMS cache vs mappings
SELECT m.gpms_asset_id, m.brazos_tail_number, h.mdstatus, h.rtbstatus, h.polled_at
FROM gpms_asset_mappings m
LEFT JOIN hums_status_current h ON h.gpms_asset_id = m.gpms_asset_id
WHERE m.is_active;

-- FDM ingest progress
SELECT gpms_asset_id, last_checked_at, backfill_complete
FROM fdm_ingest_cursors;

SELECT COUNT(*) FROM fdm_operations WHERE gpms_asset_id = 223;
```

## Time zones

All timestamps are stored and returned as **UTC** (`DateTime(timezone=True)` in Postgres; API JSON with `Z` suffix).

## Tests

Requires local Postgres (same as dev, or set `TEST_DATABASE_URL`):

```bash
pytest
```

## GPMS client endpoints used

| GPMS path | Used by |
|-----------|---------|
| `POST /auth/user` | Token manager |
| `GET /user/assets/{id}` | HUMS poll |
| `GET /user/assets/{id}/operations` | FDM backfill |
| `GET /user/assets/{id}/newimports` | FDM incremental poll |
| `GET /user/assets/{id}/exportstates/{opId}` | FDM ingest |
| `GET /user/assets/{id}/operations/{opId}` | Manual ingest metadata |
| `GET /user/fleets` | **Not used** (helpers exist in `GpmsClient` only) |

## Known limitations

- Poll scope is **mapped + active** tails only — not entire GPMS fleet discovery.
- FDM backfill is capped at `FDM_OPERATIONS_FETCH_LIMIT` operations per asset; older flights beyond that window are not auto-ingested unless you use `POST .../ingest`.
- `hums_status_snapshots` are written every poll but not exposed via API.
- Admin and read APIs have **no authentication** — add before production exposure.
- Critical events include **`alarm` only** (not warning-level statuses).
