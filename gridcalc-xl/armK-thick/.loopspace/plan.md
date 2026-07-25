# Plan: gridcalc-xl
version: 1
status: approved

## Phase 1: Workbook Shell and Cell Store
Goal: A minimal importable package supports workbook/sheet creation, raw cell storage, API validation, and passing tests for literal reads.
Phase acceptance: `pytest -q` passes with `from gridcalc import Workbook`, no public API outside the R21 surface is introduced, and literal cell behavior matches R1/R2 without formula evaluation.

### Task 1.1: Package skeleton and workbook API
risk: heavy
covers: R21
files: gridcalc/__init__.py, gridcalc/workbook.py, tests/test_workbook_api.py
acceptance:
- imports `Workbook` from `gridcalc` and exposes `gridcalc.__all__ == ["Workbook"]`
- creates an empty workbook with `sheet_names == []`, `clock == 0`, and empty undo/redo history returning `False`
- `add_sheet` accepts valid sheet names, returns handles, preserves creation order in a fresh `sheet_names` list, and rejects non-strings, invalid names, and duplicates with `ValueError`
- `sheet(name)` returns handles for existing names and raises `ValueError` for unknown or invalid names
- non-underscore public attributes of `Workbook` and sheet handles contain no names outside the R21 public surface, while later R21 methods may still be unimplemented until their planned phases
- runtime package uses only the Python standard library and static checks find no file I/O or network imports in runtime code

### Task 1.2: Address validation and literal storage
risk: light
covers: R1, R2
files: gridcalc/workbook.py, tests/test_cell_store.py
acceptance:
- sheet `set(addr, raw)` accepts valid unqualified addresses `A1` through `Z99`, rejects invalid or qualified addresses with `ValueError`, and leaves state unchanged on failure
- `set` accepts plain `int`, accepted `int` subclasses except `bool`, plain `str`, and `str` subclasses, normalizing stored values to plain `int` or `str`
- `get` on never-set cells returns `None`; `get` on literal cells returns the stored `int` or `str` unchanged
- replacing an occupied cell changes only that cell and does not evaluate formulas or change `eval_count`
- `get` with invalid address arguments raises `ValueError` and leaves contents, caches, and counters unchanged

## Phase 2: Scalar Formula Evaluation
Goal: A single sheet evaluates scalar integer formulas, references, errors, and cycles lazily with deterministic v1 semantics.
Phase acceptance: Scalar formula tests pass for grammar, arithmetic, references, error ordering, and cycle detection on one sheet, while Phase 1 literal/API tests remain green.

### Task 2.1: Parser for Phase 2 scalar expressions
risk: heavy
covers: R3
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_formula_parser.py
acceptance:
- formula text after `=` parses the Phase 2 slice of R3 for comparisons, additive, term, unary minus, primaries, integer literals, parentheses, single-cell references, spaces, and tabs; later tasks extend this parser for ranges, strings, names, sheet qualifiers, `#REF!`, `CONCAT`, `LEN`, `IF`, and `NOW`
- malformed Phase 2 formula text including `=`, lowercase or mixed-case identifiers, invalid whitespace inside two-character operators, and invalid identifiers evaluates to `#PARSE!`
- integer literals allow leading zeros and evaluate by numeric value
- comparisons are left-associative and return integer `1` or `0`
- runtime parser/evaluator code contains no `eval(`, `exec(`, `compile(`, `__import__`, `importlib`, or `pickle`

### Task 2.2: Arithmetic, references, and error ordering
risk: light
covers: R4, R5, R6, R13
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_scalar_eval.py
acceptance:
- `+`, `-`, `*`, unary minus, and integer division evaluate with truncation toward zero and division by zero returns `#DIV!`
- references read typed values from number, string, formula, and empty cells, with empty single-reference contexts contributing integer `0`
- formulas that reference string literal cells already obey R13's scalar type rules: arithmetic, unary minus, and orderings return `#TYPE!`; `=` and `<>` compare two strings exactly and reject mixed int/string operands with `#TYPE!`
- references with leading-zero or out-of-grid rows parse but evaluate to `#REF!`
- error values are exactly `#PARSE!`, `#REF!`, `#TYPE!`, `#DIV!`, `#CYCLE!`, and `#NAME!`, returned as strings without exceptions for within-bounds evaluations
- operand evaluation is depth-first textual left-to-right, short-circuits at the first error, and later formula cells are not evaluated as shown by unchanged `eval_count`

