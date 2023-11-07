#!/usr/bin/env bash

set -euo pipefail

# 1. Get a list of the refs like refs/changes/*/*/meta
# 2. Get the object name of the ref
# 3. git log --format=%H <objectname>
# 4. Store as a csv like: repo,objectname,refname,commit


REPO_NAME="$1"
SAFE_REPO="$2"
REPO_DIR="$3"
LAST_UPDATE="$4"
OUT_PATH="data/$SAFE_REPO-meta-refs.csv"
echo 'repo,objectname,refname,commit' > "$OUT_PATH"
if [[ "$LAST_UPDATE" == "never" ]]; then
    git -C "$REPO_DIR" for-each-ref refs/changes/*/*/meta --format="${REPO_DIR},%(objectname),%(refname),0" >> "$OUT_PATH"
else
    git -C "$REPO_DIR" for-each-ref refs/changes/*/*/meta --format="${REPO_DIR} %(objectname) %(refname)" \
    | while read -r R OBJECTNAME REFNAME; do
        git -C "$R" log --format=%H --after "$LAST_UPDATE" "$OBJECTNAME" \
        | awk -v repo="$R" -v objectname="$OBJECTNAME" -v refname="$REFNAME" '{print repo "," objectname "," refname "," $0}'
    done >> "$OUT_PATH"
fi
