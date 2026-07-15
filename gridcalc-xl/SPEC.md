# Spec: gridcalc-xl
version: 1
status: approved

## Overview
`gridcalc-xl` is a disposable pure-logic Python library providing one
public class, `Workbook`: an in-memory multi-sheet spreadsheet engine with
integer-and-string formula semantics, absolute references and copy,
per-sheet named ranges, full undo/redo, string-based persistence, and
incremental recomputation with volatile (clock-driven) functions,
observable through per-sheet evaluation counters. It is a throwaway
fixture — no file I/O, no UI. Its difficulty is the dependency-aware
recomputation engine under a growing feature set; the behavior is fully
specified below.

## Goals
- One public entry point, `Workbook`, whose sheets expose `set(addr, raw)`,
  `get(addr)`, and a cumulative per-sheet `eval_count` property.
- Exact semantics: every operation's result is fully determined by this
  spec — no floats, no locale/rounding questions, closed type rules. A
  formula's result is always an `int`, a `str` value, or an error string,
  never `None`.
- Incremental recomputation that is *behaviorally observable* through
  `eval_count` — including across sheets, after undo/redo, after
  round-trip, and under clock-driven volatility — while producing values
  identical to a naive full recomputation.
- Exact persistence: a string round-trip preserves stored contents,
  bindings, and evaluation semantics.

## Non-Goals
- No deletion APIs of any kind: cells cannot be cleared, sheets cannot be
  removed or renamed, names cannot be undefined (only redefined) — undo is
  the only way state ever goes backward.
- No floats; no escape sequences inside string literals (a `"` cannot
  occur inside a string literal); no locale-dependent behavior; no
  case-insensitive parsing anywhere.
- Grid per sheet is exactly `A1`–`Z99` (single uppercase letter column,
  row 1–99): no multi-letter columns, no rows above 99.
- No file I/O anywhere (persistence is string-in/string-out), no network,
  no concurrency, no UI, no performance requirements beyond the
  `eval_count` bounds (R10, R27) and the bounds in R12/R28.
- The undo/redo journal is not persisted (R24) and has no size bound.
- `to_json` output is not byte-stable and is implementation-private:
  equivalent workbooks may serialize differently, and one
  implementation's output need not load in another's `from_json` —
  golden serialized fixtures are out of scope; only same-implementation
  round-trips (R24–R25) are specified.
- Resource-exhaustion hardening is out of scope: unbounded journal
  growth, huge stored texts, and memory-exhausting `from_json` inputs
  are not defended against (R12/R28 confine only evaluation); the R24
  adversarial corpus deliberately excludes exhaustion-shaped inputs.
- Exception *message* text is unspecified everywhere: tests and the
  oracle assert on exception type only. Signature misuse (wrong arity,
  unexpected keywords) is outside the `ValueError` rule and raises
  whatever Python naturally raises (`TypeError`); no test asserts on it.
- No standalone single-sheet class is exported: sheets exist only inside a
  `Workbook` (`from gridcalc import Sheet` is not part of the API).
- `get`'s return value alone does not distinguish a genuine error value
  from a string value whose text happens to equal an error string (e.g.
  the literal `"#DIV!"`, or `CONCAT` output shaped like one); semantics
  are defined by provenance per this spec, and no API is provided to tell
  the two apart from the returned text.
- No cross-sheet-spanning ranges: a range's qualifier (if any) applies to
  both endpoints (R22).

## Company Lens
Throwaway experiment fixture for Experiment W′ (3-arm structure
dose-response at overflow scale, see the experiments monorepo
`gridcalc-xl/grading/EXPERIMENT.md`). Success is not adoption but
*gradability*: a held-out oracle must be authorable from this spec alone,
and the oracle for the v1 subset must port mechanically (delta list in the
Engineer Lens). Deliberate difficulty — the typed evaluator, the copy
rewrite rules, the undo/counter interaction, the multi-sheet dependency
model, and the volatility contract — is a design goal of the experiment,
not gold-plating. Sizing target is ~4x the v1 fixture (10 acceptance
groups, ~28 tasks, ~3000 LOC of runtime code — tests and the differential
reference are on top of, not inside, that figure). Cost bound: one
unattended overnight run per experiment arm. MVP scope is exactly R1–R28 —
nothing more.

## User Lens
The only consumers are test authors (each run's own pytest suite and the
held-out oracle). They need: a minimal API surface (exactly the methods in
R21), deterministic *values* for arbitrary interleavings of every API call
(counters are normative only for R10/R27's stated patterns, bounded
elsewhere), formula errors as plain return values (never exceptions during
evaluation, within R12/R28 bounds), and a persistence round-trip they can
insert into any test sequence without changing subsequent `get` values
(R25 — counters and the journal legitimately reset, R24). Convenience
beyond that is scope creep. Zero-to-value in four lines:
`wb = Workbook()`; `s = wb.add_sheet("S1")`; `s.set("A1", "=1+1")`;
`s.get("A1")` returns `2`.

## Engineer Lens
- Stack: Python 3.10+; runtime code uses the stdlib only (zero external
  dependencies; the `json` stdlib module is allowed for R24); tests use
  `pytest -q` and nothing else (no hypothesis or other test-time
  dependencies). Package name `gridcalc`; `from gridcalc import Workbook`
  works from the repo root.
- Security: no I/O, no `eval`/`exec` of Python, no network — the formula
  parser must be hand-written (no `eval()` on user input, even sandboxed).
  `from_json` must not execute or import anything based on its input
  (probed by adversarial `from_json` inputs plus a static source check:
  runtime code contains no `eval(`, `exec(`, `compile(`, `__import__`,
  `importlib`, or `pickle` — a smoke check, not a security guarantee).
  Adversarial corpus floor: at least 30 cases spanning non-`str` inputs,
  invalid JSON, valid-JSON wrong shapes (`null`, `[]`, numbers, bare
  strings), floats (`NaN`, `Infinity`, `1.0`), invalid sheet
  names/addresses, and deep nesting — exhaustion-shaped inputs excluded
  (Non-Goals).
