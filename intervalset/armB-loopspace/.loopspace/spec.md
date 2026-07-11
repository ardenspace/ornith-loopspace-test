# Spec: intervalset
version: 1
status: approved

## Overview
`intervalset` is a small, disposable pure-logic Python library providing one
data structure, `IntervalSet`: a mutable set of integers stored as a
collection of intervals. It is a throwaway fixture — no product, no I/O, no
polish. Its whole surface is a handful of in-memory operations that must
preserve one representation invariant, stated below.

## Goals
- One class, `IntervalSet`, that represents a set of integers as intervals.
- A single, precise representation invariant that every public operation
  preserves.
- Pure, deterministic, pytest-checkable in-memory logic; zero dependencies
  beyond pytest.

## Non-Goals
- No CLI, UI, file, or network I/O.
- No non-integer members; integers only.
- No performance targets, packaging, or real-world hardening.
- No interval flavors other than the one pinned below.

## Company Lens
Purpose is a disposable in-memory fixture. Success = a correct `IntervalSet`
whose operations preserve the representation invariant, with every behavior
expressible as a machine-checkable pytest assertion. Investment is minimal;
scope is one short run, one phase, a few tasks. Safe to halt or fail.

## User Lens
No human end-user. The consumer is a pytest suite. No UX or adoption
concerns.

## Engineer Lens
- Runtime: Python 3.10+; pytest is the only dependency.
- Purity: `contains` and `intervals` are pure reads with no side effects;
  `add` and `remove` mutate the set in place. No I/O, no globals, no
  reliance on external state.
- Representation (PINNED — not open to interpretation):
  - Members are integers. An interval `[start, end]` is CLOSED: it contains
    every integer `i` with `start <= i <= end` (both endpoints included).
  - Endpoints are Python ints; negative values and arbitrary magnitude are
    allowed.
  - A range with `start > end` denotes the EMPTY set: adding or removing it
    changes nothing, and no such range is ever part of the stored intervals.
- Representation invariant (the contract every operation preserves): at all
  times an `IntervalSet` stores the MINIMUM number of intervals whose union
  of closed integer ranges is exactly its current set of integer members —
  no more integers, no fewer. Equivalently, `intervals()` is the
  shortest list of closed integer intervals whose union equals the member
  set. The individual consequences this forces for how ranges combine and
  how a removal reshapes the stored intervals are left to the implementer to
  derive from this property; they are not enumerated here.
- Error handling: inputs are plain ints; `start > end` is the empty set, not
  an error. No other error contract is imposed by this spec.
- Security: no eval, no untrusted execution, no file/network access. Not
  applicable beyond that.
- Testing: TDD with pytest. Tests should cover the consequences the
  representation invariant forces, not merely the happy path.
- Over-engineering boundary: one class, four public methods; no config, no
  class hierarchy, no generalization beyond `IntervalSet`.

## Designer Lens
Not applicable: no UI surface.

## Requirements
- R1: `IntervalSet()` constructs an empty set — it contains no integers, and
  `intervals()` returns an empty list.
- R2: `add(start, end)` adds every integer in the closed range `[start, end]`
  to the set. After the call the representation invariant holds.
- R3: `remove(start, end)` removes every integer in the closed range
  `[start, end]` from the set; removing integers the set does not contain
  affects only those it does. After the call the representation invariant
  holds.
- R4: `contains(point)` returns `True` if the integer `point` is currently a
  member of the set and `False` otherwise.
- R5: `intervals()` returns the current members as a list of `(start, end)`
  integer tuples — one tuple per stored interval, in ascending order —
  reflecting the representation invariant.
- R6: A range with `start > end` denotes the empty set: `add`/`remove` of
  such a range leaves the set unchanged, and `intervals()` never returns
  such a tuple.
- R7 (the invariant as a checkable property): after ANY sequence of
  `add`/`remove` calls, `intervals()` is the shortest list of closed integer
  intervals, sorted ascending, whose union equals exactly the set's current
  members; and `contains(p)` is `True` for exactly those integers `p` that
  lie in one of those intervals.

## Approval
Approved by human (experiment owner) on 2026-07-11.
