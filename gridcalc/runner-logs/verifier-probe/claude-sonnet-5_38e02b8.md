## VERDICT: FAIL

The suite is green (107/107) and covers the bulk of R1–R12 well — addressing, type coercion, error taxonomy, short-circuiting, cycles (mostly), the R12 bounds, and a real R11 differential harness at the required floor (1000×50). But several requirements that explicitly enumerate multiple input shapes are exercised through only one shape, and I confirmed by hand that the *un*-exercised shapes currently behave correctly — meaning the suite would not catch a regression in exactly those spots.

## MISSING COVERAGE

1. **R3 left-associativity of `additive`/`term`.** Spec requires `additive := term ((+|-) term)*` and `term := factor ((*|/) factor)*` to be left-associative. No test — unit or differential (all `FORMULA_TEMPLATES` in `test_differential.py` are single-operator, two-operand) — ever constructs a same-precedence chain of 3+ operands like `=10-3-2` or `=8/4/2`. A right-associative regression would silently pass the whole suite.
   - Literal case: `s.set("A1", "=10-3-2"); s.get("A1")` (also `"=8/4/2"`).
   - Currently handled correctly: yes (`10-3-2 == 5`, `8/4/2 == 1`, verified by execution).

2. **R3 empty parentheses.** Spec explicitly lists "empty parentheses ... fail the grammar: `#PARSE!`" as one of three named invalid forms, alongside the two that *are* tested (`=A1:B2`, `=SUM(A1)`). No test constructs `=()`.
   - Literal case: `s.set("A1", "=()"); s.get("A1")`.
   - Currently handled correctly: yes (`#PARSE!`, verified).

3. **R7 range ordering is a conjunction, tested only as a joint violation.** `SUM(B2:A1)` violates *both* column and row order simultaneously. No test isolates a single-dimension violation.
   - Literal cases: `s.set("Q1", "=SUM(B1:A2)")` (column violated, row fine) and `s.set("Q1", "=SUM(A2:A1)")` (row violated, column fine).
   - Currently handled correctly: yes, both return `#REF!` (verified) — but a bug that checked only one axis (e.g. `tc > bc` and forgot `tr > br_`, or vice versa) would slip past every existing range test.

4. **R10 dependency closure for `COUNT` range members.** Spec is explicit that RANGE members belong to the reference closure "SUM/MIN/MAX/COUNT alike, empty cells included" for invalidation purposes, even though R8 says COUNT never *evaluates* them. No test edits a cell that is only a member of a `COUNT` range and checks the `COUNT` formula's cached value/eval_count actually gets invalidated and recomputed.
   - Literal case: `s.set("Q1","=COUNT(A1:B2)"); s.get("Q1")` (→0) `; s.set("B2",5); s.get("Q1")` expect `1` with `eval_count` delta ≥1.
   - Currently handled correctly: yes (verified: result becomes `1`, delta `1`) — but this is exactly the seam where "COUNT doesn't evaluate members" could easily be (mis)implemented as "COUNT doesn't depend on members," which would break invalidation. Nothing pins that down.

5. **R10 eval_count delta on the *first* evaluation of `#PARSE!`/`#CYCLE!` formulas is never asserted.** `test_repeat_read_adds_zero_for_values_and_errors` only asserts the *second* `get` adds 0 relative to a baseline taken *after* the first `get` — it never asserts what that first delta actually was. A broken implementation that never counts PARSE/CYCLE starts at all (always 0) would pass this test unchanged.
   - Literal case: `s = Sheet(); s.set("A1","=a1"); before=s.eval_count; s.get("A1"); assert s.eval_count-before==1` (and same for `s.set("A1","=A1")` cycle case).
   - Currently handled correctly: yes, delta is 1 in both cases (verified).

6. **R9 cycle-through-range tested only for `SUM`, not `MIN`/`MAX`.** Spec names "a `SUM`/`MIN`/`MAX` range" as the enumerated cycle path; only `SUM` has a test (`test_cycle_through_range`).
   - Literal case: `s.set("A1","=MIN(A1:B1)"); s.set("B1",1); s.get("A1")`.
   - Currently handled correctly: yes (`#CYCLE!`, verified).

7. **R3 two-character-operator whitespace rejection tested only for `<=`.** Spec names all three (`<= >= <>`) as must-not-contain-whitespace; only `"1 < = 2"` is tested.
   - Literal cases: `s.set("A1","=1 > = 2")`, `s.set("A1","=1 < > 2")`.
   - Currently handled correctly: yes, both `#PARSE!` (verified).

8. **R1 non-`str` address argument to `set` is never tested** (only `get(5)`, `get(None)`, and `set(None, 1)` are). `set(5, 1)` is never constructed.
   - Literal case: `s.set(5, 1)`.
   - Currently handled correctly: yes, raises `ValueError` (verified).

## OTHER FINDINGS

- **The "independent" differential oracle in `test_differential.py` is structurally a near-clone of `gridcalc/parser.py`** (same tokenizer character-by-character logic, same recursive-descent shape, same tuple AST). The spec's engineer lens calls for cross-checking against "an independent naive full-recompute reference" specifically so a shared misunderstanding of the grammar can't hide from both. Because the reference tokenizer/parser was apparently written by copying the production one rather than re-deriving it from SPEC.md's grammar text, a bug in tokenization or precedence that exists in production is likely to be reproduced identically in the reference, so the differential suite would not catch it. This weakens the value of that 1000-seed run specifically for grammar-level defects (it's still a strong check for evaluator/cache/dependency-graph logic, which the reference does implement independently as a plain uncached recursive evaluator).
- Relatedly, because every differential `FORMULA_TEMPLATES` entry is a single binary op / single function call over two random single-cell refs, the fuzzer never generates parenthesized or multi-operator-chained formulas, so it doesn't backstop finding (1) either — the associativity gap is not covered by either the unit suite or the randomized suite.
