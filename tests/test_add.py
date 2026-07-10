from intervalset.interval_set import IntervalSet


class TestEmpty:
    def test_empty_intervals(self):
        s = IntervalSet()
        assert s.intervals() == []

    def test_empty_contains(self):
        s = IntervalSet()
        assert s.contains(0) is False
        assert s.contains(100) is False
        assert s.contains(-50) is False


class TestSingleAdd:
    def test_add_range(self):
        s = IntervalSet()
        s.add(1, 3)
        assert s.intervals() == [(1, 3)]
        assert s.contains(1) is True
        assert s.contains(2) is True
        assert s.contains(3) is True
        assert s.contains(0) is False
        assert s.contains(4) is False

    def test_add_single_point(self):
        s = IntervalSet()
        s.add(5, 5)
        assert s.intervals() == [(5, 5)]
        assert s.contains(5) is True
        assert s.contains(4) is False
        assert s.contains(6) is False


class TestNegativesAndZero:
    def test_negative_range(self):
        s = IntervalSet()
        s.add(-3, -1)
        assert s.intervals() == [(-3, -1)]
        assert s.contains(-2) is True
        assert s.contains(-4) is False
        assert s.contains(0) is False

    def test_zero_spanning(self):
        s = IntervalSet()
        s.add(-2, 2)
        assert s.intervals() == [(-2, 2)]
        assert s.contains(0) is True
        assert s.contains(-3) is False
        assert s.contains(3) is False


class TestMerge:
    def test_overlapping_merges(self):
        s = IntervalSet()
        s.add(1, 5)
        s.add(3, 8)
        assert s.intervals() == [(1, 8)]

    def test_adjacent_merges(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(4, 6)
        assert s.intervals() == [(1, 6)]

    def test_adjacent_single_point(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(4, 4)
        assert s.intervals() == [(1, 4)]

    def test_gap_stays_separate(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(5, 7)
        assert s.intervals() == [(1, 3), (5, 7)]


class TestBridge:
    def test_bridge_collapse(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(7, 9)
        s.add(4, 6)
        assert s.intervals() == [(1, 9)]

    def test_bridge_partial(self):
        s = IntervalSet()
        s.add(1, 3)
        s.add(8, 10)
        s.add(5, 6)
        assert s.intervals() == [(1, 3), (5, 6), (8, 10)]


class TestContainedAndIdempotent:
    def test_fully_contained(self):
        s = IntervalSet()
        s.add(1, 10)
        s.add(3, 5)
        assert s.intervals() == [(1, 10)]

    def test_idempotent(self):
        s = IntervalSet()
        s.add(1, 5)
        s.add(1, 5)
        assert s.intervals() == [(1, 5)]


class TestInvalidRange:
    def test_start_gt_end_empty_set(self):
        s = IntervalSet()
        s.add(5, 3)
        assert s.intervals() == []

    def test_start_gt_end_after_add(self):
        s = IntervalSet()
        s.add(1, 10)
        s.add(8, 4)
        assert s.intervals() == [(1, 10)]


class TestSortedOutput:
    def test_sorted_intervals(self):
        s = IntervalSet()
        s.add(10, 12)
        s.add(1, 2)
        s.add(5, 6)
        assert s.intervals() == [(1, 2), (5, 6), (10, 12)]


class TestPurity:
    def test_intervals_is_pure_read(self):
        s = IntervalSet()
        s.add(1, 5)
        first = s.intervals()
        s.add(10, 12)
        second = s.intervals()
        assert first == [(1, 5)]
        assert second == [(1, 5), (10, 12)]

    def test_contains_is_pure_read(self):
        s = IntervalSet()
        s.add(1, 5)
        assert s.contains(3) is True
        s.add(10, 12)
        assert s.contains(3) is True
        assert s.contains(11) is True
