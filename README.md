# Brazos GPMS Integration

Mapping-scoped **PostgreSQL cache** for [GPMS Foresight](https://apimx.gpms-vt.com): background jobs poll GPMS for **active mapped** aircraft only, store HUMS health and FDM exportstates, and expose **read-mostly REST** for Brazos analysts and the operator portal.

**This service does not poll all GPMS fleet aircraft** — only GPMS asset IDs in `gpms_asset_mappings` where `is_active = true`.

## Documentation map

| Path | Contents |
|------|----------|
| **[`app/api/README.md`](app/api/README.md)** | Every route, handler, status codes, service wiring |
| **[`app/jobs/README.md`](app/jobs/README.md)** | Scheduler, poll cadence, startup sequence, transactions |
| **[`app/models/README.md`](app/models/README.md)** | Tables, columns, ER diagram, who reads/writes each |
| **[`app/schemas/README.md`](app/schemas/README.md)** | Pydantic response models, field sources, GPMS vs API types |
| **[`app/services/README.md`](app/services/README.md)** | GPMS client, token lock, HUMS/FDM ingest flows, CSV parsing |

Supporting modules (not separate READMEs): `app/main.py` (app factory + lifespan), `app/config.py`, `app/db.py`, `app/seed.py`, `app/time_utils.py`, `app/openapi_config.py`, `app/static/` (portal).

## Codebase layout

```
app/
├── main.py              # FastAPI app, lifespan, router registration, portal at /
├── config.py            # Settings from .env (Pydantic)
├── db.py                # Engine, SessionLocal, Alembic init_db()
├── seed.py              # Default customer + mapping (223 → N407NW)
├── openapi_config.py    # Swagger description + tags
├── time_utils.py        # UTC parsing/serialization for API
├── api/                 # REST routers → see app/api/README.md
├── jobs/                # APScheduler polls → see app/jobs/README.md
├── models/              # SQLAlchemy ORM → see app/models/README.md
├── schemas/             # Pydantic API contracts → see app/schemas/README.md
├── services/            # GPMS + business logic → see app/services/README.md
└── static/              # Operator portal (HTML/JS/CSS)

alembic/                 # Migrations (001_initial_schema)
scripts/                 # setup_local_postgres, seed_mappings, run_poll_once
tests/                   # pytest (mapping scope, CSV, status, time utils)
proxy/                   # nginx for docker-compose full profile
```

## Architecture (high level)

```
gpms_asset_mappings (is_active=true)
        │
        ├─► HUMS poll ──► hums_status_current, hums_status_snapshots
        │
        └─► FDM poll ──► fdm_operations, fdm_state_samples, fdm_ingest_cursors

PostgreSQL  ◄── GET /api/*  (cached reads)
Portal /    ◄── same REST (no direct GPMS)
```

- **HUMS** — MD/RTB health from `GET /user/assets/{id}`. No flights/CSV.
- **FDM** — Backfill operations list, then `newimports`; per op downloads exportstates CSV. Details: [`app/services/README.md`](app/services/README.md).

### Startup sequence

On `uvicorn app.main:app`:

1. Alembic migrations (`init_db`)
2. Idempotent seed (`app/seed.py` — default mapping 223 → N407NW for development purposes since there is no REAL mapping table available yet.)
3. Ensure GPMS JWT (`gpms_auth_tokens`)
4. **One immediate HUMS poll**
5. APScheduler: HUMS + FDM every 10m; FDM **also runs immediately**; token renewal weekly

Manual one-shot polls: `python scripts/run_poll_once.py`

## Quick reference

### REST API

Read endpoints use **Postgres only**. **Live GPMS:** background jobs, `POST .../ingest`, token refresh.

**No API authentication** in this build — protect at network/reverse-proxy in production.

| Docs | URL |
|------|-----|
| Swagger | http://localhost:8080/docs |
| ReDoc | http://localhost:8080/redoc |
| Portal | http://localhost:8080/ |

Route table and behavior: [`app/api/README.md`](app/api/README.md).

### Database tables

| Table | Purpose |
|-------|---------|
| `customers` | Multi-tenant; `uses_gpms` gates customer routes |
| `gpms_asset_mappings` | GPMS asset ↔ Brazos tail; **poll scope** |
| `gpms_auth_tokens` | Cached GPMS JWT (singleton) |
| `hums_status_current` | Latest HUMS per asset |
| `hums_status_snapshots` | Append-only history (**no read API yet**) |
| `fdm_operations` | Flights + `raw_csv` |
| `fdm_state_samples` | Parsed exportstates (~2s rows) |
| `fdm_ingest_cursors` | Per-asset backfill / incremental state |

Column-level detail: [`app/models/README.md`](app/models/README.md).

### Default mapping

| gpms_asset_id | brazos_tail_number |
|---------------|-------------------|
| 223 | N407NW |

Add via `app/seed.py`, `python scripts/seed_mappings.py`, or `POST /api/admin/mappings`.

## Local setup

### Option A — Docker Postgres + app on host (dev with reload)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set GPMS_EMAIL and GPMS_PASSWORD

chmod +x scripts/setup_local_postgres.sh
./scripts/setup_local_postgres.sh

uvicorn app.main:app --reload --port 8080
```

Postgres only:

```bash
docker compose up -d
```

| Setting | Value |
|---------|--------|
| Host (from Mac) | `localhost:5432` |
| Database | `brazos_gpms` |
| User / password | `brazos` / `brazos` |

`DATABASE_URL` when uvicorn runs on the host:

```text
postgresql+psycopg2://brazos:brazos@localhost:5432/brazos_gpms
```

### Option A2 — Docker Postgres + API + nginx

```bash
cp .env.example .env
# DATABASE_URL=postgresql+psycopg2://brazos:brazos@postgres:5432/brazos_gpms
# (see .env.docker.example)

chmod +x scripts/docker-up.sh
./scripts/docker-up.sh
```

Or: `docker compose --profile full up -d --build`

Stop host `uvicorn` on 8080 before starting Compose.

**VM / production (pull from Docker Hub):**

```bash
docker login
docker compose -f docker-compose.deploy.yml pull
docker compose -f docker-compose.deploy.yml up -d
```

Images: [`iyedacheche/brazos-gmps-app`](https://hub.docker.com/r/iyedacheche/brazos-gmps-app) — tags `app-latest` and `proxy-latest` (same repo). Pin a release: `BRAZOS_APP_IMAGE_TAG=app-sha-<short> BRAZOS_PROXY_IMAGE_TAG=proxy-sha-<short>`.

Local build on the server instead: `docker compose -f docker-compose.deploy.yml up -d --build`

### Docker Hub and CI/CD

| Item | Value |
|------|--------|
| Docker Hub repo | `iyedacheche/brazos-gmps-app` |
| App tag | `app-latest`, `app-sha-<git short sha>` |
| Proxy tag | `proxy-latest`, `proxy-sha-<git short sha>` |
| Postgres | `postgres:16-alpine` (official image, not published) |

**Manual push** (after `docker login`):

```bash
chmod +x scripts/docker-push.sh
./scripts/docker-push.sh          # pushes app-latest + proxy-latest
./scripts/docker-push.sh v0.2.0   # pushes app-v0.2.0 + proxy-v0.2.0
```

**GitHub Actions** (`.github/workflows/docker-publish.yml`):

- **Pull request → `main`:** `pytest` + Docker build (no push)
- **Push to `main`:** same tests, then push `app-latest` / `proxy-latest` and `app-sha-*` / `proxy-sha-*`

Add repository secrets: `DOCKERHUB_USERNAME` (`iyedacheche`), `DOCKERHUB_TOKEN` (Docker Hub access token).

### Option B — Homebrew Postgres

```bash
brew install postgresql@16
brew services start postgresql@16
createdb brazos_gpms

alembic upgrade head
python scripts/seed_mappings.py
uvicorn app.main:app --reload --port 8080
```

Migrations also run on app startup (`init_db`).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GPMS_BASE_URL` | `https://apimx.gpms-vt.com` | GPMS API base |
| `GPMS_EMAIL` / `GPMS_PASSWORD` | — | Required for polls and ingest |
| `DATABASE_URL` | local Postgres URL | **PostgreSQL only** |
| `HUMS_POLL_INTERVAL_SECONDS` | `600` | HUMS job |
| `FDM_POLL_INTERVAL_SECONDS` | `600` | FDM job |
| `GPMS_TOKEN_RENEWAL_DAYS` | `7` | Proactive JWT refresh |
| `FDM_OPERATIONS_FETCH_LIMIT` | `500` | FDM backfill cap per asset |
| `GPMS_PORTAL_ASSET_URL` | empty | Optional `format(asset_id=...)` in HUMS JSON |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_local_postgres.sh` | Docker Postgres + migrations + seed |
| `scripts/seed_mappings.py` | Idempotent mapping seed |
| `scripts/run_poll_once.py` | HUMS + FDM poll once (no scheduler) |
| `scripts/docker-push.sh` | Build and push `app-*` / `proxy-*` tags to Docker Hub |

## Operator portal

`app/static/` at `/` — calls cached API only (`/api/events/critical`, `/api/hums`, `/api/fdm/...`). Times shown as **UTC**.

## Inspect data

```bash
docker compose exec postgres psql -U brazos -d brazos_gpms -c \
  "SELECT gpms_asset_id, brazos_tail_number, is_active FROM gpms_asset_mappings;"
```

## Tests

Requires local Postgres (or `TEST_DATABASE_URL`):

```bash
pytest
```

## Known limitations

- Poll scope: **mapped + active** tails only.
- FDM backfill capped at `FDM_OPERATIONS_FETCH_LIMIT`; older flights need `POST .../ingest`.
- `hums_status_snapshots` written every poll; no read API.
- No API authentication on admin/read routes.
- Critical events: **`alarm` only** (not warning).

## GPMS endpoints used

| GPMS path | Used by |
|-----------|---------|
| `POST /auth/user` | Token manager |
| `GET /user/assets/{id}` | HUMS poll |
| `GET /user/assets/{id}/operations` | FDM backfill |
| `GET /user/assets/{id}/newimports` | FDM incremental |
| `GET /user/assets/{id}/exportstates/{opId}` | FDM ingest |
| `GET /user/assets/{id}/operations/{opId}` | Manual ingest metadata |
| `GET /user/fleets` | Not used in production (client helpers only) |
