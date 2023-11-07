#!/usr/bin/env bash
# Create an mrconfig file and update all mirrors
# Run this in /srv/git to update all mirrors before running "make"
set -euo pipefail

echo 'Updating mrconfig...'
mv .mrconfig .mrconfig.$(date -I).${RANDOM}.old

cat > .mrconfig <<EOF
[DEFAULT]
update = git remote update
countobjects = git count-objects
du = du -cks | grep -v total
sizer = git sizer
sandbox = git for-each-ref refs/heads/sandbox

EOF

while read repo; do
    printf '[%s]\n%s\n\n' "${repo}.git" "checkout = git clone --mirror https://gerrit-replica.wikimedia.org/r/${repo}"
done < <(curl -sL https://gerrit.wikimedia.org/r/projects/?all | \
    tail -c +6 | \
    jq -r '.|to_entries|map(select(.value.state == "ACTIVE"))|.[].key') >> .mrconfig

echo 'Updating mirrors...'
mr update
