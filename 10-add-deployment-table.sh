#!/usr/bin/env bash

set -euo pipefail

GERRIT_DB="$1"
TRAIN_DB="$2"

sqlite3 "$GERRIT_DB" <<EOF
CREATE TABLE if not exists deploys (
    id integer primary key,
    version text not null,
    start_deploy integer not null,
    group1_deploy integer not null,
    wikipedia_deploy integer not null,
    patchset integer not null
);
EOF

printf "Attaching $TRAIN_DB to ${GERRIT_DB}..."
sqlite3 "$GERRIT_DB" <<EOF
ATTACH DATABASE '$TRAIN_DB' AS source;
insert into deploys (
    version,
    start_deploy,
    group1_deploy,
    wikipedia_deploy,
    patchset
) select
    version,
    start_time,
    group1,
    group2,
    patchset
from source.train join source.patch on source.train.id = source.patch.train_id;
DETACH DATABASE source;
CREATE INDEX idx_patchset ON changes (patchset);
EOF
echo "done"
