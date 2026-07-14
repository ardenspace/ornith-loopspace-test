#!/bin/sh
# Halt 4 resume — decision: narrow policy exception for task 2.2 (and 2.3 if
# the same situation arises): task 2.1's frontier implementer already built
# the behavior, so failed-first TDD evidence is structurally impossible.
# Verify those tasks on coverage-only criteria. Then reattach the supervisor.
# Run detached: nohup sh hybrid_resume4.sh >> runner-logs/hybrid_supervise.log 2>&1 &
set -u

echo "=== HALT-RESUME 4 (2.2 coverage-only exception) $(date '+%F %T')"
cd /Users/arden/code/gridcalc-hybrid || exit 1
timeout 3600 opencode run --auto --print-logs --log-level INFO -m openai/gpt-5.5 \
  "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly. The project directory is /Users/arden/code/gridcalc-hybrid — resolve every .loopspace/... path relative to that directory, and do all work there. The run is halted; the human's decision on report.md is its second option: accept the narrow policy exception for task 2.2's failed-first evidence gate, because task 2.1 already implemented 2.2's behavior. Reset task 2.2 to pending and resume it with explicit coverage-only criteria (tests must cover the acceptance criteria; failed-first evidence is waived only where the behavior demonstrably landed with task 2.1's commit). If task 2.3 turns out to be in the same already-implemented situation, apply the same coverage-only exception there without halting; journal it. All other loop rules stay unchanged. Task routing stays as before: task-2.1-style frontier dispatches are over; implementation dispatches go to the implementer agent, verification dispatches to the verifier agent. Follow the looprun Halt-Resume procedure with that decision."
echo "=== resume session 4 exited rc=$? — starting supervisor"
cd /Users/arden/code/ornith-loopspace-experiments/gridcalc || exit 1
exec sh hybrid_supervise.sh
