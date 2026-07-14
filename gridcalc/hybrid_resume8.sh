#!/bin/sh
# Halt 8 resume — decision: report option 1 for task 4.3 (ornith stays).
# Run detached: nohup sh hybrid_resume8.sh >> runner-logs/hybrid_supervise.log 2>&1 &
set -u

echo "=== HALT-RESUME 8 (4.3 option 1: targeted coverage) $(date '+%F %T')"
cd /Users/arden/code/gridcalc-hybrid || exit 1
timeout 3600 opencode run --auto --print-logs --log-level INFO -m openai/gpt-5.5 \
  "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly. The project directory is /Users/arden/code/gridcalc-hybrid — resolve every .loopspace/... path relative to that directory, and do all work there. The run is halted; the human's decision on report.md is its option 1: resume task 4.3 with the narrow instruction — add the verifier-requested within-limit multiplication-chain magnitude test near 2**63-1 (e.g. =3037000499*3037000499 expecting 9223372030926249001) and a stronger confinement test combining an unrelated >512-char formula with a boundary guarantee, while preserving credible failed-first evidence where behavior actually changes. Reset task 4.3 accordingly and resume. Routing unchanged: implementation dispatches go to the implementer agent (implementer-frontier stays limited to tasks 2.1 and 4.2), verification dispatches to the verifier agent. Follow the looprun Halt-Resume procedure with that decision."
echo "=== resume session 8 exited rc=$? — starting supervisor"
cd /Users/arden/code/ornith-loopspace-experiments/gridcalc || exit 1
exec sh hybrid_supervise.sh
