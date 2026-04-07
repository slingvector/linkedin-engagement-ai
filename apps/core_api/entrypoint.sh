#!/bin/bash
# entrypoint.sh — runs Alembic migrations then starts uvicorn
# Ensures schema is always up-to-date on container startup.
set -e

echo "[entrypoint] Running database migrations..."
python -m alembic upgrade head

echo "[entrypoint] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
