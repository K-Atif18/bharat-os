#!/usr/bin/env bash
# Back up the Bharat OS database.
#
# Usage: ./backup.sh [output-directory]
#
# Requires BHARAT_OS_DATABASE_URL to point at Postgres. Writes a timestamped,
# gzip-compressed custom-format dump, which pg_restore can apply selectively
# (e.g. one table) rather than only as an all-or-nothing restore.
set -euo pipefail

OUTPUT_DIR="${1:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="${OUTPUT_DIR}/bharat_os_${TIMESTAMP}.dump"

: "${BHARAT_OS_DATABASE_URL:?BHARAT_OS_DATABASE_URL must be set}"

if [[ "${BHARAT_OS_DATABASE_URL}" == sqlite* ]]; then
  echo "Refusing to back up a SQLite URL — SQLite is not supported in production." >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

# pg_dump accepts a libpq connection URL directly, including the
# postgresql+psycopg:// scheme's postgresql:// portion.
CONNECTION_URL="${BHARAT_OS_DATABASE_URL/postgresql+psycopg/postgresql}"

pg_dump --format=custom --compress=9 --dbname="${CONNECTION_URL}" --file="${OUTPUT_FILE}"

echo "Backup written to ${OUTPUT_FILE}"
echo "Restore with: ./restore.sh ${OUTPUT_FILE}"
