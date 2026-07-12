#!/bin/sh
# Experiment W follow-up — gridcalc rerun on loopspace 0.15.0 (spec probes +
# mutation spot-check + verifier-derived instances). Same spec+plan as arm B;
# the only variable is the loopspace version. Wraps loopspace's own
# scripts/supervise.sh with the opencode/ornith resume command.
# Exits on complete/halted/stuck.
#
# Usage: sh rerun_supervise.sh
set -u

export LOOPSPACE_MAX_RESTARTS=16
export LOOPSPACE_MAX_NOPROGRESS=2
export LOOPSPACE_RESUME_CMD='pkill -9 -f opencode 2>/dev/null; sleep 3; opencode run --auto --print-logs --log-level INFO -m ornith/ornith-1.0-35b-Q5_K_M "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly. The project directory is /Users/arden/code/gridcalc-rerun — resolve every .loopspace/... path relative to that directory, and do all work there."'

exec sh /Users/arden/code/loopspace/scripts/supervise.sh /Users/arden/code/gridcalc-rerun
