#!/usr/bin/env bash
# Start local Postgres (Docker), run Alembic migrations, seed default mapping (223 → N407NW).
# See README.md for manual setup without Docker.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker Desktop, or run Postgres locally and set DATABASE_URL in .env"
  echo "Then: alembic upgrade head && python scripts/seed_mappings.py"
  exit 1
fi

echo "Starting Postgres..."
docker compose up -d --wait

if [ -d .venv ]; then
  PY=".venv/bin/python"
  ALEMBIC=".venv/bin/alembic"
else
  PY="python3"
  ALEMBIC="alembic"
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://brazos:brazos@localhost:5432/brazos_gpms}"

echo "Running migrations..."
"$ALEMBIC" upgrade head

echo "Seeding mappings (223 → N407NW)..."
"$PY" scripts/seed_mappings.py

echo "Done. Start the API with:"
echo "  uvicorn app.main:app --reload --port 8080"
