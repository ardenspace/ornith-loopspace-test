"""Sheet: the public gridcalc engine (SPEC.md R1-R12)."""

from . import evaluator as ev
from .parser import parse


def _validate_address(addr):
    if not isinstance(addr, str):
        raise ValueError(f"address must be a str, got {addr!r}")
    text = str(addr)
    if not ev.ADDR_RE.fullmatch(text):
        raise ValueError(f"invalid address: {addr!r}")
    return text


def _make_content(raw):
    if isinstance(raw, bool):
        raise ValueError(f"invalid cell value: {raw!r}")
    if isinstance(raw, int):
        return ("num", int(raw))
    if isinstance(raw, str):
        text = str(raw)
        if text.startswith("="):
            return ("formula", parse(text[1:]))
        return ("str", text)
    raise ValueError(f"invalid cell value: {raw!r}")


class Sheet:
    def __init__(self):
        self._cells = {}
        self._cache = {}
        self._deps = {}
        self._rdeps = {}
        self._in_progress = set()
        self._eval_count = 0

    @property
    def eval_count(self):
        return self._eval_count

    def set(self, addr, raw):
        a = _validate_address(addr)
        content = _make_content(raw)
        self._apply_set(a, content)
        return None

    def get(self, addr):
        a = _validate_address(addr)
        cell = self._cells.get(a)
        if cell is None:
            return None
        kind = cell[0]
        if kind == "num" or kind == "str":
            return cell[1]
        return self._compute(a)

    # -- internal: storage + dependency graph -----------------------------

    def _apply_set(self, addr, content):
        new_deps = ev.direct_deps(content[1]) if content[0] == "formula" else frozenset()

        self._invalidate_dependents(addr)

        old_deps = self._deps.get(addr, frozenset())
        for d in old_deps:
            bucket = self._rdeps.get(d)
            if bucket is not None:
                bucket.discard(addr)
        for d in new_deps:
            self._rdeps.setdefault(d, set()).add(addr)
        self._deps[addr] = new_deps

        self._cells[addr] = content
        self._cache.pop(addr, None)

    def _invalidate_dependents(self, addr):
        stack = [addr]
        seen = set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            self._cache.pop(cur, None)
            for dependent in self._rdeps.get(cur, ()):
                if dependent not in seen:
                    stack.append(dependent)

    # -- internal: lazy evaluation ------------------------------------

    def _compute(self, addr):
        if addr in self._cache:
            return self._cache[addr]
        if addr in self._in_progress:
            return "#CYCLE!"
        ast = self._cells[addr][1]
        self._in_progress.add(addr)
        self._eval_count += 1
        try:
            value = ev.evaluate(ast, self)
        finally:
            self._in_progress.discard(addr)
        self._cache[addr] = value
        return value

    # -- ctx interface consumed by gridcalc.evaluator.evaluate ------------

    def _ref_value(self, addr):
        if not ev.is_grid_address(addr):
            return "#REF!"
        cell = self._cells.get(addr)
        if cell is None:
            return 0
        kind = cell[0]
        if kind == "num":
            return cell[1]
        if kind == "str":
            return "#TYPE!"
        return self._compute(addr)

    def _range_values(self, tl, br, name):
        addrs = ev.range_addresses(tl, br)
        if addrs is None:
            return "#REF!"
        if name == "COUNT":
            return sum(1 for a in addrs if a in self._cells)

        values = []
        for a in addrs:
            cell = self._cells.get(a)
            if cell is None:
                continue
            kind = cell[0]
            if kind == "num":
                v = cell[1]
            elif kind == "str":
                v = "#TYPE!"
            else:
                v = self._compute(a)
            if isinstance(v, str):
                return v
            values.append(v)

        if name == "SUM":
            return sum(values)
        if name == "MIN":
            return min(values) if values else "#TYPE!"
        if name == "MAX":
            return max(values) if values else "#TYPE!"
        raise AssertionError(f"unknown function {name!r}")
