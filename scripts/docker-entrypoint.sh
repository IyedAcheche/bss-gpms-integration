#!/bin/sh
set -e

# Migrations + seed + polls run in app lifespan; uvicorn serves after startup.
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
