# Plan: gridcalc
version: 1
status: approved

## Phase 1: Cell store
Goal: a Python package `gridcalc` exposing `Sheet` with validated
addressing, literal storage with strict types, and the `eval_count`
property surface — no formula evaluation yet.
Phase acceptance: `pytest -q` green; `from gridcalc import Sheet` works
from the repo root; every R1/R2 criterion below has a test; `eval_count`
exists and stays `0` across literal-only workloads.

### Task 1.1: Address validation + Sheet skeleton
risk: light
covers: R1
files: gridcalc/__init__.py, gridcalc/sheet.py, tests/test_address.py
acceptance:
- get/set accept valid addresses across the grid (at least A1, Z99, M50)
- ValueError on address: lowercase ("a1"), "A0", "A01", "A100", "AA1",
  "", " A1", "A1 ", "A 1", and non-str arguments (get(5), get(None),
  set(None, 1))
- a str-subclass instance whose text is a valid address is accepted as
  addr (R2 normalization applies at the address position too)
- a get that raises ValueError leaves all observable state unchanged
  (eval_count value included)
- eval_count property exists and is 0 on a fresh Sheet

### Task 1.2: Literal values — types, normalization, replacement
risk: light
covers: R2
files: gridcalc/sheet.py, tests/test_store.py
acceptance:
- extends Sheet from 1.1 (same class — no parallel store)
- set/get round-trips int and str values; get of a never-set cell is None
- set accepts a str starting with "=" without error (stored as a formula;
  evaluation is phase 2's job — tests in this phase never call get on a
  formula cell)
- bool raw raises ValueError; float, None, list raws raise ValueError
- int-subclass and str-subclass instances are accepted and normalized:
  type(get(...)) is exactly int or str after storing them
- set returns None on success; set on an occupied cell replaces content
  (int→str→formula transitions all work)
- a set that raises ValueError leaves prior content and eval_count
  unchanged
- eval_count stays 0 across any sequence of literal set/get calls

## Phase 2: Formulas — core grammar and evaluation
Goal: formula cells evaluate on get with the core grammar (integers,
references, arithmetic, comparisons, parentheses) and the full error
model; recomputing everything on every get is acceptable at this phase.
Phase acceptance: `pytest -q` green; arithmetic/comparison/reference
formulas behave exactly per R3-R6; function-call syntax is not yet in the
grammar, so `=SUM(A1:B2)` is `#PARSE!` at this boundary — consistent with
the grammar-closure rule; every phase-1 test still green.

### Task 2.1: Parser tokenizer + AST contract
risk: light
covers: R3
files: gridcalc/parser.py, tests/test_parser.py
acceptance:
- creates `gridcalc.parser` with a parse function usable without a Sheet;
  malformed input yields a #PARSE! marker, never an exception
- parse results are explicit enough for later evaluator tasks to distinguish
  ints, refs, unary minus, binary operators, comparisons, and parentheses
  grouping without reparsing source text
