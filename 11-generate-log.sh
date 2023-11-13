#!/usr/bin/env bash

set -euo pipefail

GERRIT_DB="$1"
LOG="$2"
START_DATE="$3"
END_DATE="$4"

START=$(date -d "$START_DATE" +%s)
END=$(date -d "$END_DATE" +%s)

echo "Generating log $LOG from $GERRIT_DB"
echo 'date,patchset,type' > "$LOG"
sqlite3 "$GERRIT_DB" <<EOF
.mode csv
.output '$LOG'
select
    date,
    changes.patchset,
    type || COALESCE(vote, '')
    from deploys
    join changes on changes.patchset = deploys.patchset
    where type in (
        'newpatchset',
        'patch',
        'recheck',
        'rebase',
        'abandon',
        'codereview',
        'verified',
        'submit'
    ) AND date >= $START AND
    date <= $END;
select
    start_deploy,
    patchset,
    'deploy'
    from deploys
    where start_deploy >= $START AND
    start_deploy <= $END;
EOF

