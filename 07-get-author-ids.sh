#!/usr/bin/env bash

set -euo pipefail

# See if authors table exists
output=$(echo 'select * from authors limit 1;' | sqlite3 gerrit.db)

if [[ -z "$output" ]]; then
    echo 'No authors table found...'
    echo 'select distinct author_id from changes;' | sqlite3 gerrit.db > data/author-ids.txt
else
    echo 'Authors table found...'
    echo 'select distinct author_id from changes where author_id not in (select id from authors);' | sqlite3 gerrit.db > data/author-ids.txt
fi