### Task 2.3: Lazy counters, caching, and single-sheet cycles
risk: light
covers: R9, R10
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_cycles_and_counters.py
acceptance:
- `eval_count` starts at `0`, increments exactly once when a formula cell computation starts, and never increments for literal or empty reads
- consecutive `get` of the same unchanged formula cell returns the cached result with `+0` eval_count delta
- direct, mutual, and dependent cycles evaluate to `#CYCLE!` without starting already-in-progress cells twice
- mutating operations implemented so far never evaluate formulas or change `eval_count`

## Phase 3: Ranges and Aggregate Functions
Goal: Single-sheet ranges, aggregate functions, structural counting, and range-cycle semantics work over the Phase 2 evaluator.
Phase acceptance: Aggregate and cycle tests pass for row-major ranges, empty-cell treatment, structural `COUNT`, and invalid range behavior without regressing scalar evaluation.

### Task 3.1: Range validation and SUM/MIN/MAX
risk: light
covers: R3, R7, R8
files: gridcalc/formula.py, gridcalc/workbook.py, tests/test_ranges.py
acceptance:
- parser accepts `SUM`, `MIN`, and `MAX` only with one range argument, rejects wrong arity, unknown aggregate callees, illegal standalone ranges, and parenthesized ranges with `#PARSE!`
- ranges validate endpoint grid membership and top-left to bottom-right ordering, returning `#REF!` for invalid endpoints or misordered ranges
- range cells are visited row-major and `SUM`, `MIN`, and `MAX` short-circuit on the first error in visit order
- empty cells contribute nothing to range aggregates; all-empty `SUM` returns `0`; all-empty `MIN` and `MAX` return `#TYPE!`
- string contributions to `SUM`, `MIN`, or `MAX` return `#TYPE!` at the first offending range member in visit order

### Task 3.2: COUNT and range cycle behavior
risk: light
covers: R3, R8, R9
files: gridcalc/formula.py, gridcalc/workbook.py, tests/test_count_and_range_cycles.py
acceptance:
- parser accepts `COUNT` only with one range argument and rejects wrong arity or illegal range placement with `#PARSE!`
- `COUNT(range)` returns the number of non-empty cells including number, string, and formula cells without evaluating any range members
- `COUNT` returns `#REF!` only for invalid ranges and never contributes member cells to cycle detection
- cycles through `SUM`, `MIN`, or `MAX` ranges return `#CYCLE!` for cycle members and propagate by R5/R6/R7 to dependents
- `eval_count` evidence proves `COUNT(A1:A1)` in `A1` returns `1` and does not re-enter the formula

## Phase 4: Incremental Recalculation and Differential Oracle
Goal: Cached evaluation and invalidation obey R10/R11/R12 for the current single-sheet feature set under directed and randomized checks.
Phase acceptance: Incrementality tests and a dense seeded naive-reference harness pass while all previous semantics remain green.

### Task 4.1: Dependency closure and invalidation
risk: heavy
covers: R10
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_incremental_recalc.py
acceptance:
- computes reference closures for parseable formulas including direct references, range members, `COUNT` range members, transitive dependencies, and cycles
- after an irrelevant edit outside `X`'s closure, `get(X)` returns the cached value with total eval_count delta `0`
- after a relevant edit intersecting `X`'s closure, `get(X)` recomputes and adds at least `1` but at most the number of formula cells in `X`'s closure
- writing content identical to the existing content still counts as a relevant edit for invalidation

### Task 4.2: Naive reference and randomized equivalence floor
risk: light
covers: R11
files: tests/reference_model.py, tests/test_differential.py
acceptance:
- implements an independent naive full-recompute reference for the single-sheet features available through Phase 4
- runs at least 1000 fixed-seed API sequences of length at least 50 over a dense pool of 12 addresses (`A1`, `A2`, `B1`, `B2`, `C1`, `C2`, `D1`, `D2`, `E1`, `E2`, `F1`, `F2`) on one sheet
- sequence operations include successful and failing `set`, `get`, and formula edits, asserting `ValueError` leaves state unchanged and every `get` matches the naive reference
- logs or parametrizes seeds so every mismatch is reproducible

