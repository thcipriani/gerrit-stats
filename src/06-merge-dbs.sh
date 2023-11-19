#!/usr/bin/env bash

set -euo pipefail

DESTINATION_DB="$1"

while read db; do
  DB_FILE="$db"

  printf "Attaching $DB_FILE to ${DESTINATION_DB}..."
  sqlite3 "$DESTINATION_DB" <<EOF
ATTACH DATABASE '$DB_FILE' AS source;
insert into changes (
    repo,
    patchset,
    patch,
    sha,
    date,
    author_id,
    status,
    type,
    vote,
    reviewer_id,
    bot_like
) select
    repo,
    patchset,
    patch,
    sha,
    date,
    author_id,
    status,
    type,
    vote,
    reviewer_id,
    bot_like
from source.changes;
DETACH DATABASE source;
EOF

  echo "Merged data from $DB_FILE into ${DESTINATION_DB}."
done
