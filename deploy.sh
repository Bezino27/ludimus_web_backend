#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

if [[ "${1:-}" != "--apply" ]]; then
    echo "Použitie: ./deploy.sh --apply"
    echo "Skript nič nevykoná bez explicitného --apply."
    exit 1
fi

if [[ "${LUDIMUS_BACKUP_CONFIRMED:-}" != "yes" ]]; then
    echo "CHYBA: Pred nasadením musí byť overená aktuálna záloha databázy a media."
    echo "Po overení spusti s LUDIMUS_BACKUP_CONFIRMED=yes."
    exit 1
fi

if [[ ! -f "$COMPOSE_FILE" || ! -f "$ENV_FILE" ]]; then
    echo "CHYBA: Chýba $COMPOSE_FILE alebo produkčný $ENV_FILE."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "CHYBA: Docker nie je spustený."
    exit 1
fi

compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "docker-compose.prod.yml")

"${compose[@]}" config --quiet
"${compose[@]}" build backend
"${compose[@]}" run --rm backend python manage.py check --deploy
"${compose[@]}" run --rm backend python manage.py migrate --plan

read -r -p "Napíš DEPLOY na aplikovanie migrácií a reštart: " confirmation
if [[ "$confirmation" != "DEPLOY" ]]; then
    echo "Nasadenie zrušené."
    exit 1
fi

"${compose[@]}" run --rm backend python manage.py migrate --noinput
"${compose[@]}" run --rm backend python manage.py collectstatic --noinput
"${compose[@]}" up -d backend
"${compose[@]}" ps
