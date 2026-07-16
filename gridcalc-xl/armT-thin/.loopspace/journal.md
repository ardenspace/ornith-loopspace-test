# Journal
version: 1

## [lead] plan
- Initial lead-mode arming session. Acceptance groups G1-G10 cover R1-R28 exactly once; no gaps or overlaps found.
- First build a minimal `gridcalc` package and tests for G1 cell storage/API basics, then gate G1 before moving to formula groups.
- Work through groups in spec order because later XL groups depend on the parser/evaluator core: G1, G2, G3, G4, G5, G6, G7, G8, G9, G10.
- Use direct implementation first to conserve the 60-dispatch budget; dispatch only for isolated verification or large independent test/reference work.
- Changed since last plan entry: first plan entry for the run.

## [lead] plan
- G1 has a ledger PASS. Move to G2 and replace the formula `#PARSE!` stub with a hand-written scalar parser/evaluator.
- Implement integers, references, parentheses, unary minus, arithmetic, comparisons, division truncating toward zero, `#REF!` for syntactically valid invalid references, and closed-grammar `#PARSE!` for unsupported forms.
- Preserve R5 left-to-right error/type short-circuiting as the evaluator shape, because G3 and G5 extend it.
- Defer ranges, functions, cycles, caching bounds, strings, copy, names, undo/redo, multi-sheet, persistence, and volatile behavior to their acceptance groups unless needed structurally.
- Changed since last plan entry: G1 passed; G2 is the active checkpoint.

## [lead] plan
- G2 gate failed once on NAME token classification: `AA1` and `FOO` must be undefined NAMEs with `#NAME!`, not parse errors.
- Repair parser identifier lexing to classify REF shape first, then NAME shape, and evaluate undefined names as `#NAME!`; keep full `define_name` binding semantics deferred to G6.
- Re-run local tests, add a regression for the gate finding, then re-gate G2.
- Changed since last plan entry: one G2 FAIL to repair.

## [lead] plan
- G2 has a ledger PASS. Move to G3 and extend the scalar parser to accept aggregate function calls with `RANGE-ARG`.
- Implement `SUM`, `MIN`, `MAX`, and `COUNT` over ranges, including row-major error ordering, empty-cell treatment, string `#TYPE!` fuel, invalid/misordered range `#REF!`, and COUNT's non-evaluating structural count.
- Keep the existing evaluation stack for cycle detection and ensure cycles through ranges propagate `#CYCLE!`.
- Add local tests for range ordering, empty ranges, invalid ranges, COUNT not evaluating, and direct/mutual/range cycles before gating.
- Changed since last plan entry: G2 passed; G3 is the active checkpoint.

## [halt] resolved — external gate verifier limit resolved by switching model; retry G3 gate

## [lead] plan
- G3 gate failed once on a lead-suite coverage gap, not source behavior: misordered ranges were tested only with both row and column reversed.
- Add regression assertions for row-only and column-only misordered ranges (`A2:A1`, `B1:A1`) and cover another aggregate (`MIN`) so an `or` to `and` mutant is caught.
- Re-run `pytest -q`, then re-gate G3.
- Changed since last plan entry: external blocker resolved; one G3 FAIL to repair in tests.

## [lead] plan
- Resumed session. G3 repair from the last gate FAIL is committed (candidate 53029fb): lead suite now asserts single-dimension misordered ranges (`A2:A1`, `B1:A1`) and `MIN(A2:A1)` → `#REF!`, closing the or→and mutation gap. Full suite green (15 passed), tree clean.
- The last G3 gate launch (gates.md, opened 03:19:00) was interrupted with no recorded verdict; prior G3 non-verdicts were errors (rc=0/rc=1), not FAILs, so only 1 FAIL is on the G3 budget.
- Action: re-run the G3 gate on the committed candidate. On PASS, advance to G4 (R10/R11/R12 — incremental recomputation). On FAIL, repair from findings and re-gate.
- Changed since last plan entry: repair committed; re-gating G3.

