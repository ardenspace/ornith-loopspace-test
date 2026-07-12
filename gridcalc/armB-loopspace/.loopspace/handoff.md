# Handoff
version: 1
written: 2026-07-12
trigger: phase-boundary

## Where we are
Phase 3 complete. Phase 4 begins: Incremental recomputation.

## Next session must know
- Package structure: gridcalc/__init__.py exports Sheet; gridcalc/sheet.py holds Sheet; gridcalc/parser.py holds parse(); gridcalc/evaluator.py holds evaluate_formula()
- Test command: pytest -q (run from repo root)
- Stack: Python 3.10+ pure-logic library, stdlib-only runtime, pytest for tests
- Phase 3 built: complete R3 grammar including function calls (SUM/MIN/MAX/COUNT), range function semantics, circular-reference detection (#CYCLE!)
- Phase 3 exports: gridcalc.parser.parse, gridcalc.evaluator.evaluate_formula, gridcalc.sheet.Sheet — extended with function grammar, range functions, and cycle detection via cycle_set propagation

## Watch out for
- Phase 4 makes the engine lazy and dependency-aware with observable eval_count contract
- Phase 4.1 adds result caching and eval_count tracking; conservative invalidation (clear cache on every set) is acceptable
- Phase 4.2 replaces conservative invalidation with dependency-aware invalidation — this is the experiment's designed trap (heavy risk)
- Phase 4.3 hardens R12 bounds (32-deep parens, ~510-deep unary minus, 256-cell chain, magnitude bound)
- Phase 4.4 is test-only: seeded differential suite cross-checking against naive full-recompute reference
- Every phase 1-3 test AND every 4.1 test must pass unchanged in 4.2
- COUNT does not participate in cycle detection (A1 "=COUNT(A1:A1)" stays 1)
- Error strings (#PARSE!, #REF!, #TYPE!, #DIV!, #CYCLE!) are returned by get as ordinary str values, never exceptions