### Task 4.3: Bounds and damage confinement
risk: light
covers: R12
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_bounds.py
acceptance:
- within-bounds evaluations with formula text length at most 512, parenthesis nesting at most 32, at most 256 reached formula cells, and integer magnitudes at most `2**63 - 1` complete without raising
- directed tests cover a 256-formula dependency chain and a deeply nested/unary expression within R12 limits without `RecursionError`
- out-of-bounds evaluations terminate by returning or raising and do not corrupt later within-bounds `get` results in the same workbook
- mutating operations always store out-of-bounds formula texts without evaluating them

## Phase 5: String Semantics and Conditional Functions
Goal: Formula values become typed integers or strings with closed type rules, string functions, and lazy conditional branches.
Phase acceptance: String, `CONCAT`, `LEN`, and `IF` tests pass, including left-to-right type/error precedence and static closure behavior.

### Task 5.1: String literals and type rules
risk: light
covers: R13
files: gridcalc/formula.py, gridcalc/workbook.py, tests/test_strings_and_types.py
acceptance:
- parses string literals as primaries with no escapes, preserving every non-quote character including newlines and control characters
- arithmetic, unary minus, and ordering comparisons reject string operands with `#TYPE!` according to R5 textual left-to-right precedence
- `=` and `<>` compare two ints or two strings and return `1` or `0`; mixed int/string comparisons return `#TYPE!`
- operands after the first type offender or error are not evaluated, with `eval_count` evidence

### Task 5.2: CONCAT and LEN
risk: light
covers: R14
files: gridcalc/formula.py, tests/test_string_functions.py
acceptance:
- `CONCAT` accepts one or more expression arguments, evaluates left-to-right, short-circuits on first error, renders ints in base 10 without leading zeros, and preserves string arguments as-is
- `CONCAT` renders empty-cell reference arguments as `"0"`
- `LEN` accepts exactly one expression argument and returns character counts for strings or decimal-rendered ints
- wrong arity or empty-call forms for `CONCAT` and `LEN` evaluate to `#PARSE!`

### Task 5.3: IF evaluation and static closure
risk: light
covers: R15, R10
files: gridcalc/formula.py, gridcalc/workbook.py, tests/test_if_function.py
acceptance:
- `IF(condition, then_expr, else_expr)` evaluates the condition first; error conditions return that error and string conditions return `#TYPE!`
- integer conditions select the second argument when nonzero and the third when zero, returning the selected branch value of any type
- the unselected branch is not evaluated even if it contains errors or formula cells, with `eval_count` evidence
- R10 closure for an `IF` formula statically includes references in the condition and both branches for invalidation purposes
- extends the naive reference model from Task 4.2 to cover string literals, string type rules, `CONCAT`, `LEN`, and `IF`, with directed equivalence tests for the new semantics

## Phase 6: Copy and Named Ranges
Goal: Absolute references, formula-copy rewriting, `#REF!` token behavior, and per-sheet names work on the single-sheet engine.
Phase acceptance: Copy and name tests pass for literal/formula copying, `$` marks, out-of-grid rewrites, name validation/resolution, and invalidation on name redefinition.

### Task 6.1: Mutation journal foundation
risk: light
covers: R19
files: gridcalc/workbook.py, tests/test_mutation_journal.py
acceptance:
- journals successful `set` and `add_sheet` operations implemented before Phase 6, while failed calls, `get`, `sheet`, `sheet_names`, and observations never journal
- `undo()` reverts the most recent not-yet-undone `set` or `add_sheet` entry and returns `True`, or returns `False` with no change when none exists
- `redo()` reapplies the most recently undone `set` or `add_sheet` entry and returns `True`, or returns `False` with no change when none exists
- a new successful journaled operation clears the redo stack
- undo/redo restore prior cell contents including never-set state and added sheets in strict LIFO order

### Task 6.2: Absolute references and copy rewriting
risk: heavy
covers: R16, R17, R19
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_copy.py
acceptance:
- parser accepts optional `$` marks on reference and range endpoints, with evaluation identical to unmarked references
- parser accepts user-authored `#REF!` as a grammar-legal primary and as a `RANGE-ARG`, always evaluating to the error string `#REF!`
- extends the journal from Task 6.1 so `copy(src, dst)` validates arguments, rejects empty sources with `ValueError`, journals success, and never evaluates formulas or changes counters
- copying literals stores identical normalized values; copying unparseable or out-of-bounds formula text preserves it byte-for-byte
- copying parseable formulas shifts unmarked row/column components by destination delta, preserves `$`-marked components, and leaves invalid-grid references with leading zeros or out-of-range rows verbatim
- shifted bare references leaving the grid are replaced by `#REF!`, and shifted unqualified ranges with any endpoint leaving the grid replace the whole range expression by `#REF!`
- undo immediately after a successful `copy` restores the target cell's previous content including never-set state, and redo reapplies the copy

