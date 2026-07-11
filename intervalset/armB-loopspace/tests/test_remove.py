from intervalset.interval_set import IntervalSet


class TestInteriorSplit:
    def test_interior_subrange_splits(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(4, 6)
        assert s.intervals() == [(1, 3), (7, 10)]

    def test_single_interior_integer_splits(self):
        s = IntervalSet()
        s.add(1, 5)
        s.remove(3, 3)
        assert s.intervals() == [(1, 2), (4, 5)]


class TestBoundaryTrim:
    def test_low_boundary_trim(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(1, 3)
        assert s.intervals() == [(4, 10)]

    def test_high_boundary_trim(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(8, 10)
        assert s.intervals() == [(1, 7)]


class TestFullRemoval:
    def test_remove_whole_interval(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(1, 10)
        assert s.intervals() == []

    def test_superset_removal(self):
        s = IntervalSet()
        s.add(3, 6)
        s.remove(1, 10)
        assert s.intervals() == []


class TestMultiIntervalRemoval:
    def test_removal_spanning_multiple_intervals(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(6, 8)
        s.remove(2, 7)
        assert s.intervals() == [(1, 1), (8, 8)]


class TestNoOpRemoval:
    def test_remove_nonexistent_integers(self):
        s = IntervalSet()
        s.add(1, 3)
        s.remove(5, 7)
        assert s.intervals() == [(1, 3)]

    def test_remove_from_empty_set(self):
        s = IntervalSet()
        s.remove(1, 5)
        assert s.intervals() == []

    def test_start_gt_end_is_noop(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(6, 4)
        assert s.intervals() == [(1, 10)]


class TestInvariant:
    def test_contains_agrees_after_remove(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(4, 6)
        for i in range(0, 12):
            assert s.contains(i) == (1 <= i <= 3 or 7 <= i <= 10)

    def test_no_adjacent_intervals_after_remove(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(6, 8)
        s.remove(4, 5)
        intervals = s.intervals()
        for i in range(len(intervals) - 1):
            assert intervals[i][1] + 1 < intervals[i + 1][0]

    def test_remove_partial_overlap_left(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(3, 5)
        assert s.intervals() == [(1, 2), (6, 10)]

    def test_remove_partial_overlap_right(self):
        s = IntervalSet()
        s.add(1, 10)
        s.remove(7, 9)
        assert s.intervals() == [(1, 6), (10, 10)]

    def test_remove_negative_range(self):
        s = IntervalSet()
        s.add(-5, 5)
        s.remove(-2, 2)
        assert s.intervals() == [(-5, -3), (3, 5)]

    def test_remove_single_point_from_single_point(self):
        s = IntervalSet()
        s.add(5, 5)
        s.remove(5, 5)
        assert s.intervals() == []

    def test_remove_adjacent_intervals(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(4, 6)
        s.remove(2, 5)
        assert s.intervals() == [(1, 1), (6, 6)]
