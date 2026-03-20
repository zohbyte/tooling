#!/bin/bash
# Usage: ./throw.sh

set -Eeuo pipefail

on_error() {
	local rc=$?
	echo "[ERROR] throw.sh failed (exit=$rc, line=${BASH_LINENO[0]}, cmd=${BASH_COMMAND})" >&2
	exit "$rc"
}
trap on_error ERR

# Get the current working directory (where the user ran the script from)
DIR="$(pwd)"
SERVICE="$(basename "$DIR")"
LOG_DIR="${LOG_DIR:-$DIR/.logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/throw-$(date +%Y%m%d-%H%M%S).log"

echo "[INFO] Service: $SERVICE"
echo "[INFO] Log file: $LOG_FILE"

if [[ ! -t 0 ]]; then
	echo "[WARN] No interactive stdin detected. If glitch prompts, the process may wait for input." | tee -a "$LOG_FILE"
fi

glitch exploit throw "$DIR/exploit.py" "$SERVICE" 2>&1 | tee -a "$LOG_FILE"
rc=${PIPESTATUS[0]}

exit "$rc"