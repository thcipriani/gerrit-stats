#!/usr/bin/env bash

set -euo pipefail

NEXT_STEP_FILE=data/next-step-time.txt
LAST_STEP_FILE=data/step-time.txt

if [[ ! -f "$LAST_STEP_FILE" ]]; then
    echo 0 > "$LAST_STEP_FILE"
    exit 0
fi

# Colors
# ------
POWDER_BLUE=$(tput setaf 153)
RED=$(tput setaf 1)
RESET=$(tput sgr0)

human_time() {
  local _time=$1
  local _out=""

  local days=$(( $_time / 60 / 60 / 24 ))
  local hours=$(( $_time / 60 / 60 % 24 ))
  local minutes=$(( $_time / 60 % 60 ))
  local seconds=$(( $_time % 60 ))

  (( $days > 0 )) && _out="${days}d "
  (( $hours > 0 )) && _out="$_out${hours}h "
  (( $minutes > 0 )) && _out="$_out${minutes}m "

  _out="$_out${seconds}s"
  echo "${RED}$_out${RESET}"
}

# Current time
date +%s > "$NEXT_STEP_FILE"
NOW=$(cat "$NEXT_STEP_FILE")

# Last time
LAST_STEP=$(cat "$LAST_STEP_FILE")

# Logging
printf "[${POWDER_BLUE}$(date -Is)${RESET}] Processing step time: "
human_time "$(( $NOW - $LAST_STEP ))"

# Update last time
mv "$NEXT_STEP_FILE" "$LAST_STEP_FILE"
