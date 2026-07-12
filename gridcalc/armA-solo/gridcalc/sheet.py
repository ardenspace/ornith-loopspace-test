"""Sheet: in-memory spreadsheet engine for gridcalc."""

from __future__ import annotations

import re

from gridcalc.parser import parse, PARSE_ERROR, extract_deps
from gridcalc.evaluator import evaluate

# ── address validation (R1) ──────────────────────────────────────────


def _validate_addr(addr) -> str | None:
    """Validate address. Returns the normalized string or None if invalid."""
    if not isinstance(addr, str):
        raise ValueError(f"Address must be a string, got {type(addr).__name__}")
    if not addr:
        raise ValueError("Empty address")
    m = re.match(r"^([A-Z])([0-9]+)$", addr)
    if not m:
        raise ValueError(f"Invalid address: {addr!r}")
    col, row_str = m.group(1), m.group(2)
    if len(row_str) > 2:
        raise ValueError(f"Row out of range: {addr!r}")
    if len(row_str) == 2 and row_str[0] == "0":
        raise ValueError(f"Leading zero in row: {addr!r}")
    row = int(row_str)
    if row < 1 or row > 99:
        raise ValueError(f"Row out of range: {addr!r}")
    return addr


# ── cell storage ─────────────────────────────────────────────────────

class _Cell:
    """Internal cell storage."""
    __slots__ = ("_value", "_is_formula", "_ast", "_cached", "_has_cache")

    def __init__(self, value, is_formula: bool, ast=None):
        self._value = value
        self._is_formula = is_formula
        self._ast = ast
        self._cached = None
        self._has_cache = False


# ── Sheet ────────────────────────────────────────────────────────────

class Sheet:
    """In-memory spreadsheet engine.

    Public API: set(addr, raw), get(addr), eval_count.
    """

    def __init__(self):
        self._cells: dict[str, _Cell] = {}
        self._eval_count: int = 0
        # dependency graph: cell_addr -> set of cell addresses it depends on
        self._deps: dict[str, set[str]] = {}
        # reverse mapping: cell_addr -> set of cells that depend on it
        self._dependents: dict[str, set[str]] = {}

    @property
    def eval_count(self) -> int:
        return self._eval_count

    def _update_deps(self, addr: str, new_deps: set[str]):
        """Update dependency graph for a cell."""
        # Remove old dependencies
        old_deps = self._deps.get(addr, set())
        for old_dep in old_deps:
            if old_dep in self._dependents:
                self._dependents[old_dep].discard(addr)

        # Add new dependencies
        self._deps[addr] = new_deps
        for dep in new_deps:
            if dep not in self._dependents:
                self._dependents[dep] = set()
            self._dependents[dep].add(addr)

    def _invalidate_transitive(self, addr: str):
        """Invalidate all cells that depend on addr (transitively)."""
        to_invalidate = {addr}
        queue = [addr]
        while queue:
            current = queue.pop(0)
            for dependent in self._dependents.get(current, set()):
                cell = self._cells.get(dependent)
                if cell and cell._has_cache:
                    cell._has_cache = False
                    to_invalidate.add(dependent)
                    queue.append(dependent)

    def set(self, addr, raw) -> None:
        """Store a value or formula at the given address."""
        # Validate address first (leaves state unchanged on error)
        canonical = _validate_addr(addr)

        # Validate raw type
        if isinstance(raw, bool):
            raise ValueError("bool is not a valid raw type")
        if isinstance(raw, int):
            normalized = int(raw)
        elif isinstance(raw, str):
            normalized = str(raw)
        else:
            raise ValueError(f"Invalid raw type: {type(raw).__name__}")

        if isinstance(normalized, str) and normalized.startswith("="):
            # formula
            ast = parse(normalized)
            cell = _Cell(normalized, is_formula=True, ast=ast)
            # extract dependencies
            new_deps = extract_deps(ast)
            self._update_deps(canonical, new_deps)
        else:
            cell = _Cell(normalized, is_formula=False)
            # literal cell has no dependencies
            self._deps.pop(canonical, None)

        self._cells[canonical] = cell

        # Invalidate all cells that depend on this cell (transitively)
        self._invalidate_transitive(canonical)

    def get(self, addr):
        """Retrieve the value at the given address."""
        # Validate address first (leaves state unchanged on error)
        canonical = _validate_addr(addr)

        cell = self._cells.get(canonical)
        if cell is None:
            return None

        if not cell._is_formula:
            return cell._value

        # formula cell — evaluate
        if cell._has_cache:
            return cell._cached

        # evaluate — count this cell's computation
        count_ref = [1]  # start with 1 for this cell
        result = evaluate(cell._ast, self, count_ref)
        self._eval_count += count_ref[0]
        cell._cached = result
        cell._has_cache = True
        return result
