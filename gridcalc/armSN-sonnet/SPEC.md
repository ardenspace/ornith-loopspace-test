# Spec: gridcalc
version: 1
status: approved

## Overview
`gridcalc` is a small, disposable pure-logic Python library providing one
class, `Sheet`: an in-memory spreadsheet engine with integer arithmetic
formulas, cell/range references, range functions, circular-reference
detection, and incremental recomputation with an observable evaluation
counter. It is a throwaway fixture — no I/O, no persistence, no UI. Its
difficulty is the dependency-aware recomputation engine; the behavior is
fully specified below.

## Goals
- One class, `Sheet`, with `set(addr, raw)`, `get(addr)`, and a cumulative
  `eval_count` property.
- Exact integer semantics: every operation's result is fully determined by
  this spec — no floats, no coercion, no locale/rounding questions. A
  formula's result is always an `int` or an error string, never a string
  value and never `None`.
- Incremental recomputation that is *behaviorally observable* through
  `eval_count`, while producing values identical to a naive full
  recomputation.

## Non-Goals
- No cell deletion/clearing API, no floats, no string literals or string
  operators inside formulas (strings exist only as literal cell values),
  no absolute references (`$`), no multi-letter columns or rows above 99,
  no case-insensitive parsing, no persistence, no concurrency, no UI, no
  performance requirements beyond the `eval_count` bounds in R10 and the
  depth bounds in R12.
- `get`'s return value alone does not distinguish a genuine error value
  from a string-literal cell whose text happens to equal an error string
  (e.g. the literal `"#DIV!"`); semantics are defined by stored content —
  a string literal is always a string (so it is `#TYPE!` fuel in numeric
  contexts, never treated as an error value), and no API is provided to
  tell the two apart from the returned text.

## Company Lens
Throwaway experiment fixture for Experiment W (multi-session drift A/B,
see the experiments monorepo `gridcalc/grading/EXPERIMENT.md`). Success is
not adoption but *gradability*: a held-out oracle must be authorable from
this spec alone. Deliberate difficulty (the full grammar including
comparisons, and the R10 incrementality contract) is a design goal of the
experiment, not gold-plating. Cost bound: one unattended overnight run.
MVP scope is exactly R1-R12 — nothing more.

## User Lens
The only consumers are test authors (the run's own pytest suite and the
held-out oracle). They need: a minimal two-method-plus-property API,
formula errors as plain return values (never exceptions during
evaluation, within R12 bounds), and deterministic results for arbitrary
interleavings of `set`/`get`. Convenience beyond that is scope creep.

## Engineer Lens
- Stack: Python 3.10+; runtime code uses the stdlib only (zero external
  dependencies); tests use `pytest -q` and nothing else (no hypothesis or
  other test-time dependencies). Package name `gridcalc`;
  `from gridcalc import Sheet` works from the repo root.
- Security: no I/O, no eval/exec of Python, no network — the formula
  parser must be hand-written (no `eval()` on user input, even sandboxed).
- Error handling: *programmer* errors (invalid address argument,
  unsupported raw type) raise `ValueError` at the API boundary; *formula*
  errors are in-band error string values (R5) and never raise within the
  R12 depth bounds.
- Testing: every requirement below is phrased to be machine-checkable.
  Incrementality (R10) is checked through `eval_count` deltas only — no
  timing assertions. R11 is verified differentially: randomized `set`/
  `get` sequences cross-checked against an independent naive
  full-recompute reference, with fixed (or logged) random seeds so any
  failure is reproducible; floor: at least 1000 seeded sequences of
  length ≥ 50 over a bounded cell region, zero mismatches.
- R12's guarantees are intended difficulty: they rule out naive
  recursion under CPython's default limit in both the evaluator (the
  256-cell chain) and the parser (a ~500-deep unary-minus tower fits in
  512 chars). An iterative engine is preferred; raising the recursion
  limit is acceptable only if it is set once at import, cites R12 in a
  comment, and the R12 chain and tower cases pass. `RecursionError`
  within R12 bounds is a bug.
