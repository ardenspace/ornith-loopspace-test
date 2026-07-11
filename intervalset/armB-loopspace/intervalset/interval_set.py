class IntervalSet:
    def __init__(self):
        self._intervals = []

    def add(self, start, end):
        if start > end:
            return

        new_start, new_end = start, end

        merged = []
        skipped = []

        for s, e in self._intervals:
            if e + 1 < new_start:
                skipped.append((s, e))
            elif new_end + 1 < s:
                merged.append((s, e))
            else:
                new_start = min(new_start, s)
                new_end = max(new_end, e)

        new_interval = (new_start, new_end)

        result = []
        i = 0
        j = 0
        while i < len(skipped) and j < len(merged):
            if skipped[i] <= merged[j]:
                result.append(skipped[i])
                i += 1
            else:
                result.append(merged[j])
                j += 1
        while i < len(skipped):
            result.append(skipped[i])
            i += 1
        while j < len(merged):
            result.append(merged[j])
            j += 1

        inserted = False
        for k, (s, e) in enumerate(result):
            if new_start <= e + 1:
                result.insert(k, new_interval)
                inserted = True
                break
        if not inserted:
            result.append(new_interval)

        self._intervals = result

    def remove(self, start, end):
        if start > end:
            return

        result = []
        for s, e in self._intervals:
            if e < start or s > end:
                result.append((s, e))
            elif s >= start and e <= end:
                pass
            elif s < start and e <= end:
                result.append((s, start - 1))
            elif s >= start and e > end:
                result.append((end + 1, e))
            else:
                result.append((s, start - 1))
                result.append((end + 1, e))

        self._intervals = result

    def contains(self, point):
        for s, e in self._intervals:
            if s > point:
                return False
            if e >= point:
                return True
        return False

    def intervals(self):
        return list(self._intervals)
