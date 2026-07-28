Suite is green (107 passed). It is nonetheless a failing suite: three requirements have concrete in-bounds inputs the implementation gets wrong, and no test constructs any of them.

## 1. VERDICT: **FAIL**

## 2. MISSING COVERAGE

**1. R3 / R1 — `INT` is "one or more ASCII digits" (`0`-`9` only; no other Unicode digits anywhere in this spec)**

```python
def test_non_ascii_digits_are_parse_error():
    s = Sheet()
    s.set("A1", "=١٢")            # U+0661 U+0662, Arabic-Indic "12"
    assert s.get("A1") == "#PARSE!"
```
(c) **Implementation is wrong.** Returns `12`. `parser._tokenize` uses `c.isdigit()`, which is true for every Unicode decimal digit, and `int()` then happily converts them. No test in `test_parser.py` or anywhere else feeds a non-ASCII character to the tokenizer. Same hole in `REF` digits and in the whitespace class (only `" "`/`"\t"` are skipped, which is correct — but nothing pins it).

**2. R2 / R5 — `set` accepts any `str`; formula errors are in-band, never exceptions**

```python
def test_set_accepts_str_with_superscript_digit():
    s = Sheet()
    s.set("A1", "=²")             # U+00B2
    assert s.get("A1") == "#PARSE!"
```
(c) **Implementation is wrong.** `set` raises `ValueError: invalid literal for int() with base 10: '²'`. `'²'.isdigit()` is `True` so the tokenizer emits an `INT` token, then `parse_primary` calls `int("²")`, which raises `ValueError` — not `_ParseError`, so it escapes `parse()`'s `except` and propagates out of `set`. `test_store.py::test_invalid_raw_types_raise` only exercises non-`str` types; nothing checks that an arbitrary `str` is always storable. Same for `"=1+₁"`, `"=½"`.

**3. R12 — a within-bounds evaluation (≤512 chars, ≤32 paren nesting, ≤256 formula cells) must not raise; "`RecursionError` within R12 bounds is a bug"**

```python
def test_256_chain_of_84_char_formulas_does_not_raise():
    def addr(i): return chr(ord("A") + i // 99) + str(i % 99 + 1)
    s = Sheet()
    s.set(addr(0), 1)
    for i in range(1, 256):
        s.set(addr(i), "=" + addr(i - 1) + "+0" * 40)   # 84 chars, nesting depth 0
    assert s.get(addr(255)) == 1
```
(c) **Implementation is wrong.** `RecursionError`. `tests/test_bounds.py` tests each R12 clause in *isolation* — a 256-cell chain of 6-char formulas, a 500-minus tower in one cell, 32 nested parens in one cell — and never combines cell depth with formula width. `evaluate` recurses once per left-associative operator, so a chain hop costs ~(2 + operators) frames; at 40 `+0` terms per cell, 256 cells needs ~31k frames against the limit of 10000 set in `gridcalc/__init__.py:10`. The breaking point is between 30 and 40 trailing terms (64-char formulas pass, 84-char formulas fail) — nowhere near the 512-char ceiling the spec grants. The 32-deep-paren-plus-256-chain case passes but only at ~9000 frames, i.e. it is also inside the margin.

**4. R12 — "the damage is confined: `set` always succeeds per R2 (it never evaluates)"**

```python
def test_set_always_succeeds_on_deeply_nested_formula():
    s = Sheet()
    s.set("A1", "=" + "(" * 5000 + "1" + ")" * 5000)
```
(c) **Implementation is wrong**, on the reading that the `set`-always-succeeds clause survives out-of-bounds content. `RecursionError` from `_Parser.parse_primary` → `parse_expr` (4 frames per nesting level). `test_bounds.py::test_out_of_bounds_formula_elsewhere_does_not_break_confined_gets` uses a *flat* 1000-term formula, which the parser handles with iterative loops, so it never touches this path. This one is arguable — R12 also says out-of-bounds behaviour is unspecified — but the flat-only test means nobody made the call deliberately. (Post-failure sheet state is fine; subsequent gets still work.)

