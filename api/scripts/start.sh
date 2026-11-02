#!/bin/sh
# Migrate and seed steps arrive in Phase 2. Single worker: see ADR-005.
set -e
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
