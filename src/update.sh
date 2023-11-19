#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

usage() {
    cat<<USE
    USAGE:
      $0
    EXAMPLE:
      $0
    DESCRIPTION:
      Just run it. It will magic itself.
USE
}

commit() {
    local msg
    msg="$@"
    git -C "$SCRIPT_DIR" commit -a -m "$msg"
}

submodules() {
    git submodule update --init --recursive
    git -C "$SCRIPT_DIR"/submodules/train-stats fetch || :
    git -C "$SCRIPT_DIR"/submodules/train-stats checkout --force origin/main || :
    commit 'Bump train-stats' || :
}

newversion() {
    local version python
    version="$1"
    p=python3
    if [ -d "$SCRIPT_DIR"/venv ]; then
        . "$SCRIPT_DIR"/venv/bin/activate
        p="$SCRIPT_DIR"/venv/bin/python3
        echo 'Activating magic 1'
    elif [ -d "$SCRIPT_DIR"/../venv ]; then
        . "$SCRIPT_DIR"/../venv/bin/activate
        p="$SCRIPT_DIR"/../venv/bin/python3
        echo 'Activating magic 2'
    fi
    $p "$SCRIPT_DIR"/trainstats.py -w "$version"
}

update_trains() {
    local version trains
    version="$1"
    trains=$(tail +2 "$SCRIPT_DIR"/data/TRAINS)
    printf "%s\n%s" "$trains" "$version" > "$SCRIPT_DIR"/data/TRAINS
}

main() {
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        usage
        exit 0
    fi

    submodules
    cd "$SCRIPT_DIR"
    make
    make authors
    make deployment
}

main "$@"