## [lead] plan
- G3 PASS (ledger 958c59a). G1/G2/G3 all gated. Active checkpoint: G4 (R10 incremental recompute + eval_count, R11 naive equivalence, R12 bounds).
- Implementation approach (direct, no dispatch — conserve budget):
  1. Persistent workbook-level result cache keyed (sheet,addr); eval_count += 1 only when a formula cell's computation is *started* (not on cache hit, not on in-progress cycle hit). Cached values/errors survive across gets.
  2. Static reference closure per formula (single REFs to grid cells + SUM/MIN/MAX/COUNT range members), forward+reverse dep maps; `set` invalidates target and transitively cascades to dependents via reverse edges (with edge cleanup so stale deps don't violate the irrelevant-edit +0 bound).
  3. R12 bounds: raise recursion limit once at import citing R12 (spec-sanctioned) so the 256-cell chain and ~500-deep unary tower don't RecursionError within bounds; native big ints for magnitude; within-bounds must not raise.
  4. COUNT stays structural (no eval, no counter) but its members are still closure members (R10).
  5. Cycle detection stays per-get via a visiting set threaded through compute; caching #CYCLE! is safe (any cell reading an in-progress cell is itself on the cycle → naive-correct).
- Lead tests before gating: differential harness (≥1000 seeded set/get sequences on 3 sheets × 12 addrs vs an independent naive full-recompute) for R11; directed R10 patterns (repeat-read +0, irrelevant-edit +0, relevant-edit ≥1, no-full-sheet-recompute ceiling, multi-ref dedup); R12 boundary (256-chain, 500-tower, 2**63 magnitude).
- Changed since last plan entry: G3 passed; G4 is the active checkpoint; existing eval_count assertions confirmed cache-compatible.

## [lead] plan
- G4 PASS (ledger 71ab2dd). Active checkpoint: G5 (R13-R15 strings, CONCAT/LEN, IF).
- Extend parser with no-escape string literals as primaries, `CONCAT(expr,...)`, `LEN(expr)`, and `IF(expr,expr,expr)` while preserving closed grammar for wrong arities.
- Extend evaluator typing: arithmetic/order comparisons require ints, equality supports same-type int/int or str/str, mixed equality is `#TYPE!`, and offenders short-circuit left-to-right.
- Implement `CONCAT` decimal int rendering and `LEN` string/rendered-int lengths; implement `IF` with condition first, string condition `#TYPE!`, and only selected branch evaluation.
- Update static refs so IF closure includes condition and both branches, while runtime evaluation skips the untaken branch.
- Changed since last plan entry: G4 passed; G5 is the active checkpoint.

## [lead] plan
- G5 gate failed once on lead-suite coverage only: implementation handles string ordering/unary-minus as `#TYPE!`, but tests did not guard those branches.
- Add assertions for all four string orderings and unary-minus on string, then re-run `pytest -q` and re-gate G5.
- Changed since last plan entry: one G5 FAIL to repair in tests.

## [lead] plan
- Context-threshold handoff after G5 PASS. Newest ledger PASS is G5; G6 is next.
- Next session should start with G6 (R16-R18): `$` absolute references, `copy`, and per-sheet named ranges. Existing parser does not yet accept `$` marks or bind names; `copy` and `define_name` still raise `NotImplementedError`.
- Preserve current incremental engine behavior from G4: set invalidates target and transitive dependents; static refs currently cover refs, range members, CONCAT/LEN, and all IF branches.
- Changed since last plan entry: G5 passed; stopping for context threshold before G6.

## [lead] plan
- Resumed from fresh handoff at gate:G5; handoff is fresh, branch matches, run_status is executing. Active checkpoint: G6 (R16-R18).
- Implement directly to conserve dispatch budget: parser/evaluator support `$`-marked refs/range endpoints; sheet `copy(src,dst)` with relative rewrites and `#REF!` replacement; per-sheet `define_name` bindings for primary/range use.
- Keep G8 qualified-address behavior deferred unless G6 gate requires it; G6 tests will focus on unqualified semantics from R16-R18.
- Add local mutation-resistant tests for absolute vs relative copy, parse-error copy byte-for-byte, out-of-grid replacement, literal copy atomicity, name primary/range resolution, undefined names, and define_name invalidation.
- Changed since last plan entry: resumed after context threshold; no new gate attempts yet.

## [lead] plan
- G6 gate failed once on a real copy-rewriter bug: maximal NAME tokens containing ref-looking suffixes (`AA1`, `DATA1`) were partially rewritten.
- Repair `_rewrite_formula_for_copy` to lex maximal `[A-Z0-9_$_]` runs outside strings and shift only when the whole run is an optionally `$`-marked REF; otherwise preserve the run byte-for-byte.
- Add regression tests for primary NAME and range-arg NAME copy preservation, then re-run `pytest -q` and re-gate G6.
- Changed since last plan entry: one G6 FAIL to repair in source and tests.

## [lead] plan
- G6 PASS (ledger 923c030). Active checkpoint: G7 (R19-R20 undo/redo and caches/counters).
- Implement one workbook journal for successful `set`, `copy`, `define_name`, and `add_sheet`; failed calls and `get` stay unjournaled.
- Store enough before/after state for undo and redo, clear redo on new journaled operations, and keep undo/redo themselves from appending entries.
- Restore cells/names/sheets via internal helpers that invalidate caches but never decrement eval_count; sheet handles should raise while their sheet is absent and work again after redo/re-add.
- Add tests for LIFO undo/redo, redo clearing, failed-call non-journaling, cache invalidation after undo/redo, and handle invalidation/restoration.
- Changed since last plan entry: G6 passed; G7 is active.

## [lead] plan
- G7 PASS (ledger baeda21). Active checkpoint: G8 (R21-R23 workbook/multi-sheet).
- Implement parser/evaluator support for sheet-qualified refs/ranges (`S!A1`, `S!A1:B2`), including absent-sheet `#REF!`, cross-sheet cycles, and per-owner eval_count increments.
- Extend `copy` and `define_name` arguments to accept no-whitespace qualified addresses/ranges; copy into destination sheet while formula host semantics re-resolve unqualified refs and names there.
- Ensure `sheet_names` order, handle invalidation/restoration, per-name eval_count persistence, and public API surface checks hold.
- Add local tests for cross-sheet refs/ranges/cycles/counters, qualified copy/name args, and public-surface/handle lifecycle before gating.
- Changed since last plan entry: G7 passed; G8 is active.

## [lead] plan
- G8 gate failed with two implementation bugs and one lead-suite gap.
- Repair copy rewriter so sheet qualifiers matching REF shape (`S2`) are never shifted; only qualified REF/range endpoints shift, and out-of-grid qualified constructs become plain `#REF!`.
- Repair `add_sheet` / undo / redo touch sets by invalidating formulas that mention the affected sheet qualifier.
- Add eval_count resumption coverage for fresh re-add and redo-restore under the same sheet name.
- Changed since last plan entry: one G8 FAIL to repair.

## [lead] plan
- G8 PASS (ledger 233f97a). Active checkpoint: G9 (R24-R25 persistence round-trip).
- Add `to_json` as a pure observation: serialize sheet order, stored raw cells byte-for-byte, name bindings, and clock; do not evaluate, count, journal, or preserve caches.
- Add `Workbook.from_json` with strict schema validation, rejecting non-strings, invalid JSON, floats/bools/wrong shapes, invalid sheet names/addresses/name bindings/targets, and returning a fresh workbook with empty journal and zero eval_count.
- Add tests for semantic round-trip, raw formula/copy/name preservation, reset counters/journal, no eval during `to_json`, and adversarial invalid inputs.
- Changed since last plan entry: G8 passed; G9 is active.

## [lead] plan
- G9 gate failed with one source naming issue and two test-floor gaps.
- Rename the evaluator method/calls so runtime source contains no literal `eval(`, satisfying the spec's static security grep.
- Expand `from_json` adversarial tests to at least 30 cases covering all mandated categories, including NaN/Infinity/1.0, invalid top-level shapes, invalid names/addresses, non-str inputs, and deep nesting.
- Add a seeded 1000-sequence length-50 round-trip differential harness over the current supported operation set; interleave `to_json`/`from_json` and compare values over the 3-sheet/12-address pool after each sequence.
- Changed since last plan entry: one G9 FAIL to repair.

## [halt] resolved — verifier usage limit resolved; retry G9 gate

## [lead] plan
- G9 PASS (ledger 30d4593). Active checkpoint: G10 (R26-R28 volatile recalculation and XL bounds).
- Implement `Workbook.clock`, journaled `advance_clock`, parser/evaluator support for `NOW()`, and clock persistence.
- Add static volatility analysis: formula cells whose closure contains a `NOW()` call are touched by clock edits; invalidate volatile cells/dependents on `advance_clock`, undo, and redo.
- Add local tests for NOW values, repeat-read cache stability, clock edit recomputation only for volatile closures, undo/redo clock restoration, `NOW` inside strings not volatile, and persistence of nonzero clock.
- Changed since last plan entry: G9 passed; G10 is active.

## [lead] plan
- G10 gate failed once: overlong formula copy rewrites past R28's mutating-op boundary, differential harness lacks advance_clock/NOW, and static volatility for NOW in unselected IF branch lacks lead-suite coverage.
- Add R12(a) helper and require formula source within length/nesting limits before copy rewrite; overlong or over-nested formula sources copy byte-for-byte.
- Extend G9 differential harness to include clock/NOW now that G10 implemented clock, with naive clock journaling and round-trip clock persistence.
- Add G10 regression for `=IF(1,2,NOW())` invalidation after clock edit.
- Changed since last plan entry: one G10 FAIL to repair.
