"""Tests for intervalset.IntervalSet covering R1–R7."""

import pytest
from intervalset import IntervalSet


# ------------------------------------------------------------------ helpers

def _member_set(iset: IntervalSet) -> set[int]:
    """Materialise the full integer member set from an IntervalSet."""
    members: set[int] = set()
    for s, e in iset.intervals():
        members.update(range(s, e + 1))
    return members


def _is_minimum_intervals(intervals: list[tuple[int, int]]) -> bool:
    """Check that the list is the minimum number of intervals:
    no two adjacent intervals can be merged (i.e. interval[i].end + 1 !=
    interval[i+1].start)."""
    for i in range(len(intervals) - 1):
        if intervals[i][1] + 1 == intervals[i + 1][0]:
            return False
    return True


def _is_sorted(intervals: list[tuple[int, int]]) -> bool:
    for i in range(len(intervals) - 1):
        if intervals[i][0] >= intervals[i + 1][0]:
            return False
    return True


def _invariant_holds(iset: IntervalSet) -> bool:
    """R7: intervals() is the shortest sorted list of closed intervals whose
    union equals the member set, and contains() agrees with those intervals."""
    ivs = iset.intervals()
    if not _is_sorted(ivs):
        return False
    if not _is_minimum_intervals(ivs):
        return False
    for t in ivs:
        if t[0] > t[1]:
            return False
    members = _member_set(iset)
    # Check contains() agrees with intervals for a sample of points
    for s, e in ivs:
        for p in range(s, e + 1):
            if not iset.contains(p):
                return False
    # Check no extra members outside intervals
    if members:
        lo = min(s for s, _ in ivs)
        hi = max(e for _, e in ivs)
        for p in range(lo - 1, hi + 2):
            if p in members and not iset.contains(p):
                return False
            if not p in members and iset.contains(p):
                return False
    return True


# ================================================================ R1: empty

class TestR1:
    def test_empty_construction(self):
        iset = IntervalSet()
        assert iset.intervals() == []

    def test_empty_contains_all_false(self):
        iset = IntervalSet()
        assert iset.contains(0) is False
        assert iset.contains(-100) is False
        assert iset.contains(999999) is False

    def test_empty_member_set(self):
        iset = IntervalSet()
        assert _member_set(iset) == set()


# ================================================================ R2: add

