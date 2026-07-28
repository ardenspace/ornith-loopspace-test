# Progress notes

Status: **complete**. All 4 plan phases implemented in one pass (the engine
was built as its final form directly, rather than staged incrementally
phase-by-phase, since SPEC.md/PLAN.md were already fully approved and there
was no need to intentionally under-build early phases).

## Layout
- `gridcalc/parser.py` — hand-written tokenizer + recursive-descent parser.
  AST is plain tuples (`('int', n)`, `('ref', addr)`, `('neg', count, node)`,
  `('bin', op, l, r)`, `('func', name, tl, br)`, `('perr',)`). Never raises;
  unparseable input yields `('perr',)`.
- `gridcalc/evaluator.py` — pure, sheet-free: address/grid helpers, binary-op
  semantics (incl. truncating division), `evaluate(ast, ctx)`, and
  `direct_deps(ast)` (static R10 dependency extraction — no sheet access).
- `gridcalc/sheet.py` — `Sheet`: storage, address/type validation (R1/R2),
  lazy+cached evaluation with cycle detection via an `_in_progress` set
  (R9), and dependency-graph invalidation (`_deps`/`_rdeps`, R10/R11).
  `_ref_value`/`_range_values` are the (underscored, non-public) ctx
  interface the evaluator calls back into.
- `gridcalc/__init__.py` — raises `sys.setrecursionlimit` once (cites R12)
  instead of hand-rolling an iterative engine; spec explicitly sanctions
  this alternative.

## Design notes / non-obvious decisions
- Unary minus is collapsed into a single `('neg', count, node)` at parse
  time (loop, not recursion), so a ~510-deep `-` tower never builds a deep
  AST — sidesteps R12's tower stress case structurally rather than via the
  recursion-limit bump.
- R5's "textual left-to-right, first error wins" falls out for free from
  plain depth-first AST evaluation with precedence-correct trees — no
  separate flattening/reordering needed.
- Dependency invalidation: `_apply_set` always invalidates the edited
  cell's own cache (so identical-content re-sets still count as edits) and
  BFS-walks the *reverse* dependency graph to invalidate transitive
  dependents. Because evaluation is lazy, this alone gives the R10 bounds
  (irrelevant edit -> 0, relevant edit -> recompute only what's needed)
  without any separate "dirty" bookkeeping.
- `tests/test_differential.py` deliberately reimplements its own
  tokenizer/parser/naive evaluator from scratch (no import from
  `gridcalc.parser`/`gridcalc.evaluator`) per task 4.4's isolation
  requirement, and runs 1000 seeded 50-op sequences over a 5x5 region.

## Verification
`pytest -q` — 107 passed, ~0.15s. Covers R1-R12 across
tests/test_{address,store,parser,eval,errors,functions,cycles,counter,
incremental,bounds,differential}.py, matching PLAN.md's file list exactly.
