#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

docker compose \
  --env-file .env.local \
  -f docker-compose.dev.yml \
  logs --tail=100 -f backend
