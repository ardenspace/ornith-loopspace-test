# Handoff
version: 1
written: 2026-07-16
trigger: context-threshold
position: gate:G5

## Where we are
Lead mode is executing with gates G1-G5 PASS. The implementation currently covers cell storage, scalar formulas, ranges/functions/cycles, incremental recomputation, and strings/CONCAT/LEN/IF. Next acceptance group is G6 (R16-R18).

## Next session must know
- Run status remains `executing`; do not use `report.md` halt-resume.
- Start every session with a new `## [lead] plan` entry before work.
- Next target: G6, implementing `$` reference marks, `copy(src,dst)` rewriting, `#REF!` replacement, and per-sheet `define_name` bindings.
- `copy` and `define_name` currently raise `NotImplementedError`; parser currently lacks `$` reference marks and live name bindings.
- Local suite command is `pytest -q`; latest gate PASS is G5.
- Dispatches used: 0 of 60.

## Watch out for
- Gate errors can still occur from verifier output parsing/timeouts; retry once for transient exit-3 errors, but ledger PASS/FAIL remains authoritative.
- G3/G5 had test-coverage-only FAILs; gates expect mutation-killing lead tests, not just correct implementation.
- Do not edit `.loopspace/spec.md` or `.loopspace/gates.md`; gates.md is gate-script-only.
