#!/bin/sh
# Halt 6 resume — decision: report option 1 for task 4.1. Keep the Sheet-level
# cache/evaluator-side counting approach; remove tests asserting
# unrelated-set recomputation (spec-incompatible with 4.2); add coverage that
# non-formula set calls leave eval_count unchanged; supply credible
# failed-first evidence from a test that actually fails pre-implementation.
# Run detached: nohup sh hybrid_resume6.sh >> runner-logs/hybrid_supervise.log 2>&1 &
set -u

echo "=== HALT-RESUME 6 (4.1 option 1: narrow instruction) $(date '+%F %T')"
cd /Users/arden/code/gridcalc-hybrid || exit 1
timeout 3600 opencode run --auto --print-logs --log-level INFO -m openai/gpt-5.5 \
  "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly. The project directory is /Users/arden/code/gridcalc-hybrid — resolve every .loopspace/... path relative to that directory, and do all work there. The run is halted; the human's decision on report.md is its option 1: resume task 4.1 with the narrow instruction — keep the Sheet-level cache/evaluator-side counting approach; remove or rewrite the test asserting a nonzero eval_count delta after an unrelated set (spec-incompatible with task 4.2); add coverage proving non-formula set calls leave eval_count unchanged; and supply credible failed-first TDD evidence from a test that actually fails before the implementation. Reset task 4.1 accordingly and resume. Routing unchanged: implementation dispatches go to the implementer agent, verification dispatches to the verifier agent. Follow the looprun Halt-Resume procedure with that decision."
echo "=== resume session 6 exited rc=$? — starting supervisor"
cd /Users/arden/code/ornith-loopspace-experiments/gridcalc || exit 1
exec sh hybrid_supervise.sh
