#!/usr/bin/env bash
# Start Postgres + GPMS API containers (Compose profile: full).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Missing .env — copy .env.example and set GPMS_EMAIL / GPMS_PASSWORD"
  echo "For Docker, DATABASE_URL must use host 'postgres' (see .env.docker.example)"
  exit 1
fi

echo "Building and starting postgres + app + nginx..."
docker compose --profile full up -d --build --wait

echo ""
echo "Portal:  http://localhost:8080/"
echo "Swagger: http://localhost:8080/docs"
echo "Health:  http://localhost:8080/health"
echo ""
echo "Logs: docker compose --profile full logs -f proxy app"