- Error handling: *programmer* errors (invalid address argument,
  unsupported raw type, unknown sheet, invalid name or target, copy from
  an empty cell, qualified address where an unqualified one is required
  and vice versa) raise `ValueError` at the API boundary and leave all
  observable state unchanged; *formula* errors are in-band error string
  values (R5, extended by R18) and never raise within R12/R28 bounds.
- Testing: every requirement below is phrased to be machine-checkable.
  Incrementality (R10, R27) is checked through `eval_count` deltas only —
  no timing assertions. R11 is verified differentially: randomized API
  sequences cross-checked against an independent naive full-recompute
  reference, with fixed (or logged) random seeds so any failure is
  reproducible; floor: at least 1000 seeded sequences of length ≥ 50 over
  a dense fixed pool of 12 addresses (`A1`, `A2`, `B1`, `B2` on each of
  3 sheets), with `undo`/`redo`, `copy`, `define_name`,
  `advance_clock`, and `to_json`/`from_json` round-trips interleaved
  among `set`/`get`, zero mismatches. The generator keeps sequences
  well-formed: calls that would raise `ValueError` are legal sequence
  elements (assert the raise, state unchanged), pool sheets removed by
  a random `undo` are re-added before further use, and `copy` sources
  are constrained so rewrites stay within R12(a)'s 512-char limit
  (steering clear of R28's unspecified-accounting zone). A shared
  misreading of this spec
  by implementation and reference passes this harness silently; the
  held-out oracle is the backstop by design. Directed boundary tests
  complement the differential floor: the R12/R28 limits (256-cell
  chain, 512-char/32-deep sources, 2**63 magnitudes, 4096-char
  strings), `copy`'s out-of-grid `#REF!` rewrites, and R5/R13 ordering
  cases get explicit cases, not just random coverage.
- R12's guarantees are intended difficulty: they rule out naive recursion
  under CPython's default limit in both the evaluator (the 256-cell
  chain) and the parser (a ~500-deep unary-minus tower fits in 512
  chars). An iterative engine is preferred (a non-normative
  preference — the operative gate is that the chain and tower cases
  pass); raising the recursion limit — an interpreter-global mutation
  visible to the embedding process, sanctioned here as the sole
  exception to R24's global-state hygiene —
  is acceptable only if it is set once at import, cites R12 in a comment,
  and the R12 chain and tower cases pass. `RecursionError` within
  R12/R28 bounds is a bug.
- Over-engineering boundary: the public API is exactly the surface listed
  in R21 — additional public methods/classes are scope creep. No plugin
  systems, no AST visitors beyond what the grammar needs, no caching
  layers beyond what R10/R27 require, no serialization formats beyond
  R24.
- Deltas from the gridcalc v1 spec (for porting the v1 oracle — the v1
  subset is otherwise byte-compatible: all-integer arithmetic and
  comparisons, ranges, cycles, `COUNT`, error ordering, `eval_count`
  patterns, R12 bounds):
  1. References are read *typed*, not numerically (R13): `=A1` with `A1`
     holding a string returns that string (v1: `#TYPE!`), and
     string-vs-string `=`/`<>` comparisons are legal. Strings in
     arithmetic/orderings remain `#TYPE!`.
  2. Multi-letter uppercase identifiers (`AA1`, `FOO`) are name tokens:
     undefined ones evaluate to `#NAME!` (v1: `#PARSE!`). Lowercase/mixed
     identifiers outside sheet qualifiers are still `#PARSE!`.
  3. Texts the v1 grammar rejected are now legal: `$` reference marks,
     `"…"` string literals, `CONCAT`/`LEN`/`IF`/`NOW` calls, sheet
     qualifiers `Name!A1`, and the `#REF!` token.
  4. The API root is `Workbook`; there is no standalone `Sheet` export.
     v1 single-sheet cases run against one sheet of a fresh workbook.

## Designer Lens
Not applicable: no UI surface.

## Requirements

R1–R12 are the single-sheet core carried over from gridcalc v1, phrased
against a *sheet handle* (R21); bracketed `[XL: …]` notes mark where later
requirements extend or override them. R13–R28 are the XL extensions. Where
an XL requirement restates a v1 rule, the XL text governs.

Addressing and storage:
- R1: A valid address is exactly one uppercase letter `A`–`Z` followed by
  the ASCII digits (`0`–`9` only; no other Unicode digits anywhere in
  this spec) of an integer `1`–`99` with no leading zeros (`A1`, `Z99`).
  A sheet handle's `set`/`get` raise `ValueError` when the address
  argument is not a `str` (e.g. `get(5)`, `get(None)`) or is a `str` that
  is not a valid address (lowercase, `A0`, `A01`, `A100`, `AA1`, empty,
  internal or leading/trailing whitespace, and any qualified form like
  `S1!A1` — handle address arguments are always unqualified, R21). A
  `get` that raises `ValueError` leaves all observable state — contents,
  caches, counters — unchanged.
- R2: `set(addr, raw)` accepts `raw` of type `int` (stored as a number)
  or `str` (starting with `=` → stored as a formula; otherwise a string
  literal). `bool` raw raises `ValueError` despite being an `int`
  subclass; instances of other `int` subclasses and of `str` subclasses
  are accepted wherever an `int`/`str` is (as `addr` or `raw`) and are
  normalized on storage — `get` returns plain `int`/`str` values. Any
  other type raises `ValueError`. `set` returns `None` on success.
  A `set` that raises `ValueError` leaves the workbook — contents,
  counters, journal, and all observable state — unchanged. `set` on an
  occupied cell replaces its content. `get(addr)` on a never-set cell
  returns `None`; on a literal cell it returns the stored `int` or `str`
  unchanged; on a formula cell it returns the formula's evaluated result
  — an `int`, a `str` value, or an error string, per R3–R9 and R13–R18.

