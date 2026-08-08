#!/usr/bin/env bash
# Restore the Bharat OS database from a backup produced by backup.sh.
#
# Usage: ./restore.sh path/to/backup.dump
#
# This is destructive to the target database's current contents where table
# names collide. It does not run without explicit confirmation.
set -euo pipefail

DUMP_FILE="${1:?Usage: ./restore.sh path/to/backup.dump}"
: "${BHARAT_OS_DATABASE_URL:?BHARAT_OS_DATABASE_URL must be set}"

if [[ ! -f "${DUMP_FILE}" ]]; then
  echo "No such file: ${DUMP_FILE}" >&2
  exit 1
fi

CONNECTION_URL="${BHARAT_OS_DATABASE_URL/postgresql+psycopg/postgresql}"

echo "This will restore ${DUMP_FILE} into:"
echo "  ${BHARAT_OS_DATABASE_URL}"
echo "Existing tables with the same names will be overwritten."
read -r -p "Type 'restore' to continue: " CONFIRMATION

if [[ "${CONFIRMATION}" != "restore" ]]; then
  echo "Aborted."
  exit 1
fi

pg_restore --clean --if-exists --no-owner --dbname="${CONNECTION_URL}" "${DUMP_FILE}"

echo "Restore complete. Run 'alembic upgrade head' to apply any migrations newer than this backup."
