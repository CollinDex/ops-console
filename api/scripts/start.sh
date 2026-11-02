#!/bin/sh
# Migrate, seed (skipped when data exists), then serve. Single worker: see ADR-005.
set -e
alembic upgrade head
python -m scripts.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