### Task 6.3: Named ranges and name invalidation
risk: light
covers: R18, R19
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_names.py
acceptance:
- extends the journal from Task 6.1 so `define_name(name, target)` accepts valid per-sheet names and valid unqualified address or range targets, returns `None`, journals success, and never evaluates formulas
- invalid names, function-name collisions, REF-shaped names, non-string arguments, invalid targets, and misordered ranges raise `ValueError` with no state change or journal entry
- `NAME` tokens resolve as primaries to a single target cell typed value, as range arguments to the target range, to `#REF!` when a larger range is used as a primary, and to `#NAME!` when undefined
- redefining a name changes dependent formula values and invalidates every parsed formula cell on that sheet mentioning the name, even when the binding is identical
- undo immediately after a successful `define_name` restores the previous binding including undefined, and redo reapplies the definition
- extends the naive reference model from Phase 5 to cover `copy`, `$` rewrite rules, `#REF!` copy tokens, and named ranges, with directed equivalence tests for the new semantics

## Phase 7: Undo and Redo
Goal: All successful mutating operations participate in one LIFO journal with correct state restoration, redo clearing, handle lifecycle, counters, and caches.
Phase acceptance: Undo/redo tests pass across all operations implemented through Phase 6 without decreasing counters or violating naive value equivalence.

### Task 7.1: Mutation journal and basic undo/redo
risk: light
covers: R19
files: gridcalc/workbook.py, tests/test_undo_redo.py
acceptance:
- extends the journal from Task 6.1 through Task 6.3 so successful `set`, `copy`, `define_name`, and `add_sheet` operations all participate in one LIFO history
- failed calls, `get`, `sheet`, `sheet_names`, and observations never journal
- `undo()` and `redo()` preserve strict LIFO behavior across mixed `set`, `copy`, `define_name`, and `add_sheet` sequences
- a new successful journaled operation after undo clears the redo stack
- undo/redo restore prior cell contents including never-set state, prior name bindings including undefined, and added sheets in strict LIFO order

### Task 7.2: Undo/redo counters, caches, and handles
risk: light
covers: R19, R20
files: gridcalc/workbook.py, tests/test_undo_redo_counters.py
acceptance:
- `eval_count` is monotonic across undo/redo and never decreases
- after any undo/redo sequence, `get` values match naive recomputation of restored contents, bindings, sheet set, and current clock
- undo/redo invalidation touch sets match the reverted or reapplied operation for R10 irrelevant/relevant edit bounds
- handles bound to a removed sheet name raise `ValueError` on every member access including `eval_count`, and work again after redo or a fresh add of the same name restores that sheet name
- extends the naive reference model from Phase 6 to cover `undo` and `redo`, with directed equivalence tests for journal restoration and redo clearing

## Phase 8: Multi-Sheet Semantics
Goal: Workbook-level sheet identity, qualified references, cross-sheet copy/name targets, and cross-sheet dependency tracking work with existing semantics.
Phase acceptance: Multi-sheet tests pass for qualified grammar, binding, cross-sheet cycles, per-sheet counters, copy/name argument extensions, and creation-order behavior.

### Task 8.1: Sheet lifecycle and public surface completion
risk: light
covers: R21
files: gridcalc/workbook.py, tests/test_sheet_lifecycle.py
acceptance:
- sheet names validate exactly by R21 and are case-sensitive; `sheet_names` reflects creation order through undo/redo and returns a fresh list each call
- eval_count is kept per sheet name for the workbook lifetime and resumes after undo/redo or fresh re-creation of the same name
- every API-wide string argument accepts `str` subclasses and normalizes stored names, addresses, bindings, and raw contents to plain `str`
- no additional public methods or classes are exposed beyond R21

