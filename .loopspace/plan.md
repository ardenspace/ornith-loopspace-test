# Plan: intervalset
version: 1
status: approved

## Phase 1: IntervalSet
Goal: a Python package `intervalset` exposing an `IntervalSet` class with
`add`, `remove`, `contains`, and `intervals`, whose stored intervals always
satisfy the representation invariant, backed by a full green pytest suite.
Phase acceptance: `pytest -q` passes with every acceptance criterion below
covered by a test, no skips/xfails; `from intervalset import IntervalSet`
works from the repo root; after ANY sequence of `add`/`remove` calls,
`intervals()` returns the shortest ascending list of closed integer
intervals whose union equals exactly the members, with no two returned
intervals overlapping or adjacent, and `contains(p)` agrees with that
membership.

### Task 1.1: IntervalSet — construction, add, contains, intervals
risk: light
covers: R1, R2, R4, R5, R6, R7
files: intervalset/interval_set.py, intervalset/__init__.py, tests/test_add.py
acceptance:
- IntervalSet() is empty: intervals() returns [] and contains(x) is False for any int x
- add(1, 3) then intervals() == [(1, 3)]; contains(1), contains(2), contains(3) are True and contains(0), contains(4) are False
- add(5, 5) (single point) then intervals() == [(5, 5)]
- negative and zero-spanning ranges work: add(-3, -1) -> [(-3, -1)] with contains(-2) True; add(-2, 2) -> [(-2, 2)] with contains(0) True
- overlapping adds merge: add(1, 5) then add(3, 8) -> intervals() == [(1, 8)]
- ADJACENT integer ranges merge with no gap left: add(1, 3) then add(4, 6) -> intervals() == [(1, 6)] (because integers 1..6 are contiguous); add(1, 3) then add(4, 4) -> [(1, 4)]
- ranges separated by at least one missing integer stay separate: add(1, 3) then add(5, 7) -> intervals() == [(1, 3), (5, 7)] (integer 4 is absent)
- a new range that bridges two existing intervals collapses all into one: from add(1, 3) and add(7, 9), then add(4, 6) -> intervals() == [(1, 9)]; a bridge that does not close every gap leaves the remaining split: add(1, 3), add(8, 10), add(5, 6) -> [(1, 3), (5, 6), (8, 10)]
- a fully-contained add changes nothing: add(1, 10) then add(3, 5) -> [(1, 10)]; re-adding the same range is idempotent: add(1, 5) twice -> [(1, 5)]
- add with start > end is a no-op: add(5, 3) on an empty set -> []; add(8, 4) after add(1, 10) leaves [(1, 10)] (R6)
- intervals() is always sorted ascending regardless of insertion order (add(10,12), add(1,2), add(5,6) -> [(1,2),(5,6),(10,12)]), returns (int, int) tuples with start <= end, and no two returned intervals overlap or are adjacent
- contains and intervals are pure reads (no mutation of the set); add mutates in place

### Task 1.2: IntervalSet — remove
risk: light
covers: R3, R6, R7
files: intervalset/interval_set.py, tests/test_remove.py
acceptance:
- removing an interior sub-range splits an interval: add(1, 10) then remove(4, 6) -> intervals() == [(1, 3), (7, 10)]
- removing at the low boundary trims: add(1, 10) then remove(1, 3) -> [(4, 10)]; at the high boundary: remove(8, 10) -> [(1, 7)]
- removing a single interior integer splits: add(1, 5) then remove(3, 3) -> [(1, 2), (4, 5)]
- removing the whole interval empties it: add(1, 10) then remove(1, 10) -> []; a superset removal also empties it: add(3, 6) then remove(1, 10) -> []
- a removal spanning multiple intervals deletes only covered integers: from add(1, 3) and add(6, 8), remove(2, 7) -> [(1, 1), (8, 8)]
- removing integers not present is a no-op for them: add(1, 3) then remove(5, 7) -> [(1, 3)]; remove(1, 5) from an empty set -> []
- remove with start > end is a no-op: add(1, 10) then remove(6, 4) -> [(1, 10)] (R6)
- after any mix of add and remove the representation invariant still holds: intervals() is the shortest ascending list of closed integer intervals whose union equals the members, with no overlapping or adjacent intervals, and contains() agrees
- from intervalset import IntervalSet works from the package root and IntervalSet exposes add, remove, contains, intervals

## Re-plans

## Planning notes (frontier author)
Spec is deliberately terse at the edge level: it pins the representation
(closed integer intervals, start>end = empty) and states the invariant
(shortest / minimum-count cover), but does NOT enumerate the merge/split
consequences. Applying the loopplan discipline — "each acceptance criterion
becomes a TDD test; a criterion an agent cannot turn into pass/fail is a
planning bug" — those consequences are derived from R7 into the concrete
criteria above (adjacency merge, multi-interval bridging, remove-splitting,
boundary trims, empty-range no-op). Panel lenses applied inline:
verifiability (every criterion is a concrete pass/fail example), adversarial
(1.1 before 1.2 since remove needs add; each task fits one fresh context;
phase is shippable after 1.1 as a read-only-plus-add set and complete after
1.2), scope/risk (matches spec, no gold-plating; pure in-memory logic with
no I/O or trust boundary → light is the honest tag). No blocking findings.