class TestR2:
    def test_add_single_point(self):
        iset = IntervalSet()
        iset.add(5, 5)
        assert iset.contains(5) is True
        assert iset.contains(4) is False
        assert iset.contains(6) is False
        assert iset.intervals() == [(5, 5)]

    def test_add_range(self):
        iset = IntervalSet()
        iset.add(2, 5)
        for i in range(2, 6):
            assert iset.contains(i) is True
        assert iset.contains(1) is False
        assert iset.contains(6) is False
        assert iset.intervals() == [(2, 5)]

    def test_add_overlapping_range_merges(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(5, 8)
        iset.add(3, 5)  # bridges the gap
        assert iset.intervals() == [(1, 8)]

    def test_add_adjacent_range_merges(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(4, 6)  # adjacent: 3+1 == 4
        assert iset.intervals() == [(1, 6)]

    def test_add_into_existing_interval(self):
        iset = IntervalSet()
        iset.add(1, 10)
        iset.add(3, 7)  # fully inside
        assert iset.intervals() == [(1, 10)]

    def test_add_extending_existing_interval(self):
        iset = IntervalSet()
        iset.add(3, 7)
        iset.add(1, 5)  # extends left
        assert iset.intervals() == [(1, 7)]

    def test_add_negative_values(self):
        iset = IntervalSet()
        iset.add(-10, -5)
        assert iset.intervals() == [(-10, -5)]
        assert iset.contains(-7) is True
        assert iset.contains(-11) is False

    def test_add_negative_and_positive(self):
        iset = IntervalSet()
        iset.add(-3, -1)
        iset.add(1, 3)
        assert iset.intervals() == [(-3, -1), (1, 3)]
        assert iset.contains(0) is False

    def test_add_multiple_disjoint_ranges(self):
        iset = IntervalSet()
        iset.add(1, 2)
        iset.add(5, 6)
        iset.add(10, 11)
        assert iset.intervals() == [(1, 2), (5, 6), (10, 11)]

    def test_add_duplicate_range_is_idempotent(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.add(1, 5)
        assert iset.intervals() == [(1, 5)]

    def test_add_large_range(self):
        iset = IntervalSet()
        iset.add(-1000000, 1000000)
        assert iset.contains(0) is True
        assert iset.contains(-1000000) is True
        assert iset.contains(1000000) is True
        assert iset.contains(-1000001) is False
        assert iset.contains(1000001) is False
        assert iset.intervals() == [(-1000000, 1000000)]


# ================================================================ R3: remove

class TestR3:
    def test_remove_from_empty(self):
        iset = IntervalSet()
        iset.remove(1, 5)
        assert iset.intervals() == []

    def test_remove_nonexistent_range(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.remove(10, 15)
        assert iset.intervals() == [(1, 5)]

    def test_remove_entire_interval(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.remove(1, 5)
        assert iset.intervals() == []

    def test_remove_partial_left(self):
        iset = IntervalSet()
        iset.add(1, 10)
        iset.remove(1, 3)
        assert iset.intervals() == [(4, 10)]

    def test_remove_partial_right(self):
        iset = IntervalSet()
        iset.add(1, 10)
        iset.remove(8, 10)
        assert iset.intervals() == [(1, 7)]

    def test_remove_from_middle_splits(self):
        iset = IntervalSet()
        iset.add(1, 10)
        iset.remove(4, 6)
        assert iset.intervals() == [(1, 3), (7, 10)]

    def test_remove_across_multiple_intervals(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(5, 7)
        iset.add(9, 11)
        iset.remove(2, 10)
        assert iset.intervals() == [(1, 1), (11, 11)]

    def test_remove_partial_from_first_only(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(5, 7)
        iset.remove(2, 4)
        assert iset.intervals() == [(1, 1), (5, 7)]

    def test_remove_partial_from_last_only(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(5, 7)
        iset.remove(6, 8)
        assert iset.intervals() == [(1, 3), (5, 5)]

    def test_remove_negative_range(self):
        iset = IntervalSet()
        iset.add(-5, 5)
        iset.remove(-3, 3)
        assert iset.intervals() == [(-5, -4), (4, 5)]

    def test_remove_multiple_times(self):
        iset = IntervalSet()
        iset.add(1, 20)
        iset.remove(3, 5)
        iset.remove(10, 12)
        assert iset.intervals() == [(1, 2), (6, 9), (13, 20)]

    def test_remove_all_then_add(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.remove(1, 5)
        iset.add(10, 15)
        assert iset.intervals() == [(10, 15)]


# ================================================================ R4: contains

class TestR4:
    def test_contains_boundary_points(self):
        iset = IntervalSet()
        iset.add(3, 7)
        assert iset.contains(3) is True
        assert iset.contains(7) is True
        assert iset.contains(2) is False
        assert iset.contains(8) is False

    def test_contains_single_point_interval(self):
        iset = IntervalSet()
        iset.add(42, 42)
        assert iset.contains(42) is True
        assert iset.contains(41) is False
        assert iset.contains(43) is False

    def test_contains_after_remove(self):
        iset = IntervalSet()
        iset.add(1, 10)
        iset.remove(5, 7)
        assert iset.contains(4) is True
        assert iset.contains(5) is False
        assert iset.contains(7) is False
        assert iset.contains(8) is True


# ================================================================ R5: intervals()

class TestR5:
    def test_returns_list_of_tuples(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(7, 9)
        ivs = iset.intervals()
        assert isinstance(ivs, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in ivs)

    def test_returns_sorted(self):
        iset = IntervalSet()
        iset.add(10, 12)
        iset.add(1, 3)
        iset.add(5, 7)
        ivs = iset.intervals()
        assert ivs == [(1, 3), (5, 7), (10, 12)]

    def test_returns_copy_not_reference(self):
        iset = IntervalSet()
        iset.add(1, 5)
        ivs1 = iset.intervals()
        ivs1.append((99, 99))
        assert len(iset.intervals()) == 1

    def test_empty_returns_empty_list(self):
        iset = IntervalSet()
        assert iset.intervals() == []


# ================================================================ R6: empty range

class TestR6:
    def test_add_empty_range_noop(self):
        iset = IntervalSet()
        iset.add(5, 3)
        assert iset.intervals() == []

    def test_add_empty_range_to_nonempty(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.add(5, 3)
        assert iset.intervals() == [(1, 5)]

    def test_remove_empty_range_noop(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.remove(5, 3)
        assert iset.intervals() == [(1, 5)]

    def test_intervals_never_has_start_gt_end(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.add(10, 3)  # empty, should be ignored
        iset.remove(3, 1)  # empty, should be ignored
        for s, e in iset.intervals():
            assert s <= e


# ================================================================ R7: invariant

class TestR7:
    def test_invariant_after_empty(self):
        iset = IntervalSet()
        assert _invariant_holds(iset)

    def test_invariant_after_single_add(self):
        iset = IntervalSet()
        iset.add(3, 7)
        assert _invariant_holds(iset)

    def test_invariant_after_multiple_adds(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(7, 9)
        iset.add(15, 20)
        assert _invariant_holds(iset)

    def test_invariant_after_merge(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(5, 7)
        iset.add(3, 5)  # merges all three
        assert _invariant_holds(iset)
        assert iset.intervals() == [(1, 7)]

    def test_invariant_after_remove_split(self):
        iset = IntervalSet()
        iset.add(1, 10)
        iset.remove(4, 6)
        assert _invariant_holds(iset)
        assert iset.intervals() == [(1, 3), (7, 10)]

    def test_invariant_after_remove_entire(self):
        iset = IntervalSet()
        iset.add(1, 10)
        iset.remove(3, 7)
        assert _invariant_holds(iset)
        assert iset.intervals() == [(1, 2), (8, 10)]

    def test_invariant_after_complex_sequence(self):
        iset = IntervalSet()
        iset.add(1, 5)
        iset.add(10, 15)
        iset.add(3, 12)   # merges into [1, 15]
        iset.remove(6, 8) # splits into [1, 5], [9, 15]
        iset.add(20, 25)
        assert _invariant_holds(iset)
        assert iset.intervals() == [(1, 5), (9, 15), (20, 25)]

    def test_invariant_after_remove_across_gaps(self):
        iset = IntervalSet()
        iset.add(1, 3)
        iset.add(7, 9)
        iset.add(13, 15)
        iset.remove(2, 14)  # eats middle of all three
        assert _invariant_holds(iset)
        assert iset.intervals() == [(1, 1), (15, 15)]

    def test_invariant_with_negative_values(self):
        iset = IntervalSet()
        iset.add(-10, -5)
        iset.add(-2, 2)
        iset.add(5, 10)
        iset.remove(-3, 3)
        assert _invariant_holds(iset)
        # (-10,-5) is untouched (end -5 < start -3); (-2,2) fully removed;
        # (5,10) untouched.
        assert iset.intervals() == [(-10, -5), (5, 10)]

    def test_contains_agrees_with_intervals(self):
        """For every integer in any interval, contains() must return True,
        and for integers between intervals, contains() must return False."""
        iset = IntervalSet()
        iset.add(-5, -3)
        iset.add(0, 2)
        iset.add(7, 10)
        ivs = iset.intervals()
        # Points inside intervals
        for s, e in ivs:
            for p in range(s, e + 1):
                assert iset.contains(p) is True, f"contains({p}) should be True"
        # Points between intervals (gap regions)
        for i in range(len(ivs) - 1):
            gap_start = ivs[i][1] + 1
            gap_end = ivs[i + 1][0] - 1
            for p in range(gap_start, gap_end + 1):
                assert iset.contains(p) is False, f"contains({p}) should be False"

    def test_minimum_intervals_no_adjacent_mergeable(self):
        """The stored intervals must not have any pair where end+1 == next start."""
        iset = IntervalSet()
        iset.add(1, 5)
        iset.add(6, 10)
        iset.add(11, 15)
        ivs = iset.intervals()
        assert _is_minimum_intervals(ivs)
        assert ivs == [(1, 15)]

    def test_invariant_random_sequence(self):
        """Stress-test the invariant with a long mixed sequence."""
        iset = IntervalSet()
        iset.add(1, 5)
        iset.add(10, 15)
        iset.add(20, 25)
        iset.add(3, 12)    # merge first two → [1,15], [20,25]
        iset.remove(2, 4)  # trim from [1,15] → [1,1], [5,15], [20,25]
        iset.add(22, 28)   # extend [20,25] → [20,28]
        iset.add(0, 0)     # adjacent to [1,1] → [0,1], [5,15], [20,28]
        iset.add(30, 35)   # new interval
        iset.add(7, 9)     # inside [5,15], no change
        iset.remove(18, 22)  # trim [20,28] → [23,28]
        assert _invariant_holds(iset)
        assert iset.intervals() == [(0, 1), (5, 15), (23, 28), (30, 35)]