**5. R10 — "hitting an already-in-progress cell does not start a second computation of it" / shared dependency counted once**

```python
def test_diamond_dependency_counted_once():
    s = Sheet()
    s.set("A1", 1); s.set("B1", "=A1+1"); s.set("C1", "=A1+2"); s.set("X1", "=B1+C1")
    assert s.get("X1") == 5
    assert s.eval_count == 3        # X1, B1, C1 — not 4

def test_mutual_cycle_counts_each_cell_once():
    s = Sheet()
    s.set("A1", "=B1"); s.set("B1", "=A1")
    s.get("A1")
    assert s.eval_count == 2
```
(c) Handled correctly (3 and 2). But every counter test in `test_counter.py`/`test_incremental.py` uses a *linear* chain; no test has two paths converging on one cell, which is exactly the shape the cache exists for, and no test pins the in-progress clause to an exact count.

**6. R8 — "COUNT ... never yields an error (beyond R7's `#REF!` for an invalid range itself)"**

```python
def test_count_on_invalid_range_is_ref_error():
    s = Sheet()
    s.set("Q1", "=COUNT(B2:A1)")
    assert s.get("Q1") == "#REF!"
```
(c) Handled correctly. `test_functions.py::test_ref_error_cases` parametrises `SUM` only; `COUNT` returns before the `#REF!` check in a plausible refactor of `_range_values` (the ordering in `sheet.py:124-127` is what saves it, and nothing guards that ordering).

**7. R9 — cycle "through a `SUM`/`MIN`/`MAX` range"**

```python
def test_cycle_through_min_and_max_ranges():
    for fn in ("MIN", "MAX"):
        s = Sheet()
        s.set("A1", f"={fn}(A1:B1)"); s.set("B1", 1)
        assert s.get("A1") == "#CYCLE!"
```
(c) Handled correctly. `test_cycles.py::test_cycle_through_range` covers `SUM` only. Likewise `test_counter.py::test_range_short_circuit_excludes_later_members` covers `SUM` only — `MIN`/`MAX` short-circuit counting (`eval_count == 2`) is never asserted.

**8. R10 — reference closure includes `COUNT` range members ("`SUM`/`MIN`/`MAX`/`COUNT` alike")**

```python
def test_count_range_member_edit_is_relevant():
    s = Sheet()
    s.set("A1", 1); s.set("Q1", "=COUNT(A1:B2)")
    assert s.get("Q1") == 1
    s.set("B2", 9)                  # empty -> non-empty, changes COUNT
    before = s.eval_count
    assert s.get("Q1") == 2
    assert s.eval_count - before >= 1
```
(c) Handled correctly. `test_incremental.py::test_range_closure_includes_members_empty_included` uses `SUM`. `COUNT` is the distinctive case: it is the only function whose result changes on an empty→non-empty transition, and it is also the one exempted from evaluation, so a stale-cache bug there is uniquely easy to introduce.

**9. R3 — "empty parentheses ... fail the grammar"** (named verbatim in the spec)

```python
@pytest.mark.parametrize("f", ["=SUM()", "=()"])
def test_empty_parens_are_parse_error(f): ...
```
(c) Handled correctly (`#PARSE!` both). `test_functions.py::test_parse_error_cases` lists `=SUM(A1)`, `=A1:B2`, `=SUM((A1:B2))` but not the empty-paren forms the spec calls out in the same sentence.

**10. R3 — "spaces and tabs ... including between a function name and its `(`"** (named verbatim)

```python
def test_whitespace_between_func_name_and_paren():
    s = Sheet(); s.set("A1", 1); s.set("B1", 2)
    s.set("C1", "=SUM (A1:B1)")
    assert s.get("C1") == 3
```
(c) Handled correctly. Only the around-the-colon half of that sentence is tested (`=SUM(A1 : B1)`). Also untested: leading/trailing whitespace in the whole formula (`"= 1 + 2 "` → `3`).

**11. R3 — "the two-character operators `<= >= <>` must not contain whitespace"**

