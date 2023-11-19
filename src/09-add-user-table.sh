#!/usr/bin/env bash

set -euo pipefail

GERRIT_DB="$1"
USER_DB="$2"

sqlite3 "$GERRIT_DB" <<EOF
CREATE TABLE if not exists authors (
    id integer primary key,
    username text not null,
    is_wmf integer not null,
    was_wmf integer not null,
    is_wmde integer not null,
    was_wmde integer not null
);
EOF

printf "Attaching $USER_DB to ${GERRIT_DB}..."
sqlite3 "$GERRIT_DB" <<EOF
ATTACH DATABASE '$USER_DB' AS source;
insert into authors (
    id,
    username,
    is_wmf,
    was_wmf,
    is_wmde,
    was_wmde
) select
    id,
    username,
    is_wmf,
    was_wmf,
    is_wmde,
    was_wmde
from source.authors;
DETACH DATABASE source;
EOF
echo "done"
