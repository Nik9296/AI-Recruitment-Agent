#!/usr/bin/env bash
# One-command local setup for macOS / Linux.
# Requires Docker.

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install Docker, start it, then run this script again."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
  echo "Optional: add GOOGLE_API_KEY to .env if you want JD analysis."
else
  echo "Using existing .env (not overwritten)"
fi

echo "Starting Postgres, API, dashboard, and demo seed..."
docker compose up --build -d

ready=0
for _ in $(seq 1 45); do
  if curl -fsS "http://127.0.0.1:8000/ready" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done

if [ "$ready" -eq 0 ]; then
  echo "API is still starting. Check: docker compose logs backend"
else
  echo "API is ready."
fi

echo
echo "Dashboard:  http://localhost:3000"
echo "API docs:   http://127.0.0.1:8000/docs"
echo "Login:      recruiter  /  recruiter-review"
echo "(unless you changed RECRUITER_USERNAME / RECRUITER_PASSWORD in .env)"
echo
echo "Stop later with: docker compose down"
