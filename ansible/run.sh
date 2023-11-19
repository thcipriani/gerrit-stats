#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Activate the virtual environment
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
else
    echo "Virtual environment not found. Creating one..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    source "$SCRIPT_DIR/.venv/bin/activate"
    pip3 install -r "$SCRIPT_DIR/requirements.txt"
fi

export ANSIBLE_NOCOWS=1
ansible-playbook -i "$SCRIPT_DIR/hosts" "$SCRIPT_DIR/playbook.yml"
