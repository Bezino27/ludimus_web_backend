#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

echo "Zastavujem lokálny Django backend..."

docker compose \
  --env-file .env.local \
  -f docker-compose.dev.yml \
  down

echo "Lokálny backend je zastavený."
echo "PostgreSQL 18 na Macu zostáva spustený."
