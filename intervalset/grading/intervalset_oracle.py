"""Held-out acceptance oracle for `intervalset`. Authored independently from
the spec, BEFORE either arm was built. Neither arm (loopspace-B nor solo-A)
sees this file. Run with the target repo root on PYTHONPATH:

    PYTHONPATH=<repo> python3 -m pytest experiment/intervalset_oracle.py -q

Grades correctness of the public API (IntervalSet.add/remove/contains/
intervals) against the spec's representation invariant: intervals() must be
the SHORTEST list of closed integer intervals whose union equals exactly the
member set (so adjacent integer ranges MUST merge), sorted ascending; a
start>end range is the empty set.

The oracle embeds an independent brute-force reference (a plain set of ints)
to compute the expected canonical form, so the stress tests are not
hand-computed.
"""
import random
import pytest
from intervalset import IntervalSet


# ---------- independent brute-force reference ----------
def canonical(members):
    """Minimum closed-integer-interval cover of a set of ints (adjacency merged)."""
    if not members:
        return []
    xs = sorted(members)
    out = []
    start = prev = xs[0]
    for x in xs[1:]:
        if x == prev + 1:
            prev = x
        else:
            out.append((start, prev))
            start = prev = x
    out.append((start, prev))
    return out


def brute_apply(ops):
    """Apply (op, a, b) ops to a plain int set; start>end ranges are empty."""
    m = set()
    for op, a, b in ops:
        if a <= b:
            r = set(range(a, b + 1))
            if op == "add":
                m |= r
            else:
                m -= r
    return m


def build(ops):
    s = IntervalSet()
    for op, a, b in ops:
        getattr(s, op)(a, b)
    return s


def norm(intervals):
    """Coerce intervals() output to a list of (int, int) tuples for comparison."""
    return [tuple(iv) for iv in intervals]


# ---------- R1: empty ----------
def test_empty_intervals():
    assert norm(IntervalSet().intervals()) == []


def test_empty_contains():
    s = IntervalSet()
    for p in (-5, 0, 1, 100):
        assert s.contains(p) is False


# ---------- R2/R5: basic add ----------
def test_single_add():
    s = build([("add", 1, 3)])
    assert norm(s.intervals()) == [(1, 3)]


def test_single_point_add():
    s = build([("add", 5, 5)])
    assert norm(s.intervals()) == [(5, 5)]


def test_add_negative():
    s = build([("add", -3, -1)])
    assert norm(s.intervals()) == [(-3, -1)]
    assert s.contains(-2) is True


def test_add_spanning_zero():
    s = build([("add", -2, 2)])
    assert norm(s.intervals()) == [(-2, 2)]
    assert s.contains(0) is True


# ---------- R4: contains at boundaries ----------
def test_contains_boundaries():
    s = build([("add", 2, 5)])
    assert s.contains(1) is False
    assert s.contains(2) is True
    assert s.contains(5) is True
    assert s.contains(6) is False


# ---------- forced: overlap merge ----------
def test_overlap_merge():
    s = build([("add", 1, 5), ("add", 3, 8)])
    assert norm(s.intervals()) == [(1, 8)]


def test_contained_add_noop():
    s = build([("add", 1, 10), ("add", 3, 5)])
    assert norm(s.intervals()) == [(1, 10)]


def test_idempotent_add():
    s = build([("add", 1, 5), ("add", 1, 5)])
    assert norm(s.intervals()) == [(1, 5)]


# ---------- forced: ADJACENCY merge (the +1) ----------
def test_adjacent_merge():
    # [1,3] and [4,6] over integers cover {1..6} -> single interval [1,6]
    s = build([("add", 1, 3), ("add", 4, 6)])
    assert norm(s.intervals()) == [(1, 6)]


def test_adjacent_single_point_merge():
    s = build([("add", 1, 3), ("add", 4, 4)])
    assert norm(s.intervals()) == [(1, 4)]


def test_non_adjacent_stays_split():
    # gap at 4 -> two intervals
    s = build([("add", 1, 3), ("add", 5, 7)])
    assert norm(s.intervals()) == [(1, 3), (5, 7)]


# ---------- forced: multi-interval bridging ----------
def test_bridge_multiple():
    # {[1,3],[7,9]} then add [4,6]: 4 adj 3, 6 adj 7 -> one interval [1,9]
    s = build([("add", 1, 3), ("add", 7, 9), ("add", 4, 6)])
    assert norm(s.intervals()) == [(1, 9)]