### Task 8.2: Qualified references and ranges
risk: light
covers: R22
files: gridcalc/formula.py, gridcalc/workbook.py, tests/test_qualified_refs.py
acceptance:
- parser accepts qualified references and whole qualified ranges with whitespace around `!`, and binds unqualified references to the formula's hosting sheet
- tokenization treats any sheet-name-shaped identifier followed by `!` as a sheet token, including `SUM!A1` and `A1!B2`
- malformed qualifiers, invalid sheet-name tokens before `!`, or second qualifiers inside a range produce `#PARSE!`
- well-shaped qualifiers naming no current sheet evaluate to `#REF!` and contribute no closure members while absent
- `add_sheet(S)` and undo/redo removing or restoring `S` invalidate every parsed formula cell mentioning qualifier `S`

### Task 8.3: Cross-sheet semantics and argument extensions
risk: heavy
covers: R23, R10, R11, R12
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_cross_sheet.py
acceptance:
- R5 ordering, R7 row-major visits, R9 cycle detection, R10 closures, and R12 256-cell reach operate over `(sheet, address)` identity and sum counter deltas across sheets
- cross-sheet cycles through references or ranges return `#CYCLE!` for cycle members and propagate to dependents
- unqualified references and `NAME` tokens in a copied formula re-resolve against the destination sheet
- `copy(src, dst)` accepts either argument as unqualified or `SHEET!ADDR` with no whitespace, raises `ValueError` for unknown sheets or malformed qualified arguments, and can copy across sheets
- copying formulas with qualified references shifts the `REF` part exactly as R17 specifies, preserves qualifiers, and replaces whole qualified references or qualified ranges with `#REF!` when shifted endpoints leave the grid
- `define_name` target accepts unqualified or `SHEET!ADDR` / `SHEET!ADDR:ADDR` with no whitespace and validates target sheet existence

### Task 8.4: Multi-sheet differential floor
risk: light
covers: R11, R23
files: tests/reference_model.py, tests/test_differential_multisheet.py
acceptance:
- extends the independent naive reference to all features through Phase 8
- runs at least 1000 fixed-seed API sequences of length at least 50 over exactly 3 sheets and a dense pool of 12 addresses (`A1`, `A2`, `B1`, `B2` on each sheet)
- interleaves well-formed successful and failing `set`, `get`, `copy`, `define_name`, `add_sheet`, `undo`, and `redo` calls, re-adding pool sheets removed by undo before further pool use
- asserts `ValueError` leaves state unchanged and every `get` across all pool sheets matches the naive reference

## Phase 9: Persistence
Goal: Clock state and string-based persistence round-trip stored state exactly, reject invalid inputs safely, and preserve semantic equivalence without persisting journals or caches.
Phase acceptance: Clock journaling, persistence, adversarial input, static security, and post-round-trip differential tests pass while all previous phases remain green.

### Task 9.1: Clock API for persisted state
risk: light
covers: R26, R19, R20
files: gridcalc/workbook.py, tests/test_clock_api.py
acceptance:
- `wb.clock` starts at `0` and is read-only; `advance_clock()` increments by exactly `1`, returns the new value, and journals success
- undo/redo of `advance_clock` restores and reapplies prior clock values without appending new journal entries
- `advance_clock` never evaluates formulas and does not change any `eval_count`
- existing undo/redo tests include clock operations in LIFO order and redo clearing

### Task 9.2: to_json and from_json state restoration
risk: heavy
covers: R24
files: gridcalc/workbook.py, tests/test_persistence.py
acceptance:
- `to_json()` returns a `str` accepted by `json.loads`, evaluates nothing, changes no counter, and appends no journal entry
- `Workbook.from_json(s)` is a classmethod that accepts only `str` inputs and returns a new workbook satisfying all invariants or raises without corrupting other workbooks
- `Workbook.from_json(s)` failure does not corrupt interpreter-global state, with a directed test using an unrelated workbook before and after invalid inputs
- round-tripped workbooks restore sheet names and creation order, every stored cell content including formula text byte-for-byte, every sheet's name bindings, and the clock value
- round-tripped workbooks reset journal, redo stack, every `eval_count`, and evaluation caches; `undo()` immediately after loading returns `False`
- invalid JSON, valid JSON with wrong shapes, any JSON float including `NaN`, `Infinity`, and `1.0`, invalid sheet names, invalid addresses, invalid bindings, and duplicate names raise `ValueError` except pathological `json.loads` exceptions allowed by R24

