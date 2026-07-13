#!/bin/sh
# Halt 3 resume — decision: task 2.1 implementation routes to the
# implementer-frontier agent (gpt-5.5); every other implementation dispatch
# stays on the implementer agent (ornith). Then reattach the supervisor.
# Run detached: nohup sh hybrid_resume3.sh >> runner-logs/hybrid_supervise.log 2>&1 &
set -u

echo "=== HALT-RESUME 3 (2.1 -> implementer-frontier) $(date '+%F %T')"
cd /Users/arden/code/gridcalc-hybrid || exit 1
timeout 3600 opencode run --auto --print-logs --log-level INFO -m openai/gpt-5.5 \
  "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly. The project directory is /Users/arden/code/gridcalc-hybrid — resolve every .loopspace/... path relative to that directory, and do all work there. The run is halted; the human's decision on report.md: reset task 2.1 to pending and resume the same task — the harness routing was fixed outside loopspace. From now on, task 2.1's implementation dispatches go to the implementer-frontier agent; every other task's implementation dispatches go to the implementer agent, and verification dispatches go to the verifier agent. Follow the looprun Halt-Resume procedure with that decision."
echo "=== resume session 3 exited rc=$? — starting supervisor"
cd /Users/arden/code/ornith-loopspace-experiments/gridcalc || exit 1
exec sh hybrid_supervise.sh
