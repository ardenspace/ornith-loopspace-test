#!/bin/sh
# Experiment L — armSN build: Sonnet solo, same procedure as arm A (solo_loop.sh).
# Only the model changes. Fresh session per iteration; the repo (plus any notes
# file the model keeps) is the only memory between sessions. Snapshot commit
# after every session so trajectory grading stays available.
#
# NOTE (operator): arm A ran headless via `opencode run --auto`. This loop shells
# out to `claude` instead, because opencode has no Anthropic OAuth (see the
# hybrid run's pre-registration). An unattended loop needs whatever autonomy flag
# you are willing to grant inside this experiment repo — set it in CLAUDE_FLAGS
# below. Left empty, each session will stop at the first approval prompt.
#
# Usage: CLAUDE_FLAGS='...' sh sonnet_solo_loop.sh
set -u

REPO=/Users/arden/code/gridcalc-sonnet
RUNNER=/Users/arden/code/ornith-loopspace-experiments/gridcalc
PROMPT_FILE=$RUNNER/armA_solo_prompt.txt   # verbatim reuse — arm parity
LOG_DIR=$RUNNER/runner-logs/sonnet-solo
MODEL=claude-sonnet-5
CLAUDE_FLAGS=${CLAUDE_FLAGS:-}
# Defaults mirror solo_loop.sh (arm parity). Both are ceilings, not targets —
# arm A declared <DONE> in session 1 (~40 min), nowhere near them. Override via
# env to cap a supervised run shorter; the cap is a checkpoint, not a stopping
# rule — a run cut off without <DONE> must be relaunched (the repo is the only
# memory between sessions) before grading, or arm parity breaks.
MAX_SESSIONS=${MAX_SESSIONS:-12}
DEADLINE=$(( $(date +%s) + ${MAX_HOURS:-8} * 3600 ))

# The solo prompt names arm A's repo path; rewrite that one path for this arm.
PROMPT=$(sed 's#/Users/arden/code/gridcalc-solo#'"$REPO"'#g' "$PROMPT_FILE")

mkdir -p "$LOG_DIR"
cd "$REPO" || { echo "seed $REPO first (SPEC.md + PLAN.md, git init)"; exit 1; }

i=1
while [ "$i" -le "$MAX_SESSIONS" ]; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "sonnet_solo_loop: 8h time cap reached after $((i - 1)) sessions"
    break
  fi
  echo "sonnet_solo_loop: session $i starting $(date '+%H:%M:%S')"
  # shellcheck disable=SC2086
  claude -p --model "$MODEL" $CLAUDE_FLAGS \
    "$PROMPT" > "$LOG_DIR/session_$i.log" 2>&1
  git add -A
  git commit -q --allow-empty -m "sonnet solo session $i"
  if grep -q "<DONE>" "$LOG_DIR/session_$i.log"; then
    echo "sonnet_solo_loop: <DONE> declared at session $i"
    break
  fi
  i=$((i + 1))
done
echo "sonnet_solo_loop: finished"
