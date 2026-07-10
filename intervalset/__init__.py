"""intervalset — a mutable set of integers stored as a minimum set of closed intervals."""


class IntervalSet:
    """A mutable set of integers, represented as a sorted list of disjoint
    closed integer intervals [start, end] (both inclusive).

    Representation invariant: the stored intervals are the *minimum* number of
    closed integer intervals whose union equals the set of members — no more
    integers, no fewer, no redundant intervals.
    """

    def __init__(self):
        self._intervals: list[tuple[int, int]] = []

    # ------------------------------------------------------------------ public

    def add(self, start: int, end: int) -> None:
        """Add every integer in the closed range [start, end]."""
        if start > end:
            return
        new_start, new_end = start, end
        merged = []
        for s, e in self._intervals:
            if e < start - 1 or s > end + 1:
                merged.append((s, e))
            else:
                new_start = min(new_start, s)
                new_end = max(new_end, e)
        self._intervals = merged
        # Insert in sorted order
        inserted = False
        for i, (s, e) in enumerate(self._intervals):
            if new_start < s:
                self._intervals.insert(i, (new_start, new_end))
                inserted = True
                break
        if not inserted:
            self._intervals.append((new_start, new_end))

    def remove(self, start: int, end: int) -> None:
        """Remove every integer in the closed range [start, end]."""
        if start > end:
            return
        new_intervals: list[tuple[int, int]] = []
        for s, e in self._intervals:
            if e < start or s > end:
                # No overlap — keep as is
                new_intervals.append((s, e))
            elif s >= start and e <= end:
                # Fully covered — remove entirely
                pass
            elif s < start and e > end:
                # Removal is strictly inside — split into two
                new_intervals.append((s, start - 1))
                new_intervals.append((end + 1, e))
            elif s < start:
                # Left part overlaps — keep left piece
                new_intervals.append((s, start - 1))
            else:
                # Right part overlaps — keep right piece
                new_intervals.append((end + 1, e))
        self._intervals = new_intervals

    def contains(self, point: int) -> bool:
        """Return True iff *point* is a member of the set."""
        for s, e in self._intervals:
            if s <= point <= e:
                return True
            if s > point:
                return False
        return False

    def intervals(self) -> list[tuple[int, int]]:
        """Return the current members as a sorted list of (start, end) tuples."""
        return list(self._intervals)
