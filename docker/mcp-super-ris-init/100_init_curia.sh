#!/bin/bash
# Runs CURIA schema SQL files on fresh DB init (docker-entrypoint-initdb.d).
# Checks two locations: dedicated mount (/srv/curia-sql) and artifacts (/srv/super-ris-artifacts/curia_db).
set -e

CURIA_SQL_DIR=""
if [ -d "/srv/curia-sql" ] && ls /srv/curia-sql/0*.sql >/dev/null 2>&1; then
  CURIA_SQL_DIR="/srv/curia-sql"
elif [ -d "/srv/super-ris-artifacts/curia_db" ] && ls /srv/super-ris-artifacts/curia_db/0*.sql >/dev/null 2>&1; then
  CURIA_SQL_DIR="/srv/super-ris-artifacts/curia_db"
fi

if [ -z "$CURIA_SQL_DIR" ]; then
  echo "[100_init_curia] No CURIA SQL files found — skipping."
  exit 0
fi

echo "[100_init_curia] Initializing CURIA schema from ${CURIA_SQL_DIR}..."
for sql in "$CURIA_SQL_DIR"/0*.sql; do
  echo "  Running $(basename "$sql")..."
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" < "$sql"
done
echo "[100_init_curia] CURIA schema initialized."
