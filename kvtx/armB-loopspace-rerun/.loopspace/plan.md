# Plan: kvtx
version: 1
status: approved

## Phase 1: Database with nested transactions
Goal: a Python package `kvtx` exposing a `Database` class with `set`, `get`,
`delete`, `count`, `begin`, `rollback`, `commit`, whose transaction and
count semantics match the spec exactly, backed by a full green pytest suite.
Phase acceptance: `pytest -q` passes with every acceptance criterion below
covered by a test, no skips/xfails; `from kvtx import Database` works from
the repo root; reads (`get`, `count`) always reflect the overlay model
across arbitrary interleavings of set/delete/begin/rollback/commit.

### Task 1.1: Base store — set, get, delete, count
risk: light
covers: R1, R2
files: kvtx/database.py, kvtx/__init__.py, tests/test_store.py
acceptance:
- set(k, v) then get(k) == v; get of an unset key returns None
- delete(k) makes get(k) return None; delete of an unset key is a no-op (no error)
- overwriting: set(k, "a") then set(k, "b") -> get(k) == "b"
- count(v) returns the number of keys currently mapped to v; count of a value held by no key returns 0
- multiple keys same value: set(a, "x"), set(b, "x") -> count("x") == 2
- overwrite updates BOTH counts: set(a, "x"), set(b, "x"), then set(a, "y") -> count("x") == 1 and count("y") == 1
- delete decrements count: set(a, "x"), set(b, "x"), delete(a) -> count("x") == 1
- deleting the last holder: set(a, "x"), delete(a) -> count("x") == 0
- count returns an int; get returns a str or None

### Task 1.2: Nested transactions — begin, rollback, commit
risk: heavy
covers: R3, R4, R5, R6, R7, R8
files: kvtx/database.py, tests/test_tx.py
acceptance:
- reads see uncommitted writes: begin(), set(a, "1") -> get(a) == "1" and count("1") == 1 before any commit
- rollback undoes writes in the innermost transaction: begin(), set(a, "1"), rollback() -> get(a) is None (a was unset before), and rollback() returned True
- rollback restores a prior value on overwrite: set(a, "1"), begin(), set(a, "2"), rollback() -> get(a) == "1"
- rollback restores a deleted key: set(a, "1"), begin(), delete(a), rollback() -> get(a) == "1"
- nested rollback only undoes the innermost: set(a, "1"), begin(), set(a, "2"), begin(), set(a, "3"), rollback() -> get(a) == "2"; a second rollback() -> get(a) == "1"
- commit applies ALL open transactions and empties the stack: begin(), set(a, "1"), begin(), set(a, "2"), commit() -> get(a) == "2", commit() returned True, and a subsequent rollback() returns False (no open transaction)
- rollback with no open transaction returns False and changes nothing: on a fresh db, rollback() is False and get of any key is unchanged
- commit with no open transaction returns False and changes nothing
- count reflects overlays and is restored by rollback: set(a, "x"), begin(), set(b, "x"), count("x") == 2, rollback(), count("x") == 1
- count reflects overlays and is preserved by commit: set(a, "x"), begin(), set(b, "x"), commit(), count("x") == 2 and no open transaction remains
- overwrite-inside-transaction count consistency: set(a, "x"), begin(), set(a, "y"), count("x") == 0 and count("y") == 1; rollback() -> count("x") == 1 and count("y") == 0
- delete-inside-transaction count consistency: set(a, "x"), set(b, "x"), begin(), delete(a), count("x") == 1; rollback() -> count("x") == 2
- deep nesting with mixed commit point: set(a, "1"), begin(), set(a, "2"), begin(), delete(a), begin(), set(a, "3"), rollback() -> get(a) is None; rollback() -> get(a) == "2"; commit() -> get(a) == "2" with no open transaction
- from kvtx import Database works from the package root and Database exposes set, get, delete, count, begin, rollback, commit

## Re-plans

## Planning notes (frontier author)
Spec is behaviorally precise (unlike the ambiguity experiment): the
difficulty is implementing the transaction state machine and keeping
`count` consistent across overlays, not reading the spec. Task 1.1 is pure
in-memory CRUD with the overwrite/delete count bookkeeping → light. Task 1.2
is a nested state machine with partial-failure branches (rollback restores
prior state; commit folds all levels) and the count/overlay interaction →
heavy, so looprun runs the three-lens panel (correctness / security /
test-integrity) on it. Panel lenses applied inline at plan time:
verifiability (every criterion is a concrete pass/fail sequence),
adversarial (1.1 before 1.2 since transactions layer over the base store;
each task fits one fresh context; phase shippable after 1.1 as a
transaction-less store, complete after 1.2), scope/risk (matches spec, no
gold-plating; 1.2's state machine is honestly heavy, 1.1 honestly light).
No blocking findings.
