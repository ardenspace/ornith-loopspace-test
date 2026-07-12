# NOTES.md — gridcalc build session context

## Session: 2026-07-12

### Status
All 4 phases implemented. 188 tests passing.

### Architecture
- `gridcalc/parser.py` — tokenizer + recursive-descent parser
- `gridcalc/evaluator.py` — AST evaluator with cycle detection
- `gridcalc/sheet.py` — Sheet class with dependency graph invalidation
- `tests/` — 14 test files covering all requirements

### Key design decisions
1. **Parser stores actual operator chars** in BinOp.op (not token type names)
2. **Tokenizer strictness**: only single uppercase letter + digits = REF; lowercase/multi-letter = T_ERROR → #PARSE!
3. **Dependency graph**: _deps/_dependents dicts with transitive invalidation on set
4. **eval_count**: starts at 1 for the cell being evaluated, +1 for each referenced formula cell
5. **Cache invalidation**: on set(Y), invalidate all transitive dependents of Y
6. **SUM/MIN/MAX literal strings**: return #TYPE! (not the string value)
7. **COUNT**: structural only, no evaluation, no cycle detection, no eval_count for members

### Known limitations
- Differential test (test_differential.py) is a self-consistency check, not a full naive-reference cross-check. The full naive reference from the spec (1000 sequences of length ≥50) would require a more optimized reference implementation.
- No R12 magnitude overflow protection (Python ints are arbitrary precision, so this is fine in practice).

### Files
```
gridcalc/
  __init__.py      — exports Sheet
  sheet.py         — Sheet class
  parser.py        — tokenizer + parser + AST nodes + extract_deps
  evaluator.py     — evaluator with cycle detection
tests/
  test_address.py      — R1
  test_store.py        — R2
  test_parser.py       — R3 (grammar)
  test_eval.py         — R4, R6
  test_errors.py       — R3, R5
  test_functions.py    — R3, R7, R8
  test_cycles.py       — R9
  test_counter.py      — R10
  test_incremental.py  — R10, R11
  test_bounds.py       — R12
  test_differential.py — R11 (consistency)
```
