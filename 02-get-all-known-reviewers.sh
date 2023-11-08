#!/usr/bin/env bash

DB_FILE="gerrit.db"
OUTPUT_FILE="data/all-known-reviewers.csv"

if [[ ! -f "$DB_FILE" ]]; then
    echo "$DB_FILE does not yet exist..."
    exit 0
fi

echo "Gathering all known reviewers from $DB_FILE into $OUTPUT_FILE"
# Run SQLite commands
sqlite3 "$DB_FILE" <<EOF
.headers on
.mode csv
.output $OUTPUT_FILE
SELECT id, repo, patchset, author_id FROM changes WHERE type = "reviewer" GROUP BY patchset, author_id;
.output stdout
.quit
EOF