def test_bridge_with_remaining_gaps():
    s = build([("add", 1, 3), ("add", 8, 10), ("add", 5, 6)])
    assert norm(s.intervals()) == [(1, 3), (5, 6), (8, 10)]


def test_out_of_order_adds_sorted():
    s = build([("add", 10, 12), ("add", 1, 2), ("add", 5, 6)])
    assert norm(s.intervals()) == [(1, 2), (5, 6), (10, 12)]


# ---------- R6: start > end is empty ----------
def test_add_empty_range_noop():
    s = build([("add", 5, 3)])
    assert norm(s.intervals()) == []


def test_add_empty_range_leaves_existing():
    s = build([("add", 1, 10), ("add", 8, 4)])
    assert norm(s.intervals()) == [(1, 10)]


def test_remove_empty_range_noop():
    s = build([("add", 1, 10), ("remove", 6, 4)])
    assert norm(s.intervals()) == [(1, 10)]


# ---------- R3: remove splitting / trimming ----------
def test_remove_splits():
    s = build([("add", 1, 10), ("remove", 4, 6)])
    assert norm(s.intervals()) == [(1, 3), (7, 10)]


def test_remove_low_boundary():
    s = build([("add", 1, 10), ("remove", 1, 3)])
    assert norm(s.intervals()) == [(4, 10)]


def test_remove_high_boundary():
    s = build([("add", 1, 10), ("remove", 8, 10)])
    assert norm(s.intervals()) == [(1, 7)]


def test_remove_entire():
    s = build([("add", 1, 10), ("remove", 1, 10)])
    assert norm(s.intervals()) == []


def test_remove_superset():
    s = build([("add", 3, 6), ("remove", 1, 10)])
    assert norm(s.intervals()) == []


def test_remove_middle_single():
    s = build([("add", 1, 5), ("remove", 3, 3)])
    assert norm(s.intervals()) == [(1, 2), (4, 5)]


def test_remove_across_multiple():
    # {[1,3],[6,8]} remove [2,7] -> removes 2,3,6,7 -> leaves {1},{8}
    s = build([("add", 1, 3), ("add", 6, 8), ("remove", 2, 7)])
    assert norm(s.intervals()) == [(1, 1), (8, 8)]


def test_remove_disjoint_noop():
    s = build([("add", 1, 3), ("remove", 5, 7)])
    assert norm(s.intervals()) == [(1, 3)]


def test_remove_from_empty():
    s = build([("remove", 1, 5)])
    assert norm(s.intervals()) == []


# ---------- readout invariants ----------
def test_intervals_are_tuples_of_ints():
    s = build([("add", 1, 3), ("add", 5, 7)])
    ivs = s.intervals()
    for iv in ivs:
        a, b = iv
        assert isinstance(a, int) and isinstance(b, int)
        assert a <= b


def test_no_adjacent_or_overlapping_in_output():
    s = build([("add", 1, 3), ("add", 4, 6), ("add", 8, 9), ("add", 10, 11)])
    ivs = norm(s.intervals())
    for (a, b), (c, d) in zip(ivs, ivs[1:]):
        assert c > b + 1  # strictly separated by a real gap


# ---------- big magnitude (no member enumeration required for correctness) ----------
def test_large_magnitude_contains():
    s = build([("add", 0, 10 ** 9)])
    assert s.contains(500_000_000) is True
    assert s.contains(10 ** 9) is True
    assert s.contains(10 ** 9 + 1) is False
    assert norm(s.intervals()) == [(0, 10 ** 9)]


# ---------- randomized stress vs brute-force reference ----------
@pytest.mark.parametrize("seed", range(25))
def test_random_sequence_matches_bruteforce(seed):
    rng = random.Random(seed)
    ops = []
    for _ in range(rng.randint(3, 15)):
        op = rng.choice(["add", "remove"])
        a = rng.randint(-8, 12)
        b = rng.randint(-8, 12)  # may be < a: exercises the empty-range rule
        ops.append((op, a, b))
    s = build(ops)
    expected = canonical(brute_apply(ops))
    assert norm(s.intervals()) == expected
    # contains agrees with membership over the working window
    members = brute_apply(ops)
    for p in range(-10, 15):
        assert s.contains(p) is (p in members)