- Over-engineering boundary: the public API is exactly `Sheet` with
  `set`, `get`, and `eval_count` — additional public methods are scope
  creep. No plugin systems, no AST visitors beyond what the grammar
  needs, no caching layers beyond the one dependency graph R10 requires.

## Designer Lens
Not applicable: no UI surface.

## Requirements

Addressing and storage:
- R1: A valid address is exactly one uppercase letter `A`-`Z` followed by
  the ASCII digits (`0`-`9` only; no other Unicode digits anywhere in
  this spec) of an integer `1`-`99` with no leading zeros (`A1`, `Z99`).
  `set`/`get` raise `ValueError` when the address argument is not a `str`
  (e.g. `get(5)`, `get(None)`) or is a `str` that is not a valid address
  (lowercase, `A0`, `A01`, `A100`, `AA1`, empty, internal or
  leading/trailing whitespace). A `get` that raises `ValueError` leaves
  all observable state — contents, caches, `eval_count` — unchanged.
- R2: `set(addr, raw)` accepts `raw` of type `int` (stored as a number)
  or `str` (starting with `=` → stored as a formula; otherwise a string
  literal). `bool` raw raises `ValueError` despite being an `int`
  subclass; instances of other `int` subclasses and of `str` subclasses
  are accepted wherever an `int`/`str` is (as `addr` or `raw`) and are
  normalized on storage — `get` returns plain `int`/`str` values. Any
  other type raises `ValueError`. `set` returns `None` on success.
  A `set` that raises `ValueError` leaves the sheet — contents,
  `eval_count`, and all observable state — unchanged. `set` on an
  occupied cell replaces its content. `get(addr)` on a never-set cell returns
  `None`; on a literal cell it returns the stored `int` or `str`
  unchanged; on a formula cell it returns the formula's evaluated result
  (an `int` or an error string, per R3-R9).

Formula grammar (the text after the leading `=`):
- R3: The grammar, complete and closed — any formula text it does not
  derive evaluates to `#PARSE!` (including the empty formula `=`):
  - `expr    := additive ( CMP additive )*` where `CMP` is one of
    `= <> < <= > >=`; comparisons are left-associative and yield the
    integers `1`/`0` — there is no boolean type (`=1<2<3` is `(1<2)<3`,
    i.e. `1`). Semantics: `=` is integer equality, `<>` inequality,
    `< <= > >=` the usual integer orderings; each yields `1` when the
    relation holds, else `0`.
  - `additive := term ( (+|-) term )*`, left-associative.
  - `term    := factor ( (*|/) factor )*`, left-associative.
  - `factor  := - factor | primary` — unary minus stacks (`=--1` is `1`,
    `=2--3` is `5`).
  - `primary := INT | REF | FUNC ( RANGE ) | ( expr )` — a function call
    is an ordinary primary and composes as a sub-expression
    (`=SUM(A1:B2)+1`, `=-MAX(A1:A2)*2` are legal).
  - `INT`: one or more ASCII digits; leading zeros are allowed and
    carry no meaning (`=007` is `7`).
  - `REF`: one uppercase letter `A`-`Z` followed by one or more ASCII
    digits. (Validity of what it denotes is R6's job, not the parser's.)
  - `FUNC`: exactly `SUM`, `MIN`, `MAX`, or `COUNT`, uppercase. Any other
    identifier — unknown names (`AVG`), lowercase or mixed case (`sum`,
    `a1`), multi-letter non-function names (`AA1`) — fails the grammar:
    `#PARSE!`.
  - `RANGE := REF : REF` — a range may appear only as the sole argument
    of a function call; a range anywhere else (`=A1:B2`,
    `=SUM((A1:B2))`), a function with no colon in its argument
    (`=SUM(A1)`), and empty parentheses all fail the grammar: `#PARSE!`.
  - Whitespace: spaces and tabs are allowed before/after any token,
    including between a function name and its `(` and around the `:` of
    a range (`:` is a token; `=SUM(A1 : B2)` is legal). The
    two-character operators `<= >= <>` must not contain whitespace
    (`=1 < = 2` is `#PARSE!`).