### Task 9.3: Persistence security and adversarial corpus
risk: heavy
covers: R24
files: gridcalc/workbook.py, tests/test_persistence_security.py
acceptance:
- tests at least 30 adversarial `from_json` cases spanning non-string inputs, invalid JSON, valid-JSON wrong shapes (`null`, `[]`, numbers, bare strings), floats, invalid sheet names, invalid addresses, invalid bindings, and deep nesting excluding exhaustion-shaped inputs
- `from_json` never executes or imports anything based on input, with a static source check that runtime code contains no `eval(`, `exec(`, `compile(`, `__import__`, `importlib`, or `pickle`
- every adversarial input either raises the permitted exception type or returns a workbook satisfying the public invariants; no partial workbook is exposed
- after any adversarial failure, an unrelated workbook remains usable and within-bounds `get` results remain correct

### Task 9.4: Round-trip semantic equivalence
risk: light
covers: R25, R11
files: tests/reference_model.py, tests/test_roundtrip_equivalence.py
acceptance:
- for every workbook reachable by successful API calls in directed tests, `Workbook.from_json(wb.to_json())` has the same `sheet_names`, `clock`, and `get` results for every address `A1` through `Z99` on every sheet
- subsequent identical successful API sequences applied to original and round-tripped workbooks, excluding undo/redo, produce identical `get` results and further round-trip behavior
- `copy` after round-trip rewrites exactly the restored formula text it would have rewritten before the round-trip
- extends the dense 3-sheet 12-address differential harness with `to_json`/`from_json` round-trips interleaved in at least 1000 fixed-seed sequences of length at least 50

## Phase 10: Volatility and XL Bounds Completion
Goal: NOW-driven volatility and XL string/cross-sheet bounds complete the v1 spec surface with final differential and boundary coverage.
Phase acceptance: The full test suite passes, including volatile recalculation, XL bound extensions, static security checks, and all directed and randomized floors from the spec.

### Task 10.1: NOW() function
risk: light
covers: R26
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_clock_now.py
acceptance:
- parser accepts exactly uppercase `NOW()` with empty parentheses and evaluates it to the current clock as an `int`
- `NOW` with arguments and empty parentheses on other functions evaluate to `#PARSE!`

### Task 10.2: Volatile invalidation and warm bound
risk: heavy
covers: R27, R10, R11
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_volatile_recalc.py
acceptance:
- statically marks a formula cell volatile when any parsed formula in its closure contains a `NOW()` call, including unselected `IF` branches, and ignores `NOW` text inside string literals or `#PARSE!` formulas
- every `get` involving volatile formulas matches naive recomputation at the current clock
- repeat reads with no edit have eval_count delta `0` even for volatile formulas
- clock edits invalidate exactly volatile formula cells; non-volatile closures have eval_count delta `0` after clock-only edits
- after the R27 warm-up precondition, one or more clock-only edits followed by `get(X)` add at most the number of volatile formula cells in `X`'s closure

### Task 10.3: XL bounds and final randomized floor
risk: heavy
covers: R28, R11, R12, R25
files: gridcalc/workbook.py, gridcalc/formula.py, tests/test_xl_bounds.py, tests/test_differential_full.py
acceptance:
- R12's 256-formula reach is enforced across all sheets, and string intermediates/results including literals, `CONCAT`, and decimal renderings are within bounds up to length 4096
- evaluations producing out-of-bounds string intermediates or results over 4096 characters terminate by returning or raising and do not corrupt later within-bounds `get` results in the same workbook
- out-of-bounds formula texts exceeding R12(a) are copied byte-for-byte unchanged and do not break later within-bounds evaluations
- closure, mention, and volatility accounting over formula texts exceeding R12(a) is not asserted, but storing, copying, journaling, and undo/redo for those texts succeed
- runs the full-feature independent naive reference over at least 1000 fixed-seed sequences of length at least 50 on exactly 3 sheets and the dense 12-address pool (`A1`, `A2`, `B1`, `B2` on each sheet), interleaving `set`, `get`, `copy`, `define_name`, `add_sheet`, `advance_clock`, `undo`, `redo`, and `to_json`/`from_json` round-trips
- the full-feature generator keeps sequences well-formed exactly as the spec requires: legal failing calls assert `ValueError` and unchanged state, pool sheets removed by undo are re-added before further pool use, and copy sources are constrained so rewrites stay within R12(a)'s 512-character formula limit
- includes directed boundary tests for 256-cell cross-sheet chains, 512-character and 32-parenthesis-depth formulas, 4096-character strings, `2**63 - 1` integer magnitudes, and R5/R13 ordering cases

## Re-plans
<appended by the orchestrator when a task is split/reordered; never edited by hand>
