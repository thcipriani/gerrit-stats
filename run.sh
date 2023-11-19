#!/usr/bin/env bash

set -euo pipefail

if echo " $(groups) " | fgrep -q ' docker '; then
    echo "User is in docker group."
    DOCKER_USER="$(id -u):$(id -g)"
else
    if [ -z "${SUDO_UID:-}" ] || ! [ $(id -u) -eq 0 ]; then
        echo "Run with sudo."
        echo "This is a hack to allowing full access to the docker daemon by the effective user."
        exit 1
    fi
    DOCKER_USER="$SUDO_UID:$SUDO_GID"
fi

docker build -t devel-stats -f Dockerfile .
docker run -it --rm \
    --user "$DOCKER_USER" \
    -v $(pwd)/src:/src \
    -v $(pwd)/data:/src/data \
    -v /srv/git:/srv/git:ro \
    devel-stats \
    /src/update.sh "w000t!"