- R4: Division is integer division truncating toward zero: `=-7/2` is
  `-3`, `=7/-2` is `-3`, `=7/2` is `3`. Division by zero evaluates to
  `#DIV!`.
- R5: Error values are exactly the strings `#PARSE!`, `#REF!`, `#TYPE!`,
  `#DIV!`, `#CYCLE!`, returned by `get` as ordinary `str` values (never
  exceptions, within R12 bounds). Operands are evaluated depth-first in
  the textual left-to-right order they appear in the formula source; the
  first error encountered in that order is the formula's result (in
  `=A1+B1*C1` the order is `A1`, `B1`, `C1`), and evaluation
  short-circuits there: operands textually after the first error are not
  evaluated (observable through R10's counter — in `=1/0+Y1` with `Y1` a
  formula cell, `Y1`'s computation never starts).
- R6: Every reference in a formula is read *numerically*: a number cell
  contributes its value; an empty (never-set) cell contributes `0`; a
  string-literal cell contributes `#TYPE!`; a formula cell contributes
  that formula's result (int or error). This applies in every context —
  arithmetic, comparison, and bare (`=A1` with `A1` holding the string
  `"hi"` is `#TYPE!`; with `A1` empty it is `0`). A `REF` token whose
  digits have a leading zero or denote a row outside `1`-`99` (`A01`,
  `A0`, `A100`) parses fine but denotes no grid cell: it evaluates to
  `#REF!`.

Ranges, functions, cycles:
- R7: A range `TL:BR` is valid when both endpoints denote grid cells
  (else `#REF!`, same rule as R6) and TL's column ≤ BR's column and TL's
  row ≤ BR's row (else `#REF!`). Range cells are visited row-major
  (`A1, B1, A2, …` for `A1:B3`). For `SUM`/`MIN`/`MAX`, formula cells in
  the range contribute their evaluated result; the first error value in
  visit order (whether from a formula cell or the `#TYPE!` of a
  string-literal cell) is the function's result, and evaluation
  short-circuits there — members after it are not evaluated (observable
  through R10's counter, same rule as R5).
- R8: Over the *non-empty* cells of a valid range (empty cells contribute
  nothing to any function): `SUM` adds the numeric contributions and is
  `0` on an all-empty range; `MIN`/`MAX` take the least/greatest numeric
  contribution and are `#TYPE!` on an all-empty range. `COUNT` is purely
  structural: it returns the number of non-empty cells (number, string,
  and formula cells all count) *without evaluating anything* — it never
  yields an error (beyond R7's `#REF!` for an invalid range itself),
  never increments `eval_count` for range members, and its range
  members do not participate in cycle detection (`A1` holding
  `=COUNT(A1:A1)` is `1`, not `#CYCLE!`).
- R9: Circular references: if evaluating a cell requires the value of a
  cell whose evaluation is already in progress — directly, mutually, or
  through a `SUM`/`MIN`/`MAX` range — that read contributes `#CYCLE!`.
  Consequently every cell on the cycle evaluates to `#CYCLE!` for that
  `get`, and cells off the cycle that depend on one receive `#CYCLE!`
  by R5/R6/R7 propagation.

Incremental recomputation:
- R10: `eval_count` is a cumulative `int` property, starting at `0`.
  `set` never evaluates formulas and never changes `eval_count`;
  evaluation happens only inside `get` (lazy). During a `get`,
  `eval_count` increases by exactly 1 for each formula cell whose value
  computation is *started* (error results — `#PARSE!`, `#CYCLE!`
  included — count the same as numbers; hitting an already-in-progress
  cell does not start a second computation of it). Reads of literal or
  empty cells never increment it. Error results are cached like values.
  The *reference closure* of a formula cell X is the least set
  containing X itself and, for every formula cell in the set, every cell
  its formula references directly — each single `REF` and every cell
  covered by any `RANGE` argument (`SUM`/`MIN`/`MAX`/`COUNT` alike,
  empty cells included). It is a transitive closure (least fixed point):
  cyclic references add no new members. A `#PARSE!` formula contributes
  no references (its closure is just itself), and an invalid range —
  bad endpoints or mis-ordered, `#REF!` regardless of any cell's
  contents — contributes no members. For the bounds below the
  closure is always computed from the *currently stored* contents at the
  moment of the final `get` — i.e. after the edit, so `set(X, …)` itself
  is a relevant edit (X is in its own closure). Required bounds,
  measured as `eval_count` deltas; they are normative for exactly the
  operation patterns stated (other interleavings are constrained only by
  R11's values and the counting rule above). The two edit bounds apply
  when X holds a formula at the moment of the final `get`; if the edit
  left X a literal or empty cell, that `get` adds `0` (such reads never
  count):
  - Repeat read: two consecutive `get(X)` with no `set` in between — the
    second `get` adds `0`.
  - Irrelevant edit: after a `get(X)`, a `set(Y)` with `Y` outside the
    reference closure of `X`, then `get(X)` — the final `get` adds `0`.
  - Relevant edit: after a `get(X)`, a `set(Y)` with `Y` inside the
    reference closure of `X`, then `get(X)` — the final `get` returns
    the value R11 requires and adds at least `1`. A `set` that writes
    content identical to what the cell already held still counts as an
    edit for these bounds (no content-comparison short-circuit).
  - No full-sheet recompute: that same final `get(X)` adds at most the
    number of formula cells in the reference closure of `X` (X
    included).
- R11: Values never depend on evaluation strategy: after any sequence of
  `set`/`get` calls, every `get` returns exactly what a naive full
  recomputation from the currently stored literals and formulas would
  return.
- R12: Size, depth, and magnitude bounds — an evaluation is *within
  bounds* when (a) every formula it reaches has source text of at most
  512 characters and parenthesis nesting depth (count of `(` open at
  once; unary minus and flat operator chains do not add nesting) of at
  most 32, (b) it reaches at most 256 formula cells, and (c) every
  arithmetic intermediate and result it produces has absolute value at
  most 2**63 - 1. Within-bounds evaluations must complete without
  raising. Behavior of an out-of-bounds evaluation is unspecified (an
  exception is acceptable there), and the damage is confined: `set`
  always succeeds per R2 (it never evaluates), and a `get` whose
  evaluation stays within bounds keeps every guarantee in this spec even
  when out-of-bounds formulas or values exist elsewhere in the sheet.
  All other requirements apply only to within-bounds evaluations.

## Approval
Approved by human on 2026-07-12. Open non-blocking issues at approval:
- Comparison operators have no consumer (no IF/boolean context) — kept
  deliberately as experiment difficulty, not product value.
- "Oracle authorable from this spec alone" is a meta-criterion evaluated
  by Experiment W outside the run, not self-checkable in the loop.
- No descope path if the build overruns the overnight budget (MVP scope
  is fixed by design; a non-completing arm is a valid experiment result).
- Formulas over 512 chars get no cheap rejection at `set`; the
  resource-exhaustion surface is confined by R12 but not eliminated.
- R10's delta bounds are normative only for the exact stated patterns;
  other interleavings are constrained only by R11 values.
- Panel round 3 ran without the company and user reviewers (spend-limit
  failure); both reported zero blocking findings on round 2, and the two
  post-round-3 blocking fixes (R12 magnitude bound, R10 literal-edit
  carve-out) were applied without a confirming fourth round (3-round
  cap).
