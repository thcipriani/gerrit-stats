#!/usr/bin/env bash

set -euo pipefail

DB="$1"

sqlite3 "$DB" <<EOF
CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    patchset INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    sha TEXT NOT NULL,
    date INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    status TEXT,
    type TEXT NOT NULL,
    label TEXT,
    value INTEGER,
    bot_like INTEGER NOT NULL
);
EOF
