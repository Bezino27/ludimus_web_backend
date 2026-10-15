#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env.local"

echo "=================================="
echo "  LUDIMUS WEB - LOCAL DEPLOY"
echo "=================================="

# 1. Kontrola potrebných súborov
if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "CHYBA: Chýba $COMPOSE_FILE"
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "CHYBA: Chýba $ENV_FILE"
    exit 1
fi

# 2. Kontrola Dockeru
if ! docker info >/dev/null 2>&1; then
    echo "CHYBA: Docker nie je spustený."
    exit 1
fi

# 3. Kontrola konfigurácie
echo ""
echo "Kontrolujem Docker Compose..."

docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    config --quiet

# 4. Kontrola, že nepoužívame Docker databázu
if docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    config --services | grep -qx "db"; then
    echo "CHYBA: Konfigurácia stále obsahuje Docker databázu."
    exit 1
fi

# 5. Spustenie backendu
echo ""
echo "Spúšťam lokálny Django backend..."

docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    up -d --build backend

# 6. Stav kontajnera
echo ""
echo "Stav backendu:"

docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    ps

# 7. Posledné logy
echo ""
echo "Posledné logy:"

docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    logs --tail=40 backend

echo ""
echo "=================================="
echo "  LOCAL DEPLOY DOKONČENÝ"
echo "=================================="
echo "Django Admin: http://127.0.0.1:8000/admin/"
