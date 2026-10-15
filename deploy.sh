#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

COMPOSE=(docker compose --env-file .env -f docker-compose.yml -f docker-compose.prod.yml)
CONTAINER=ludimus_backend

usage() {
  echo "Použitie: sudo ./deploy.sh [--check]"
  echo "  --check  Len overí aktuálne bežiaci backend, nič nemení."
  echo "  bez argumentu  Zostaví a nasadí backend po potvrdení."
}

if [[ $# -gt 1 ]] || { [[ $# -eq 1 ]] && [[ "$1" != "--check" ]]; }; then
  usage
  exit 2
fi

if [[ $EUID -ne 0 ]]; then
  echo "CHYBA: Spusti cez sudo."
  exit 1
fi

for file in .env docker-compose.yml docker-compose.prod.yml; do
  if [[ ! -f "$file" ]]; then
    echo "CHYBA: Chýba $file"
    exit 1
  fi
done

if ! docker info >/dev/null 2>&1; then
  echo "CHYBA: Docker nie je dostupný."
  exit 1
fi

"${COMPOSE[@]}" config --quiet

check_running() {
  echo "Kontrolujem Django, migrácie a databázu..."
  docker exec "$CONTAINER" python manage.py check
  docker exec "$CONTAINER" python manage.py migrate --check
  docker exec "$CONTAINER" python manage.py shell -c \
    "from django.db import connection; c=connection.cursor(); c.execute('SELECT 1'); print('DATABASE OK:', c.fetchone())"
  echo "Používateľ kontajnera:"
  docker exec "$CONTAINER" id
}

if [[ "${1:-}" == "--check" ]]; then
  check_running
  echo "KONTROLA DOKONČENÁ"
  exit 0
fi

printf '\nLUDIMUS WEB – PRODUKČNÝ DEPLOY\n'
read -r -p "Overil si aktuálnu zálohu DB a media? Napíš BACKUP: " backup_confirm
if [[ "$backup_confirm" != "BACKUP" ]]; then
  echo "Deploy zrušený."
  exit 1
fi

"${COMPOSE[@]}" build backend
"${COMPOSE[@]}" run --rm --no-deps --entrypoint python backend manage.py check --deploy

echo "Kontrolujem databázové migrácie..."
if ! "${COMPOSE[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate --check; then
  "${COMPOSE[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate --plan
  read -r -p "Migrácie sú potrebné. Po kontrole plánu napíš MIGRATE: " migrate_confirm
  if [[ "$migrate_confirm" != "MIGRATE" ]]; then
    echo "Deploy zrušený bez migrácií."
    exit 1
  fi
  "${COMPOSE[@]}" run --rm --no-deps --entrypoint python backend manage.py migrate --noinput
fi

read -r -p "Nasadiť novú verziu backendu? Napíš DEPLOY: " deploy_confirm
if [[ "$deploy_confirm" != "DEPLOY" ]]; then
  echo "Deploy zrušený."
  exit 1
fi

"${COMPOSE[@]}" up -d --no-build --no-deps --force-recreate backend
check_running
"${COMPOSE[@]}" ps

echo "DEPLOY DOKONČENÝ – over ešte verejné API a prihlasovanie."
