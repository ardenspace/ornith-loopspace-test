#!/bin/sh
# Experiment L — step 3: blind verifier probe.
# Runs the SAME prompt against one model, on one frozen snapshot of armSN.
# Each cell is independent: no verifier sees another's output, and the prompt
# carries no hint about ranges, ordering, or M7.
#
# The probe is read-only analysis — it reports findings, it does not edit the
# tree. Add whatever flags your runner needs for an unattended session.
#
# Usage: sh verifier_probe.sh <model> [repo]
#   sh verifier_probe.sh claude-sonnet-5     # (a) same model      [floor]
#   sh verifier_probe.sh claude-opus-5       # (b) same lineage    [the question]
#   sh verifier_probe.sh gpt-5.5             # (c) other lineage   [ceiling]
set -u

MODEL=${1:?usage: verifier_probe.sh <model> [repo]}
REPO=${2:-/Users/arden/code/gridcalc-sonnet}
RUNNER=/Users/arden/code/ornith-loopspace-experiments/gridcalc
OUT_DIR=$RUNNER/runner-logs/verifier-probe

mkdir -p "$OUT_DIR"
SNAP=$(git -C "$REPO" rev-parse --short HEAD)
PROMPT=$(sed "s#REPO_PATH#$REPO#g" "$RUNNER/verifier_probe_prompt.txt")
OUT=$OUT_DIR/${MODEL}_${SNAP}.md

echo "probe: model=$MODEL snapshot=$SNAP -> $OUT"

# Autonomy flags are the operator's call, as with sonnet_solo_loop.sh. All three
# cells must run under the SAME grant or the comparison is confounded, so set
# both to the equivalent level for their runner.
CLAUDE_FLAGS=${CLAUDE_FLAGS:-}
OPENCODE_FLAGS=${OPENCODE_FLAGS:-}

# shellcheck disable=SC2086
case "$MODEL" in
  gpt-*)  opencode run $OPENCODE_FLAGS -m "openai/$MODEL" "$PROMPT" > "$OUT" 2>&1 ;;
  *)      claude -p --model "$MODEL" $CLAUDE_FLAGS "$PROMPT" > "$OUT" 2>&1 ;;
esac

echo "--- mixed mis-order mentions (judge manually; a bare 'B2:A1' does NOT count) ---"
grep -niE "B1:A2|mixed|mis-order|misorder|reversed column|column .* reversed" "$OUT" || echo "(none)"
