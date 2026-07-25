# Handoff
version: 1
written: 2026-07-26
trigger: phase-boundary
position: 10.3

## Where we are
Phase 10 is verified on `loopspace/gridcalc-xl/phase-10`. All planned tasks are complete; the next looprun step is run-complete state finalization.

## Next session must know
- Task 10.1 passed at `a7f7bd5` (`loopspace: task 10.1 — NOW() function`).
- Task 10.2 passed at `f3629f9` (`loopspace: task 10.2 — Volatile invalidation and warm bound`).
- Task 10.3 passed at `6b4f0a7` (`loopspace: task 10.3 — XL bounds and final randomized floor`).
- Phase 10 boundary verification passed with probes in `tests/probes_phase_10.py`; full suite green (`4137 passed`).

## Watch out for
- Preserve user `opencode.json` change if it appears; it is intentionally excluded from loopspace commits.
- Existing untracked loopspace artifacts from earlier sessions should not be committed or reused: `.loopspace/task-6.3-report.md` and `.loopspace/task-9.2-report.md`.
- Phase 9 structure-note: `tests/test_persistence.py` and `tests/test_persistence_security.py` duplicate JSON payload/adversarial cases; acceptable, but centralize if maintenance grows.
