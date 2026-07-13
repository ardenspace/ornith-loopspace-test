#!/bin/sh
# Hybrid rerun — gridcalc on loopspace 0.15.2, frontier orchestrator/verifier
# (anthropic/claude-sonnet-5) x ornith implementer. Same spec+plan seed as
# arm B and the 0.15.0 rerun; variables vs the 0.15.0 rerun: loopspace
# version (0.15.2), orchestrator+verifier model, tier A, ornith client
# timeout 300s -> 900s (project opencode.json).
#
# Requires: opencode authenticated with anthropic (opencode auth login),
# ornith llama-server on :18081.
#
# Usage: sh hybrid_supervise.sh
set -u

export LOOPSPACE_MAX_RESTARTS=16
export LOOPSPACE_MAX_NOPROGRESS=2
# 0.15.2 defaults kept explicit for the record:
export LOOPSPACE_STALL_TIMEOUT=3600
export LOOPSPACE_MAX_FASTFAIL=3
export LOOPSPACE_FASTFAIL_SECS=60
export LOOPSPACE_RESUME_CMD='pkill -9 -f opencode 2>/dev/null; sleep 3; opencode run --auto --print-logs --log-level INFO -m anthropic/claude-sonnet-5 "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly. The project directory is /Users/arden/code/gridcalc-hybrid — resolve every .loopspace/... path relative to that directory, and do all work there. When dispatching subagents: implementation dispatches go to the implementer agent, verification dispatches to the verifier agent."'

exec sh /Users/arden/code/loopspace/scripts/supervise.sh /Users/arden/code/gridcalc-hybrid
