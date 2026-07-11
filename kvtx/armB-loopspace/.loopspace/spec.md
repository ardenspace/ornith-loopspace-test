# Spec: kvtx
version: 1
status: approved

## Overview
`kvtx` is a small, disposable pure-logic Python library providing one
data structure, `Database`: an in-memory key/value store with **nested
transactions** and a value-count query. It is a throwaway fixture — no I/O,
no persistence, no networking. Keys and values are strings. Its difficulty
is entirely in the transaction state machine and keeping `count` consistent
across transaction overlays; the behavior is fully specified below.

## Goals
- One class, `Database`, with `set`, `get`, `delete`, `count`, `begin`,
  `rollback`, `commit`.
- Correct nested-transaction semantics with partial rollback and full
  commit, and a `count(value)` query that always reflects the current
  visible state.
- Pure, deterministic, pytest-checkable in-memory logic; zero dependencies
  beyond pytest.

## Non-Goals
- No CLI, UI, file, or network I/O; no persistence.
- No types other than string keys and string values.
- No performance targets, packaging, or real-world hardening.
- No isolation/concurrency between multiple Database instances; single
  in-memory instance, single thread.

## Company Lens
Purpose is a disposable in-memory fixture whose whole point is a correct,
non-trivial state machine. Success = a `Database` whose transaction and
count semantics match the spec exactly, every behavior a machine-checkable
pytest assertion. Safe to halt or fail.

## User Lens
No human end-user. The consumer is a pytest suite. No UX concerns.

## Engineer Lens
- Runtime: Python 3.10+; pytest is the only dependency.
- Purity: `get`, `count` are pure reads with no side effects; `set`,
  `delete`, `begin`, `rollback`, `commit` mutate the database state in
  place. No I/O, no globals, no reliance on external state.
- Types: keys and values are `str`. `count` returns `int`. `get` returns the
  value `str` or `None`. `rollback`/`commit` return `bool` (see R6/R7).
- Transaction model (state machine): transactions form a stack (they nest).
  Reads (`get`, `count`) always observe the effect of every command issued
  so far under all currently-open transactions, layered over the committed
  base state. `rollback` discards only the innermost open transaction;
  `commit` applies every open transaction. There is no per-instance limit on
  nesting depth.
- Error/edge handling (partial-failure branches): `rollback` and `commit`
  with no open transaction are defined no-ops that report it via their
  return value (R6, R7) — they never raise. `delete` of an absent key is a
  no-op. `get` of an absent key returns `None`. `count` of a value held by
  no key returns `0`.
- Security: no eval, no untrusted execution, no I/O. Not applicable beyond
  that.
- Testing: TDD with pytest. Cover the transaction interactions and the
  `count`/overlay consistency, not just single commands.
- Over-engineering boundary: one class, seven methods; no config, no class
  hierarchy, no persistence layer, no generalization.

## Designer Lens
Not applicable: no UI surface.

## Requirements
- R1: `set(key, value)` records that `key` currently maps to `value`
  (creating or overwriting). `get(key)` returns the current value of `key`,
  or `None` if `key` is not currently set. `delete(key)` makes `key` not
  set; deleting a key that is not set is a no-op.
- R2: `count(value)` returns the number of keys whose current value equals
  `value` (an `int`, `0` if none). Overwriting a key's value with `set`
  updates the counts of both the old and the new value; `delete` decrements
  the count of the deleted key's value. `count` always reflects the current
  visible state, including uncommitted changes in open transactions.
- R3: `begin()` opens a new transaction. Transactions nest: each `begin`
  pushes a new innermost transaction onto a stack. Commands issued while one
  or more transactions are open are provisional until committed.
- R4: `rollback()` discards every change made since the most recent still-open
  `begin()` and closes that (innermost) transaction; any enclosing open
  transactions and the committed base state are unaffected. After a
  rollback, `get` and `count` observe the state as it was just before that
  `begin()`.
- R5: `commit()` permanently applies every change made under every currently
  open transaction to the base state and closes ALL open transactions (the
  transaction stack becomes empty). After a commit there are no open
  transactions.
- R6: `rollback()` returns `True` if a transaction was open (and was rolled
  back) and `False` if no transaction was open, in which case it does
  nothing.
- R7: `commit()` returns `True` if at least one transaction was open (and was
  committed) and `False` if none was open, in which case it does nothing.
- R8: Reads are consistent with the overlay model at all times: `get(key)`
  reflects the innermost open transaction that touched `key` (a `set` shows
  its value; a `delete` shows `None`), else the next enclosing transaction
  that touched it, and finally the committed base; `count(value)` equals the
  number of keys whose thus-resolved current value equals `value`.

## Approval
Approved by human (experiment owner) on 2026-07-11.
