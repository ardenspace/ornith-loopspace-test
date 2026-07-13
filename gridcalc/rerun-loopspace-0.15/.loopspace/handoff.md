# Handoff — Phase 2 → Phase 3
trigger: phase-boundary

## Phase 2 Summary
Phase 2 (Formulas — core grammar and evaluation) verified and complete. Parser + evaluator with arithmetic, references, comparisons, and error propagation.

## Next session must know
- Phase 3 builds ranges, functions (SUM/MIN/MAX/COUNT), and cycle detection on top of Phase 2
- Phase 3 tasks: 3.1 (function grammar + SUM/MIN/MAX/COUNT), 3.2 (circular-reference detection)
- Task 3.1 is heavy risk — grammar closure with function calls, range semantics, visit order
- Task 3.2 is heavy risk — in-progress-set state machine with partial-failure branches
- Phase 2 tests must survive phase 3 unchanged (function syntax added in 3.1)
- R12 sizing constraints still apply (512-char formulas, 32-deep parens, 256-cell chains)

## Watch out for
- Task 3.1: function calls are primaries and compose (=SUM(A1:B2)+1, =-MAX(A1:A2)*2); whitespace around ":" is legal
- Task 3.1: #PARSE! on unknown names, lowercase, ranges outside functions, empty parens
- Task 3.1: visit order row-major; first error in visit order wins at value level
- Task 3.1: SUM skips empty cells and is 0 on all-empty range; MIN/MAX use non-empty numeric contributions
- Task 3.1: COUNT counts non-empty cells without evaluating them, never errors beyond invalid range's #REF!
- Task 3.2: self-reference, mutual cycles, through SUM/MIN/MAX ranges; COUNT does not participate in cycles
- Task 3.2: breaking the cycle with a set recovers; cells off the cycle referencing one return #CYCLE!
