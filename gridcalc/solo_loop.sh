#!/bin/sh
# Experiment W — arm A (solo) session loop.
# Fresh opencode session per iteration; the repo (plus any notes file the
# model chooses to keep) is the only memory between sessions. Commits a
# snapshot after every session for trajectory grading.
#
# Usage: sh solo_loop.sh
set -u

REPO=/Users/arden/code/gridcalc-solo
RUNNER=/Users/arden/code/gridcalc-runner
PROMPT_FILE=$RUNNER/armA_solo_prompt.txt
LOG_DIR=$RUNNER/logs
MAX_SESSIONS=12
DEADLINE=$(( $(date +%s) + 8 * 3600 ))

mkdir -p "$LOG_DIR"
cd "$REPO" || exit 1

i=1
while [ "$i" -le "$MAX_SESSIONS" ]; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "solo_loop: 8h time cap reached after $((i - 1)) sessions"
    break
  fi
  echo "solo_loop: session $i starting $(date '+%H:%M:%S')"
  pkill -9 -f opencode 2>/dev/null
  sleep 3
  opencode run --auto --print-logs --log-level INFO \
    -m ornith/ornith-1.0-35b-Q5_K_M \
    "$(cat "$PROMPT_FILE")" > "$LOG_DIR/session_$i.log" 2>&1
  git add -A
  git commit -q --allow-empty -m "solo session $i"
  if grep -q "<DONE>" "$LOG_DIR/session_$i.log"; then
    echo "solo_loop: <DONE> declared at session $i"
    break
  fi
  i=$((i + 1))
done
pkill -9 -f opencode 2>/dev/null
echo "solo_loop: finished"