- tokenizes INT with leading zeros ("007"), REF tokens ("A1", "A01" — token
  validity is the evaluator's job), binary + - * /, unary -, parentheses,
  all six comparisons, and spaces AND tabs between tokens
- #PARSE! on unknown characters and split two-character operators such as
  "1 < = 2"
- Do NOT assert #PARSE! for uppercase function-call or range syntax
  ("SUM(A1:B2)", "A1:B2") — task 3.1 adds them to the grammar and phase-2
  tests must survive phase 3 unchanged

### Task 2.2: Parser precedence + associativity
risk: light
covers: R3
files: gridcalc/parser.py, tests/test_parser.py
acceptance:
- extends the parser from 2.1 (no parallel parser)
- parses binary + - * /, stacked unary minus ("--1", "2--3"), parentheses,
  and all six comparisons into the AST contract from 2.1
- precedence encoded: "1+2*3" groups * first; "1<2<3" associates left;
  unary minus binds tighter than * /
- spaces and tabs are accepted before/after any token in the supported
  phase-2 grammar
- #PARSE! on empty input, lowercase refs/names such as "a1" and
  "sum(A1:B2)", multi-letter non-function names such as "AA1", and
  unbalanced parens

### Task 2.3: Parser R12 depth bounds
risk: light
covers: R12
files: gridcalc/parser.py, tests/test_parser.py
acceptance:
- extends the parser from 2.1/2.2 (no parallel parser)
- malformed input still yields #PARSE!, never an exception
- R12 sizing from day one: a ~510-deep unary-minus tower within 512 chars
  parses without raising
- R12 sizing from day one: 32-deep nested parentheses parse without raising
- the depth-bound tests exercise the same public parse function used by
  tasks 2.1 and 2.2

### Task 2.4: Evaluator — arithmetic, references, division
risk: light
covers: R4, R6, R12
files: gridcalc/evaluator.py, gridcalc/sheet.py, tests/test_eval.py
acceptance:
- extends the parser from 2.1-2.3 and Sheet from 1.1/1.2 (no parallel parser
  or store)
- get on a formula cell returns the computed int: "=1+2*3" is 7,
  "=(1+2)*3" is 9, "=--1" is 1, "=2--3" is 5, "=007" is 7
- division truncates toward zero: "=7/2" is 3, "=-7/2" is -3, "=7/-2" is
  -3; "=7/0" is "#DIV!"
- references read numerically: number cell contributes its value; empty
  cell contributes 0 ("=Z9+1" is 1 on a fresh sheet); string cell yields
  "#TYPE!" (bare "=A1" with A1 a string too); formula cells chain
- reference-shaped tokens denoting no grid cell ("=A01", "=A0", "=A100")
  yield "#REF!"
- after any set, subsequent gets reflect the current sheet (full
  recompute acceptable)
- get on a #PARSE! formula returns "#PARSE!"
- R12 sizing from day one: a 256-formula-cell reference chain evaluates
  without raising (architecture note: this rules out naive recursion
  under CPython's default limit — see spec Engineer Lens)

### Task 2.5: Comparisons + error values and propagation
risk: light
covers: R3, R5
files: gridcalc/evaluator.py, tests/test_errors.py
acceptance:
- extends the evaluator from 2.4
- all six comparisons yield 1/0 ints; "=1<2<3" is 1; "=1+1=2" is 1;
  "=2<>2" is 0
- comparison with a string operand yields "#TYPE!"
- error strings are exactly "#PARSE!", "#REF!", "#TYPE!", "#DIV!",
  "#CYCLE!" per R5; the first four are tested behaviorally here, and
  errors propagate through references (#CYCLE! behavior is task 3.2's)
- with errors in several operands, the textually left-most wins: with B1
  and C1 both errors, "=A1+B1*C1" returns B1's error
- "=1/0+A1" is "#DIV!" whatever A1 holds (short-circuit at the value
  level; the counter-visible half is task 4.1's criterion)

## Phase 3: Ranges, functions, cycles
Goal: the complete R3 grammar including function calls, range function
semantics, and circular-reference detection — still a full-recompute
engine.
Phase acceptance: `pytest -q` green; the grammar is complete per R3
(function calls now parse and evaluate); R7-R9 hold exactly; every
phase-1/2 test still green.

### Task 3.1: Function grammar + SUM/MIN/MAX/COUNT
risk: light
covers: R3, R7, R8
files: gridcalc/parser.py, gridcalc/evaluator.py, tests/test_parser.py, tests/test_functions.py
acceptance:
- extends the parser from 2.1-2.3 and the evaluator from 2.4/2.5 (grammar
  grows; no parallel implementations)
- function calls are primaries and compose: "=SUM(A1:B2)+1",
  "=-MAX(A1:A2)*2" evaluate; whitespace around ":" is legal
  ("=SUM(A1 : B2)")
- #PARSE! on: unknown names ("=AVG(A1:A2)"), lowercase ("=sum(A1:B2)"),
  "=SUM(A1)", "=A1:B2" outside a function, "=SUM((A1:B2))"
- #REF! on: mis-ordered ranges ("=SUM(B2:A1)"), out-of-grid endpoints
  ("=SUM(A0:B2)", "=SUM(A1:A100)")
- visit order row-major; first error in visit order wins at the value
  level (a string cell's "#TYPE!" occupies its position); the
  counter-visible half of range short-circuit is task 4.1's criterion
- SUM skips empty cells and is 0 on an all-empty range; MIN/MAX use
  non-empty numeric contributions and are "#TYPE!" on an all-empty range;
  any string cell makes SUM/MIN/MAX "#TYPE!"
- COUNT counts non-empty cells (numbers, strings, formulas) without
  evaluating them and never errors beyond an invalid range's "#REF!";
  A1 holding "=COUNT(A1:A1)" is 1

### Task 3.2: Circular-reference detection
risk: heavy
covers: R9
files: gridcalc/evaluator.py, tests/test_cycles.py
acceptance:
- extends the evaluator from 3.1
- self-reference: A1 "=A1" is "#CYCLE!"
- mutual: A1 "=B1", B1 "=A1" — both "#CYCLE!"
- through a range: A1 "=SUM(A1:B1)" is "#CYCLE!"; COUNT does not
  participate (A1 "=COUNT(A1:A1)" stays 1)
- a cell off the cycle referencing one returns "#CYCLE!" (propagation)
- breaking the cycle with a set recovers: subsequent gets return correct
  values per the naive model

## Phase 4: Incremental recomputation
Goal: the engine becomes lazy and dependency-aware with the observable
eval_count contract — while phases 1-3 behavior stays byte-identical.
Phase acceptance: the FULL `pytest -q` suite green including every
phase 1-3 test unchanged; R10 delta bounds, the R11 differential floor,
and R12 bounds all pass.

### Task 4.1: Lazy evaluation, result caching, eval_count
risk: light
covers: R10, R5, R7, R8
files: gridcalc/sheet.py, gridcalc/evaluator.py, tests/test_counter.py
acceptance:
- extends the engine from phase 3 (rework in place; no parallel engine)
- set never changes eval_count (formula sets included)
- during a get, eval_count rises by exactly 1 per formula cell whose
  computation starts; literal/empty reads add 0
- repeat read adds 0 — number results AND error results ("#PARSE!",
  "#CYCLE!" included) are cached
- after ANY set, subsequent gets still reflect the current sheet — a
  conservative invalidation (e.g. clear the whole cache on every set) is
  acceptable at this task; 4.2 replaces it with dependency-aware
  invalidation. Do NOT write tests asserting deltas that depend on the
  conservative strategy (e.g. a nonzero delta after an edit outside the
  closure) — 4.2 tightens those to 0 and 4.1's tests must survive it
  unchanged
- counter-visible short-circuit: with Y1 a formula cell, evaluating
  "=1/0+Y1" never starts Y1's computation (its delta contribution is 0)
- counter-visible range semantics: members after the first error in a
  SUM/MIN/MAX range are never computed (delta excludes them), and COUNT
  adds 0 for its range members however many formulas they hold

### Task 4.2: Dependency graph + dirty propagation
risk: heavy
covers: R10, R11
files: gridcalc/sheet.py, gridcalc/evaluator.py, tests/test_incremental.py
acceptance:
- extends the caching layer from 4.1 (invalidation replaces
  recompute-everything; no parallel cache)
- irrelevant edit: set(Y) with Y outside X's reference closure, then
  get(X) adds 0
- relevant edit: set(Y) with Y inside the closure (set(X, ...) itself
  included), then get(X) returns the updated value and adds ≥1 and at
  most the number of formula cells in X's closure (X included) — a
  formula cell outside the closure is never recomputed
- closure semantics: range members count (empty cells and COUNT ranges
  included); an invalid range contributes no members; a #PARSE! formula's
  closure is itself; an edit that leaves X literal/empty makes the final
  get add 0
- a set writing identical content still counts as an edit (≥1 on the
  next dependent get)
- every phase 1-3 test AND every 4.1 test passes unchanged

### Task 4.3: Bounds hardening
risk: light
covers: R12
files: gridcalc/parser.py, gridcalc/evaluator.py, tests/test_bounds.py
acceptance:
- extends the engine from 4.2
- within-bounds evaluations never raise: 32-deep nested parentheses; a
  ~510-deep unary-minus tower inside 512 chars; a 256-formula-cell
  reference chain
- magnitude bound: within-bounds arithmetic whose intermediates and
  results stay at or below |2**63 - 1| completes without raising (e.g. a
  multiplication chain peaking near the bound)
- confinement: with a >512-char formula sitting in an unrelated cell,
  set succeeds and within-bounds gets keep all guarantees

### Task 4.4: Seeded differential suite
risk: light
covers: R11
files: tests/test_differential.py
acceptance:
- test-only task against the engine from 4.3 (no production changes
  expected; the naive reference lives inside the test file and shares no
  code with gridcalc's engine)
- the in-test reference implements the spec's naive full-recompute model
  including references, functions, errors, and cycles
- at least 1000 seeded random set/get sequences of length ≥50 over a
  bounded region (literals, formulas, functions, errors, cycles mixed)
  cross-checked against the reference — zero mismatches, seeds fixed or
  logged

## Re-plans

## Planning notes (frontier author)
Experiment W arm B (multi-session drift): the plan is deliberately
structured so later phases rewrite earlier phases' evaluation path —
phase 3 grows phase 2's parser, phase 4 rewrites phase 2-3's evaluation
strategy while their tests must stay green unchanged. Dependencies are
named in each task's first acceptance line ("extends ... — no parallel
implementation") per loopplan 0.14 guidance. Risk tags: 3.2 heavy (in-progress-set state machine
with partial-failure branches), 4.2 heavy (invalidation state machine —
the experiment's designed trap); the rest light (pure in-memory logic,
whole surface unit-testable, per the risk rule). The scope/risk audit
noted all three heavies are pure in-memory logic — they are kept heavy
deliberately: 3.2/4.2 are state machines with partial-failure branches
(the rule's own heavy criterion, kvtx precedent), and Experiment W
exercises the heavy panel across multi-session distance by design
("when in doubt, heavy"). R12's sizing constraints are pulled forward
into 2.3/2.4 acceptance so the parser/evaluator architecture is right
from day one instead of discovered at 4.3. Phase 2 ships with function
syntax as #PARSE! (grammar-closure-consistent interim; 2.1/2.2 tests
assert #PARSE! only for inputs that stay invalid in the final grammar,
so phase-2 tests survive phase 3 unchanged), and each phase is a
shippable increment. R coverage: R1(1.1) R2(1.2) R3(2.1, 2.2, 2.5, 3.1)
R4(2.4) R5(2.5, 4.1) R6(2.4) R7(3.1, 4.1) R8(3.1, 4.1) R9(3.2)
R10(4.1, 4.2) R11(4.2, 4.4) R12(2.3, 2.4, 4.3).
