#!/bin/sh
# Halt 7 resume — decision: same policy as the 2.1 halt (6 failed implementer
# dispatches on a heavy task): task 4.2's implementation routes to the
# implementer-frontier agent. Narrow scope from the report's option 1: fix
# transitive invalidation for cached closure tracking and add the
# X1 -> Y1 -> A1 regression test. Then reattach the supervisor.
# Run detached: nohup sh hybrid_resume7.sh >> runner-logs/hybrid_supervise.log 2>&1 &
set -u

echo "=== HALT-RESUME 7 (4.2 -> implementer-frontier) $(date '+%F %T')"
cd /Users/arden/code/gridcalc-hybrid || exit 1
timeout 3600 opencode run --auto --print-logs --log-level INFO -m openai/gpt-5.5 \
  "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly. The project directory is /Users/arden/code/gridcalc-hybrid — resolve every .loopspace/... path relative to that directory, and do all work there. The run is halted; the human's decision on report.md: reset task 4.2 to pending and resume it, with its implementation dispatches routed to the implementer-frontier agent (same policy as task 2.1: six failed implementer dispatches). Scope per the report's first option: fix transitive invalidation for cached closure tracking and add the X1 -> Y1 -> A1 regression test. Every other task's implementation dispatches stay on the implementer agent; verification dispatches go to the verifier agent. Follow the looprun Halt-Resume procedure with that decision."
echo "=== resume session 7 exited rc=$? — starting supervisor"
cd /Users/arden/code/ornith-loopspace-experiments/gridcalc || exit 1
exec sh hybrid_supervise.sh