Formula grammar (the text after the leading `=`):
- R3: The v1 grammar, complete and closed — any formula text the *full XL
  grammar* (this rule plus the extensions listed at the end) does not
  derive evaluates to `#PARSE!` (including the empty formula `=`):
  - `expr    := additive ( CMP additive )*` where `CMP` is one of
    `= <> < <= > >=`; comparisons are left-associative and yield the
    integers `1`/`0` — there is no boolean type (`=1<2<3` is `(1<2)<3`,
    i.e. `1`). Typing of comparisons is R13's job.
  - `additive := term ( (+|-) term )*`, left-associative.
  - `term    := factor ( (*|/) factor )*`, left-associative.
  - `factor  := - factor | primary` — unary minus stacks (`=--1` is `1`,
    `=2--3` is `5`).
  - `primary := INT | REF | FUNC-CALL | ( expr )` — a function call is an
    ordinary primary and composes as a sub-expression (`=SUM(A1:B2)+1`,
    `=-MAX(A1:A2)*2` are legal).
  - `INT`: one or more ASCII digits; leading zeros are allowed and
    carry no meaning (`=007` is `7`).
  - `REF`: one uppercase letter `A`–`Z` followed by one or more ASCII
    digits. (Validity of what it denotes is R6's job, not the parser's.)
    [XL: optionally `$`-marked, R16; optionally sheet-qualified, R22.]
  - `FUNC-CALL`: the fixed function set with per-function argument
    shapes; any call form not listed is `#PARSE!`:
    `SUM ( RANGE-ARG )`, `MIN ( RANGE-ARG )`, `MAX ( RANGE-ARG )`,
    `COUNT ( RANGE-ARG )` [v1], plus `CONCAT ( expr ( , expr )* )`,
    `LEN ( expr )` [R14], `IF ( expr , expr , expr )` [R15], and
    `NOW ( )` [R26]. `RANGE-ARG := RANGE | NAME | #REF!` [R17, R18].
    A function name not followed by `(` fails the grammar (`=SUM` is
    `#PARSE!`), as does a listed function with the wrong argument shape
    (`=SUM(A1)`, `=SUM()`, `=CONCAT()`, `=NOW(1)` are `#PARSE!`).
    Unknown callees — lowercase or mixed case (`sum(…)`), or any
    identifier outside the set above followed by `(` (`AVG(A1:B2)`,
    `AA1(…)`) — fail the grammar: `#PARSE!`.
  - `RANGE := REF : REF` — a range may appear only as a `RANGE-ARG`; a
    range anywhere else (`=A1:B2`, `=SUM((A1:B2))`) fails the grammar:
    `#PARSE!`. [XL: optionally qualified as a whole, R22.]
  - Whitespace: spaces and tabs are allowed before/after any token,
    including between a function name and its `(`, around argument
    commas, around the `:` of a range, and around the `!` of a sheet
    qualifier. The two-character operators `<= >= <>` must not contain
    whitespace (`=1 < = 2` is `#PARSE!`).
  - [XL extensions folded into the grammar above and below: `STRING`
    literals as primaries (R13), `$` marks on REFs (R16), the `#REF!`
    token as a primary or `RANGE-ARG` (R17), `NAME` tokens as primaries
    or `RANGE-ARG`s (R18), sheet qualifiers (R22). Identifier
    classification: a token of uppercase letters/digits/underscores that
    matches the REF shape (one letter then digits) is a REF; otherwise,
    if it matches the NAME shape (R18) it is a NAME — so `AA1` and `FOO`
    are NAMEs, `#NAME!` when undefined, *not* `#PARSE!`; an identifier
    matching neither shape — a single letter (`=F`), or 33+ characters —
    falls to the closed-grammar catch-all: `#PARSE!`.]
- R4: Division is integer division truncating toward zero: `=-7/2` is
  `-3`, `=7/-2` is `-3`, `=7/2` is `3`. Division by zero evaluates to
  `#DIV!`. Arithmetic operands must be `int` per R13.
- R5: Error values are exactly the strings `#PARSE!`, `#REF!`, `#TYPE!`,
  `#DIV!`, `#CYCLE!`, `#NAME!` [XL: `#NAME!` added by R18], returned by
  `get` as ordinary `str` values (never exceptions, within R12/R28
  bounds). Operands are evaluated depth-first in the textual
  left-to-right order they appear in the formula source; the first error
  encountered in that order is the formula's result (in `=A1+B1*C1` the
  order is `A1`, `B1`, `C1`), and evaluation short-circuits there:
  operands textually after the first error are not evaluated (observable
  through R10's counters — in `=1/0+Y1` with `Y1` a formula cell, `Y1`'s
  computation never starts). [XL: `IF` alone deviates by design — its
  untaken branch is skipped even when it would error, R15.]
- R6: Every reference in a formula contributes the referenced cell's
  *typed value* per R13: a number cell its `int`; a string-literal cell
  its `str`; a formula cell that formula's result (`int`, `str`, or
  error); an empty (never-set) cell the `int` `0` — in every
  *single-reference* context (bare `REF`, operator operand, expression
  argument of a function); as a member of a `RANGE`, an empty cell
  instead contributes nothing (R8).
  A `REF` token whose digits have a leading zero or denote a row outside
  `1`–`99` (`A01`, `A0`, `A100`) parses fine but denotes no grid cell:
  it evaluates to `#REF!`. [XL: this replaces v1's uniform *numeric*
  read — see the delta list in the Engineer Lens.]