```python
@pytest.mark.parametrize("f", ["=1 > = 2", "=1 < > 2"])
def test_split_two_char_operators_are_parse_error(f): ...
```
(c) Handled correctly. `test_parser.py` covers `"1 < = 2"` only — one of the three operators the spec names.

**12. R7 — TL col ≤ BR col **and** TL row ≤ BR row are two separate conditions**

```python
@pytest.mark.parametrize("f", ["=SUM(B1:A1)", "=SUM(A2:A1)"])   # col-only, row-only
def test_single_axis_misordered_range_is_ref_error(f): ...
```
(c) Handled correctly. Every existing mis-ordered-range test uses `B2:A1`, which violates both conditions at once — it passes even if one of the two comparisons in `evaluator._valid_range` is deleted.

**13. R6 — "This applies in every context — arithmetic, comparison, and bare"**

```python
def test_bare_reference_to_empty_cell_is_zero():
    s = Sheet(); s.set("A1", "=Z9")
    assert s.get("A1") == 0
```
(c) Handled correctly. The empty-cell rule is tested only in arithmetic (`"=Z9+1"` → `1`); the bare context is tested only for the string case. Nothing distinguishes "empty contributes `0`" from "empty contributes `None`, and `None + 1` happened to work".

**14. Non-Goals — a string literal whose text equals an error string is a string, never an error value**

```python
def test_error_looking_string_literal_is_type_fuel():
    s = Sheet(); s.set("A1", "#DIV!"); s.set("B1", "=A1")
    assert s.get("A1") == "#DIV!"
    assert s.get("B1") == "#TYPE!"
```
(c) Handled correctly. Exercised only incidentally, because `"#DIV!"` happens to be in `test_differential.py`'s `LITERALS`; no named test, and a differential failure here would surface as an opaque seed dump.

**15. R4 — truncation toward zero, both operands negative**

```python
def test_division_both_negative(): assert ev("-7/-2") == 3
```
(c) Handled correctly. Three of the four sign combinations are tested; `(-,-)` is not.

## 3. OTHER FINDINGS

- **The R11 differential oracle is not independent.** `tests/test_differential.py`'s `_ref_tokenize` / `_RefParser` are a near-verbatim transcription of `gridcalc/parser.py` — same `c.isdigit()` call, same letters-then-digits branch, same `len(letters) != 1` check, same operator dispatch. The spec asks for "an independent naive full-recompute reference"; what is there is an independent *evaluator* bolted to a *copied* front end. Finding 1 proves the consequence: both sides accept `=١٢` as `12`, so 1000 seeds agree on a wrong value. Any tokenizer or grammar defect is structurally invisible to this test.
- **The differential harness's formula space is one level deep.** All 14 `FORMULA_TEMPLATES` are `{a} op {b}` or a single function call over two addresses — no parentheses, no nested function calls, no chained comparisons, no whitespace variation, no stacked unary minus beyond `=-{a}`. I re-ran the same harness with depth-3 generated expressions (parens, unary stacks, tab/space noise, out-of-grid endpoints) over 4000 seeds × 60 ops and found zero mismatches, so this is not currently masking a live defect — but it is a much thinner net than the spec's "any sequence of `set`/`get`" implies.
- **`sys.setrecursionlimit` is the sanctioned-but-unverified escape hatch.** The Engineer Lens permits raising the limit "only if ... the R12 chain and tower cases pass". They pass individually; finding 3 shows the limit is not sized for the R12 envelope. `gridcalc/__init__.py:6` also cites `Sheet.ref_value`, which does not exist (the method is `_ref_value`).
- **Duplicate test.** `test_functions.py::test_count_of_count_self_reference_is_one_not_cycle` and `test_cycles.py::test_count_does_not_participate_in_cycle_detection` are byte-identical bodies. The suite's 107 count overstates coverage by one.
- **`test_store.py::test_formula_string_accepted_without_error` asserts nothing** and carries a stale `# phase 1: never call get() on it` comment. It passes if `set` returns garbage.
- **No test pins the public API surface.** The Engineer Lens makes `Sheet` with exactly `set`/`get`/`eval_count` normative ("additional public methods are scope creep"), and nothing checks it. Cheap to assert; currently the only enforcement is review.
