#!/bin/sh
set -eu

if [ -n "${DATABASE_URL:-}" ]; then
  python -m alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