Ranges, functions, cycles:
- R7: A range `TL:BR` is valid when both endpoints denote grid cells
  (else `#REF!`, same rule as R6) and TL's column ≤ BR's column and TL's
  row ≤ BR's row (else `#REF!`). Range cells are visited row-major
  (`A1, B1, A2, …` for `A1:B3`). For `SUM`/`MIN`/`MAX`, members
  contribute their typed value (R6); a `str` contribution — from a
  string-literal cell or a string-valued formula — is `#TYPE!` fuel. The
  first error value in visit order is the function's result, and
  evaluation short-circuits there — members after it are not evaluated
  (observable through R10's counters, same rule as R5).
- R8: Over the *non-empty* cells of a valid range (empty cells contribute
  nothing to any function): `SUM` adds the `int` contributions and is
  `0` on an all-empty range; `MIN`/`MAX` take the least/greatest `int`
  contribution and are `#TYPE!` on an all-empty range. `COUNT` is purely
  structural: it returns the number of non-empty cells (number, string,
  and formula cells all count) *without evaluating anything* — it never
  yields an error (beyond R7's `#REF!` for an invalid range itself),
  never increments any `eval_count` for range members, and its range
  members do not participate in cycle detection (`A1` holding
  `=COUNT(A1:A1)` is `1`, not `#CYCLE!`).
- R9: Circular references: if evaluating a cell requires the value of a
  cell whose evaluation is already in progress — directly, mutually,
  through a `SUM`/`MIN`/`MAX` range, or across sheets [R23] — that read
  contributes `#CYCLE!`. Consequently every cell on the cycle evaluates
  to `#CYCLE!` for that `get`, and cells off the cycle that depend on
  one receive `#CYCLE!` by R5/R6/R7 propagation.

Incremental recomputation:
- R10: Each sheet's `eval_count` is a cumulative `int` property, starting
  at `0`. No mutating operation (`set`, `copy`, `define_name`,
  `add_sheet`, `advance_clock`, `undo`, `redo`) ever evaluates formulas
  or changes any `eval_count`; evaluation happens only inside `get`
  (lazy). During a `get`, the counter of the sheet *owning the cell*
  increases by exactly 1 for each formula cell whose value computation is
  *started* (error results — `#PARSE!`, `#CYCLE!` included — count the
  same as values; hitting an already-in-progress cell does not start a
  second computation of it). Reads of literal or empty cells never
  increment anything. Results — values and errors alike — are cached.
  The *reference closure* of a formula cell X is the least set of
  (sheet, address) pairs containing X itself and, for every formula cell
  in the set, every cell its formula references directly — each single
  `REF` (qualified or not, resolved per R22's binding rules), every cell
  covered by any `RANGE-ARG` (`SUM`/`MIN`/`MAX`/`COUNT` alike, empty
  cells included, `NAME` arguments via their current binding per R18),
  and the references of *both* `IF` branches regardless of the condition
  (R15 — the closure is static). It is a transitive closure (least fixed
  point): cyclic references add no new members. A `#PARSE!` formula
  contributes no references (its closure is just itself); an invalid
  range — bad endpoints or mis-ordered — contributes no members; an
  undefined `NAME` contributes no members; a qualifier naming no
  existing sheet contributes no members. For the bounds below the
  closure is always computed from the *currently stored* contents and
  bindings at the moment of the final `get` — so the edit itself is
  relevant (X is in its own closure). Bound patterns below are measured
  as the *sum of all sheets' `eval_count` deltas*; they are normative
  for exactly the operation patterns stated (other interleavings are
  constrained only by R11's values and the counting rule above). An
  *edit* below means any journaled operation or `undo`/`redo` (R19,
  R20); which cells an edit touches is defined per operation (R17, R18,
  R20, R22, R27). The two edit bounds apply when X holds a formula at the
  moment of the final `get`; if the edit left X a literal or empty cell,
  that `get` adds `0` (such reads never count):
  - Repeat read: two consecutive `get(X)` with no edit in between — the
    second `get` adds `0`. [XL: for volatile X the clock must also be
    unchanged, R27 — subsumed by "no edit" since `advance_clock` is an
    edit.]
  - Irrelevant edit: after a `get(X)`, an edit whose touch set contains
    no (sheet, address) pair inside the reference closure of `X` — then
    `get(X)` adds `0`.
  - Relevant edit: after a `get(X)`, an edit whose touch set intersects
    the reference closure of `X` — the final `get` returns the value
    R11 requires and adds at least `1`. Touch sets, per operation: a
    `set` or `copy` touches its target cell; a `define_name` touches
    per R18 (mention-holding formula cells on the defining sheet); an
    `add_sheet` touches per R22 (qualifier-mentioning formula cells); a
    clock edit touches per R27 (volatile cells); `undo`/`redo` touch as
    the operation they revert/reapply (R20). An edit that writes
    content identical to what the cell already held still counts (no
    content-comparison short-circuit; undo/redo included, R20).
  - No full-sheet recompute: that same final `get(X)` adds at most the
    number of formula cells in the reference closure of `X` (X
    included), summed across sheets.
- R11: Values never depend on evaluation strategy: after any sequence of
  successful API calls — including `copy`, `define_name`, `undo`/`redo`,
  `add_sheet`, `advance_clock`, and `from_json` — every `get` returns
  exactly what a naive full recomputation from the currently stored
  literals, formulas, name bindings, sheet set, and clock value would
  return. (Testing floor: the seeded differential harness in the
  Engineer Lens.)
- R12: Size, depth, and magnitude bounds — an evaluation is *within
  bounds* when (a) every formula it reaches has source text of at most
  512 characters and parenthesis nesting depth (count of `(` open at
  once; unary minus and flat operator chains do not add nesting) of at
  most 32, (b) it reaches at most 256 formula cells, counted across all
  sheets [R28] — a cell is *reached* when the evaluation starts its
  computation or reads its result, so a cached result read counts as
  reached without a new start —, (c) every arithmetic intermediate and
  result it produces
  has absolute value at most 2**63 − 1, and (d) every string
  intermediate and result it produces has length at most 4096 characters
  [R28]. Within-bounds evaluations must complete without raising.
  Behavior of an out-of-bounds evaluation is unspecified (an exception
  is acceptable there, but the evaluation must terminate — return or
  raise; non-termination is a defect even out of bounds), and the
  damage is confined: mutating operations
  always succeed per their own rules (they never evaluate), and a `get`
  whose evaluation stays within bounds keeps every guarantee in this
  spec even when out-of-bounds formulas or values exist elsewhere in the
  workbook. After an out-of-bounds evaluation raises, the workbook
  remains usable and within-bounds `get`s keep every value guarantee
  (R11); counters may have increased arbitrarily during the aborted
  evaluation, so R10/R27's bound patterns are normative only for
  pattern windows containing no out-of-bounds evaluation. All other
  requirements apply only to within-bounds evaluations. (Directed
  boundary cases: Engineer Lens.)

Strings in formulas (Phase 5):
- R13: The grammar gains `STRING` as a primary: `"` followed by zero or
  more characters that are not `"`, then `"` — no escape sequences (a
  `"` can never occur inside a string literal); *any* other character
  is legal inside a literal and preserved verbatim, including newlines
  and control characters, which stay illegal as whitespace elsewhere in
  a formula (R3 allows only spaces and tabs) and must survive storage
  and R24's round-trip byte-for-byte. A `STRING` evaluates to its
  contents as a
  `str` value; formula results may now be strings. Typing rules, closed:
  `+ - * /`, unary minus, and the orderings `< <= > >=` require `int`
  operands — a `str` operand (literal, reference contribution, or
  function result) makes that operand position contribute `#TYPE!`,
  discovered in R5's left-to-right order. `=` and `<>` compare two
  `int`s or two `str`s (`str` comparison is exact, code-point-wise,
  case-sensitive), yielding `1`/`0`; a mixed `int`-vs-`str` comparison
  is `#TYPE!`. Typing violations are discovered positionally, exactly
  like errors: operands are examined in R5's textual left-to-right
  order, and the first operand position that offends — whether by
  carrying an error value or by having a type its operator forbids —
  determines the result (`="x"+A1` is `#TYPE!` regardless of `A1`, the
  string being the first offender in textual order; `=A1+"x"` with `A1`
  evaluating to `#DIV!` is `#DIV!`). Operands textually after the first
  offender are not evaluated, exactly as for errors (observable through
  R10's counters).
- R14: `CONCAT ( expr ( , expr )* )` takes one or more comma-separated
  expression arguments; `LEN ( expr )` takes exactly one. Arguments are
  evaluated left-to-right with R5 short-circuit on the first error. The
  *decimal rendering* of an `int` is its base-10 text with a leading `-`
  for negatives and no leading zeros (the value, not its source text:
  `=CONCAT(007)` is `"7"`). `CONCAT` renders `int` arguments and takes
  `str` arguments as-is, returning the left-to-right concatenation as a
  `str` (an empty-cell reference argument contributes `int` `0`, hence
  renders `"0"` — R6's empty-cell rule is uniform across
  single-reference contexts; range members differ, R8).
  `LEN` returns the number of characters of a `str` argument, or of the
  decimal rendering of an `int` argument (`=LEN(-12)` is `3`,
  `=LEN("")` is `0`).
- R15: `IF ( expr , expr , expr )`: the first argument (condition) is
  evaluated first; an error condition is the result; a `str` condition
  is `#TYPE!`; an `int` condition selects the second argument when
  nonzero, the third when zero. Only the selected branch is evaluated —
  the unselected branch's cells are never evaluated, even when the
  selected branch or the condition errors (observable through R10's
  counters), and an error inside the unselected branch's text is
  invisible to the result. The result is the selected branch's value, of
  any type. For R10, the closure is static: references in *both*
  branches (and the condition) are closure members.

Absolute references, copy, named ranges (Phase 6):
- R16: The `REF` token gains optional `$` marks: `$` may appear
  immediately before the column letter and/or immediately before the row
  digits (`$A1`, `A$1`, `$A$1`; whitespace inside a token is illegal as
  ever). A `$`-marked reference denotes exactly the cell its unmarked
  form denotes — evaluation, validity (R6), closures, and cycles are
  unaffected. `$` marks matter only to `copy` (R17). Range endpoints may
  carry `$` marks likewise.
- R17: `sh.copy(src, dst)` (a sheet-handle method) copies the content of
  cell `src` to cell `dst`; both arguments are unqualified addresses on
  `sh` [XL: either may be sheet-qualified, R23]. `ValueError` — with no
  state change and no journal entry — when either argument fails R1, or
  `src` is an empty (never-set) cell. `copy` returns `None`, never
  evaluates anything, and is journaled (R19). A literal `src` stores the
  identical value at `dst`. A formula `src` whose text the full grammar
  does not derive (a `#PARSE!` formula) is copied byte-for-byte
  unchanged. A parseable formula `src` stores at `dst` the source
  text transformed as follows, all other characters preserved exactly
  (operators, whitespace, `STRING` contents, `NAME` tokens, `INT`s,
  function names are never touched): let Δcol/Δrow be `dst` minus `src`
  per component; in every `REF` token *whose letter and digits denote a
  grid cell by R6's digit-shape rule* (any sheet qualifier is irrelevant
  to this test — `Ghost!A1` shifts like `A1` whether or not `Ghost`
  exists), an
  un-`$`-marked column/row component is shifted by Δ and re-rendered in
  place (its `$` marks and any sheet qualifier preserved), a `$`-marked
  component is kept; a `REF` token that already denotes no grid cell
  (leading-zero or out-of-range digits, `A0`, `A007`, `A100`) is kept
  verbatim — it evaluates to `#REF!` either way (R6). If a
  shifted component leaves the grid (column outside `A`–`Z` or row
  outside `1`–`99`): for a bare or qualified `REF`, the entire token
  (qualifier and `$`s included) is replaced by `#REF!`; for a `RANGE`
  where either endpoint leaves the grid, the entire range expression
  (qualifier included) is replaced by `#REF!`. A replacement spans the
  full replaced construct — qualifier, `$` marks, `:`, and any
  whitespace interior to the construct — while all characters outside
  it are preserved. The token `#REF!` is
  grammar-legal as a primary and as a `RANGE-ARG`, always evaluating to
  the error `#REF!`. `copy` with `src == dst` is legal (zero shift, text
  unchanged). The rewritten text may exceed R12(a)'s limits (`#REF!`
  replacements and digit growth lengthen text); R12's out-of-bounds
  rules then apply to `get(dst)`. For R10's bounds, a `copy` is an edit
  at `dst`.
- R18: `sh.define_name(name, target)` binds a *per-sheet* name:
  resolution of a `NAME` token in a formula uses the names of the sheet
  *hosting* that formula (so a cross-sheet `copy` re-resolves names in
  `dst`'s sheet, R23). `NAME` syntax: 2–32 characters from `A`–`Z`,
  `0`–`9`, `_`, starting with a letter or `_`, that does not match the
  `REF` shape (one letter then only digits) and is not a function name
  (`SUM`, `MIN`, `MAX`, `COUNT`, `CONCAT`, `LEN`, `IF`, `NOW`).
  `target` is an unqualified address (`"B2"`) or range (`"A1:B2"`) on
  `sh` [XL: may be qualified, R23] whose endpoints satisfy R1 and whose
  range is well-ordered per R7. Violations of any of these — including
  non-`str` arguments — raise `ValueError` with no state change and no
  journal entry. Redefining an existing name replaces its binding;
  `define_name` returns `None`, never evaluates anything, and is
  journaled (R19). In formulas, a `NAME` is legal as a `RANGE-ARG`
  (denoting its target; a single-address target acts as a 1×1 range) and
  as a primary (denoting the target cell's typed value when the target
  is a single address or 1×1 range; a larger target used as a primary is
  `#REF!`). An undefined `NAME` (in either position) evaluates to
  `#NAME!`. `define_name` validates its target fully at call time
  (including, for a qualified target, that the sheet exists — R23);
  combined with the journal's strict LIFO order this makes dangling
  bindings unreachable: an `undo` can only remove a sheet after every
  later journal entry — including any `define_name` targeting it — has
  been undone first, so a live binding's target sheet always exists.
  For R10, a formula mentioning `NAME` N references the cells of N's
  current binding (nothing when undefined), and a `define_name` on N is
  an edit touching every formula cell on `sh` whose parsed formula
  mentions N — even when the new binding equals the current one (no
  binding-comparison short-circuit, matching R10's rule for `set`).

Undo/redo (Phase 7):
- R19: The workbook keeps one totally-ordered journal of every
  *successful* mutating operation: `set`, `copy` (R17), `define_name`
  (R18), `add_sheet` (R21), `advance_clock` (R26). `get`, `sheet`,
  `sheet_names`, `clock`, and `to_json` (R24) never journal; failed
  (`ValueError`) calls never journal.
  `wb.undo()` reverts the most recent not-yet-undone journal entry and
  returns `True`; with nothing to undo it returns `False` and changes
  nothing. `wb.redo()` re-applies the most recently undone entry and
  returns `True`, or returns `False` when nothing is undone. Any new
  journaled operation clears the redo stack; `undo`/`redo` themselves
  never append entries. Reverting a `set` or `copy` restores the target
  cell's previous content — including the never-set state; reverting a
  `define_name` restores the name's previous binding — including
  undefined; reverting an `add_sheet` removes that sheet (by journal
  order it is empty again at that point) and reverting `advance_clock`
  restores the previous clock value; `redo` re-applies each exactly.
  Sheet handles are bound to their sheet *name*: any member access
  through a handle whose sheet does not currently exist — the
  `eval_count` property included — raises `ValueError`, and the same
  handle works again once `redo` (or a fresh `add_sheet` of that name)
  restores the sheet.
- R20: Undo/redo versus counters and caches: every `eval_count` is
  monotonic — `undo`/`redo` never decrease any counter (history of
  computation is not history of content). After any `undo`/`redo`
  sequence, values obey R11 against the *restored* contents, bindings,
  sheet set, and clock. For R10's bound patterns, an `undo`/`redo` is
  the edit(s) it performs: restoring a cell's content is an edit at that
  cell *even when the restored content equals what a still-earlier state
  held* (no content-comparison short-circuit); restoring a binding is a
  `define_name`-equivalent edit (R18); restoring the clock is an
  `advance_clock`-equivalent edit (R27); an `undo`/`redo` whose
  operation touches nothing in `get(X)`'s closure leaves `get(X)` at
  `+0` (irrelevant-edit bound).

Workbook and multi-sheet (Phase 8):
- R21: The public API root is `Workbook` (`from gridcalc import
  Workbook`). `Workbook()` starts empty: no sheets, no names, clock `0`,
  empty journal. `wb.add_sheet(name)` creates an empty sheet and returns
  its handle; a sheet name is a `str` of 1–32 characters from `A`–`Z`,
  `a`–`z`, `0`–`9`, `_`, starting with a letter; a non-`str`, an invalid
  name, or a duplicate (names are case-sensitive) raises `ValueError`.
  `wb.sheet(name)` returns the handle of an existing sheet, else
  `ValueError`. `wb.sheet_names` is the list of current sheet names in
  creation order (reflecting undo/redo). `eval_count` state is kept per
  sheet *name* for the lifetime of the workbook: a sheet removed by
  `undo` and later restored by `redo` — or re-created by a fresh
  `add_sheet` under the same name — resumes its previous counter, so
  R20's monotonicity holds per name, workbook-wide. A sheet handle
  exposes exactly
  `set(addr, raw)`, `get(addr)`, `copy(src, dst)`,
  `define_name(name, target)`, and the read-only property `eval_count`,
  with R1–R20 semantics; handle address arguments (`addr` of
  `set`/`get`) are always unqualified — a qualified string raises
  `ValueError` per R1. The complete public surface is: `Workbook()`,
  `add_sheet`, `sheet`, `sheet_names`, `undo`, `redo`, `advance_clock`,
  `clock`, `to_json`, `from_json` (classmethod), and the five handle
  members above. Nothing else is public API — operationally:
  `gridcalc.__all__ == ["Workbook"]`, and the non-underscore attributes
  of `Workbook` and of a sheet handle are exactly the names listed
  here. `wb.sheet_names` returns a fresh list each call (mutating the
  returned list never changes workbook state); repeated
  `wb.sheet(name)` calls may return the same or a new handle object —
  handles carry no identity semantics beyond their name binding (R19).
  R2's subclass rule is API-wide: every `str` argument (sheet names,
  addresses, names, targets, `from_json` input) accepts `str`
  subclasses, normalized on storage — `sheet_names` and stored state
  return plain `str`.
- R22: Grammar: a `REF` or a whole `RANGE` may carry a sheet qualifier —
  `QREF := SHEET ! REF` and `QRANGE := SHEET ! REF : REF`, where `SHEET`
  is a sheet-name token (same syntax as R21, matched case-sensitively);
  whitespace is allowed around `!` as around any token. Tokenization
  precedence: an identifier immediately followed — whitespace permitted —
  by `!` is always a `SHEET` token, even when it also matches the `REF`,
  function-name, or `NAME` shapes (`=SUM!A1` and `=A1!B2` are qualified
  references, never `#PARSE!`); an identifier that cannot be a sheet
  name (e.g. one starting with `_`) followed by `!` fails the grammar —
  `#PARSE!` — while a well-shaped qualifier naming no existing sheet is
  `#REF!` at evaluation (the syntax/existence boundary). A qualifier
  binds the whole range — a second qualifier inside a range
  (`S1!A1:S2!B2`, `A1:S2!B2`) fails the grammar: `#PARSE!`. An
  *unqualified* `REF`/`RANGE` binds to the sheet hosting the formula; a
  qualified one binds to the named sheet. At evaluation, a qualifier
  naming no currently existing sheet makes that reference (or range)
  contribute `#REF!`; for R10 it contributes no closure members while
  the sheet is absent. For R10's bound patterns, an `add_sheet(S)` — and
  any `undo`/`redo` that removes or restores S — is an edit touching
  every formula cell whose parsed formula mentions qualifier S (name
  bindings never dangle, R18, so no separate rule is needed for them).
  Qualified references may carry `$` marks on the `REF` part (R16); the
  qualifier itself is never shifted by `copy` (R17).
- R23: All v1 semantics lift to (sheet, address) identity: R5 ordering,
  R7 row-major visits, R9 cycle detection (a cycle may thread through
  any number of sheets), R10 closures and bounds (summed across sheets;
  each computation increments the owning sheet's counter), R11 naive
  equivalence, and R12's 256-formula-cell reach. Hosting-sheet binding
  makes a formula's meaning depend on the sheet it lives on: after
  `copy` to another sheet, unqualified references and `NAME` tokens
  re-resolve against the destination sheet (`NAME`s by R18's per-sheet
  namespaces — a name undefined there is `#NAME!`). `copy` and
  `define_name` arguments extend: `copy(src, dst)` accepts each argument
  either unqualified (meaning the handle's own sheet) or qualified
  (`"S2!B2"`, meaning that sheet — `ValueError` when the sheet does not
  exist); `define_name`'s `target` likewise may be qualified, so a name
  on one sheet may denote cells of another. Qualified-argument shape is
  exactly `SHEET ! ADDR` (or `SHEET ! ADDR : ADDR` for a name target)
  with no whitespace; anything else fails the argument validation of
  R17/R18 (`ValueError`).

Persistence (Phase 9):
- R24: `wb.to_json()` returns a `str` that `json.loads` accepts. It is a
  pure observation: it evaluates nothing, changes no counter, and
  appends no journal entry. `Workbook.from_json(s)` is a classmethod
  returning a *new* workbook; it raises `ValueError` — and only
  `ValueError` — when `s` is not a `str`, when `json.loads` rejects it
  as invalid JSON, or when the parsed JSON does not match the
  implementation's schema or would violate any invariant of this spec
  (any JSON float — `NaN`, `Infinity`, and integer-valued `1.0` alike —
  invalid sheet names or addresses, wrong shapes); pathological inputs on which
  `json.loads` itself raises something other than `ValueError` (e.g.
  `RecursionError` on extreme nesting) may propagate that exception.
  `from_json` never executes or imports anything based on the input
  (probe: the Engineer Lens security check plus an adversarial-input
  corpus); any string produced by `to_json` loads successfully. On
  *any* input it either returns a workbook satisfying every invariant
  of this spec or raises — never a partially-constructed workbook — and
  no exception corrupts other workbooks or interpreter-global state.
  Restored exactly: the sheet set with names and creation order, every
  cell's stored content (numbers, string literals, and formula *text*
  byte-for-byte — `$` marks, qualifiers, whitespace, and `#REF!` tokens
  included), every sheet's name bindings, and the clock value. Reset:
  the journal is empty (`undo()` returns `False` immediately after
  loading), every sheet's `eval_count` is `0`, and no evaluation results
  are carried over — the first `get` of a formula cell on the loaded
  workbook computes it fresh (observable through R10's counters).
- R25: Round-trip equivalence: for any workbook `W` reachable by
  successful API calls, `W2 = Workbook.from_json(W.to_json())` has the
  same `sheet_names` and `clock`, and for every sheet and address,
  `W2`'s `get` returns exactly what `W`'s `get` returns (equivalently:
  what R11's naive recomputation of the shared stored state yields) —
  values, strings, and error values alike. Any subsequent sequence of
  successful API calls applied identically to `W` and `W2` (excluding
  `undo`/`redo`, whose journals legitimately differ) yields identical
  `get` results and identically-behaving further round-trips; in
  particular a `copy` after the round-trip rewrites exactly the text it
  would have rewritten before, and R10's bounds hold on `W2` as a fresh
  workbook over the restored state. Byte-equality of `to_json` outputs
  is not required — equivalence is semantic. (Verified by the same
  seeded differential harness as R11, with `to_json`/`from_json`
  round-trips interleaved into the sequences — Engineer Lens floor.)

Volatile recalculation (Phase 10):
- R26: `wb.clock` is a read-only `int` property starting at `0`;
  `wb.advance_clock()` increments it by exactly 1, returns the new
  value, and is journaled (R19; its undo restores the previous value).
  Grammar: `NOW ( )` — exactly the uppercase name `NOW` with empty
  parentheses — is a function call taking no arguments (any argument is
  `#PARSE!`; empty parentheses on every other function remain
  `#PARSE!`). `NOW()` evaluates to the current clock value as an `int`.
- R27: A formula cell is *volatile* when any formula cell in its
  reference closure (itself included) contains a `NOW()` function call
  in its parsed formula — the definition is static and syntactic: a
  `NOW` inside an unselected `IF` branch still makes the cell volatile,
  while `NOW` appearing only inside a `STRING` literal is text, not a
  call, and does not. A `#PARSE!` formula cell is never volatile and
  never contributes a `NOW` (it has no parsed formula; its closure is
  itself). Correctness is R11 with the clock as an input: every `get`
  matches naive recomputation at the *current* clock, always. For
  R10's bound patterns, a *clock edit* (`advance_clock`, or an
  `undo`/`redo` whose operation is an `advance_clock`) is an edit
  touching exactly the volatile formula cells — so after clock-only
  edits, `get(X)` adds `0` whenever X's closure has no volatile member
  (irrelevant-edit bound), and the repeat-read bound (no edit of any
  kind in between) gives `0` even for volatile X (results are stable
  within a clock value). Tighter volatile bound, normative for exactly
  this pattern: when every formula cell in X's reference closure has
  been evaluated at least once since it was last edited (e.g. by a
  preceding `get` of each closure member) and a `get(X)` has then been
  performed, one or more clock-only edits followed by `get(X)` add at
  most the number of volatile formula cells in X's closure — warm
  non-volatile members are not recomputed. (Without that warm-up
  precondition the pattern is not normative: a clock change may flip an
  `IF` branch or move an R5 error position onto never-computed cells,
  which then count per R10's counting rule.)
- R28: XL bound extensions, folded into R12's within-bounds definition:
  the 256-formula-cell reach of R12(b) is counted across all sheets of
  the workbook, and R12(d) bounds every string intermediate and result
  (string literal contents, `CONCAT` results, decimal renderings) at
  4096 characters. Out-of-bounds behavior and damage confinement are
  exactly R12's. R12(a)'s source-text limits also delimit mutating-op
  obligations: a stored formula text exceeding them is copied
  byte-for-byte unchanged (like a `#PARSE!` formula — `copy` still
  succeeds, journals, and undoes normally), and R10/R18/R22/R27 closure,
  mention, and volatility accounting over such texts is unspecified
  (`set` itself always succeeds and stores verbatim). No bounds are
  placed on journal length, sheet count, or name count — they are
  limited only by memory.

## Acceptance Groups
- G1: R1, R2 — cell store
- G2: R3, R4, R5, R6 — formula grammar and scalar evaluation
- G3: R7, R8, R9 — ranges, functions, cycles
- G4: R10, R11, R12 — incremental recomputation
- G5: R13, R14, R15 — string type and functions
- G6: R16, R17, R18 — absolute references, copy, named ranges
- G7: R19, R20 — undo/redo
- G8: R21, R22, R23 — workbook and multi-sheet
- G9: R24, R25 — persistence round-trip
- G10: R26, R27, R28 — volatile recalculation and XL bounds

## Approval
Approved by human on 2026-07-15. Panel: 5 lenses (designer skipped — no
UI) × 3 rounds; round 1 resolved 6 blocking findings (qualifier
tokenization precedence, add_sheet touch sets, per-name counter
lifecycle, unparseable-formula copy, dangling name targets), round 2
resolved 1 (the R27 volatile bound, repaired with the warm-up
precondition and re-verified satisfiable in round 3), round 3 returned
zero blocking findings. Twelve round-3 clarifications were applied
without a confirming fourth round (3-round cap; same convention as the
gridcalc v1 approval). Open non-blocking issues at approval:
- The R11/R25 naive full-recompute reference is effectively a second
  implementation of the semantics — the largest work item not counted
  in the ~3000 LOC sizing; the one-overnight cost bound absorbs it by
  assertion only.
- The Engineer Lens claim that the v1 subset is otherwise
  byte-compatible is a cross-document assertion this spec cannot
  establish alone; if the four-item delta list is incomplete, the
  mechanical oracle port mis-grades silently.
- R24/R25's universally quantified guarantees ("never executes or
  imports", "no corruption", "any workbook") are verified only up to
  the stated corpus/harness floors; the held-out oracle is the backstop.
- Out-of-bounds evaluations must terminate but carry no time or memory
  cap — arbitrarily slow evaluations remain possible in unattended runs.
- The volatile-clock subsystem (G10) is the least user-valuable
  requirement group; kept by pre-registered experiment design.
- Cost/sizing targets (~3000 LOC, one overnight run per arm) are
  lens-level statements enforced by no acceptance group — intentional.
