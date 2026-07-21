"""Workbook class for gridcalc.

Root of the public API.  Manages sheets, clock, journal (undo/redo),
and persistence (to_json / from_json).
"""

from __future__ import annotations

import json
import re as _re
import string as _string_mod

from .evaluator import (
    _Ctx,
    _ERR_NAME,
    _ERR_PARSE,
    _ERR_REF,
    _ERR_TYPE,
    _is_err,
    _valid_addr,
)
from .parser import parse as _parse
from .sheet import Sheet, _check_addr_unqualified, _rewrite_formula

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FUNC_NAMES = frozenset({"SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW"})

_SHEET_NAME_RE = _re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_ADDR_RE = _re.compile(r"^[A-Z][1-9][0-9]?$")


# ---------------------------------------------------------------------------
# Journal entry types
# ---------------------------------------------------------------------------


class _JournalEntry:
    __slots__ = ("op",)

    def __init__(self, op: str) -> None:
        self.op = op


class _SetEntry(_JournalEntry):
    __slots__ = ("sheet_name", "addr", "old_content", "new_content")

    def __init__(self, sheet_name: str, addr: str, old_content: object, new_content: object) -> None:
        super().__init__("set")
        self.sheet_name = sheet_name
        self.addr = addr
        self.old_content = old_content
        self.new_content = new_content


class _CopyEntry(_JournalEntry):
    __slots__ = ("sheet_name", "dst", "dst_sheet", "old_content", "src_sheet", "src_addr", "src_content")

    def __init__(self, sheet_name: str, dst: str, dst_sheet: str, old_content: object,
                 src_sheet: str, src_addr: str, src_content: object) -> None:
        super().__init__("copy")
        self.sheet_name = sheet_name
        self.dst = dst
        self.dst_sheet = dst_sheet
        self.old_content = old_content
        self.src_sheet = src_sheet
        self.src_addr = src_addr
        self.src_content = src_content


class _DefineNameEntry(_JournalEntry):
    __slots__ = ("sheet_name", "name", "old_binding")

    def __init__(self, sheet_name: str, name: str, old_binding: str | None) -> None:
        super().__init__("define_name")
        self.sheet_name = sheet_name
        self.name = name
        self.old_binding = old_binding


class _AddSheetEntry(_JournalEntry):
    __slots__ = ("sheet_name",)

    def __init__(self, sheet_name: str) -> None:
        super().__init__("add_sheet")
        self.sheet_name = sheet_name


class _AdvanceClockEntry(_JournalEntry):
    __slots__ = ("old_clock",)

    def __init__(self, old_clock: int) -> None:
        super().__init__("advance_clock")
        self.old_clock = old_clock


# ---------------------------------------------------------------------------
# Reference closure computation (R10)
# ---------------------------------------------------------------------------


def _collect_ref_texts(formula_text: str) -> list[str]:
    """Extract all REF token texts and RANGE token texts from a formula."""
    refs: list[str] = []
    i = 0
    n = len(formula_text)
    _qref_re = _re.compile(r"([A-Za-z][A-Za-z0-9_]*)!(\$?[A-Z]\$?[0-9]+)")
    _ref_re = _re.compile(r"(\$?[A-Z]\$?[0-9]+)")

    while i < n:
        c = formula_text[i]
        if c == '"':
            j = i + 1
            while j < n and formula_text[j] != '"':
                j += 1
            i = max(j + 1, i + 1)
            continue
        if formula_text[i : i + 5] == "#REF!":
            i += 5
            continue

        m = _qref_re.match(formula_text, i)
        if m:
            qualifier = m.group(1)
            ref_text = m.group(2)
            ref_end = m.end()
            j = ref_end
            while j < n and formula_text[j] in (" ", "\t"):
                j += 1
            if j < n and formula_text[j] == ":":
                j += 1
                while j < n and formula_text[j] in (" ", "\t"):
                    j += 1
                m2 = _ref_re.match(formula_text, j)
                if m2:
                    ref2_text = m2.group(1)
                    range_end = m2.end()
                    refs.append(f"{qualifier}!{ref_text}:{ref2_text}")
                    i = range_end
                    continue
            refs.append(f"{qualifier}!{ref_text}")
            i = ref_end
            continue

        m = _ref_re.match(formula_text, i)
        if m:
            ref_text = m.group(1)
            ref_end = m.end()
            j = ref_end
            while j < n and formula_text[j] in (" ", "\t"):
                j += 1
            if j < n and formula_text[j] == ":":
                j += 1
                while j < n and formula_text[j] in (" ", "\t"):
                    j += 1
                m2 = _ref_re.match(formula_text, j)
                if m2:
                    ref2_text = m2.group(1)
                    range_end = m2.end()
                    refs.append(f"{ref_text}:{ref2_text}")
                    i = range_end
                    continue
            refs.append(ref_text)
            i = ref_end
            continue

        i += 1

    return refs


def _parse_ref_token(text: str) -> tuple[str | None, str, int] | None:
    """Parse a REF token text into (qualifier, col, row)."""
    qualifier = None
    s = text
    m = _re.match(r"([A-Za-z][A-Za-z0-9_]*)!", s)
    if m:
        qualifier = m.group(1)
        s = s[m.end() :]
    if s.startswith("$"):
        s = s[1:]
    col = s[0] if s else ""
    s = s[1:]
    if s.startswith("$"):
        s = s[1:]
    if not col or col not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return None
    if not s or not s.isdigit():
        return None
    row = int(s)
    return (qualifier, col, row)


def _parse_range_token(text: str) -> tuple[str | None, str, int, str, int] | None:
    """Parse a RANGE token text into (qualifier, c1, r1, c2, r2)."""
    qualifier = None
    s = text
    m = _re.match(r"([A-Za-z][A-Za-z0-9_]*)!", s)
    if m:
        qualifier = m.group(1)
        s = s[m.end() :]

    def _parse_one(s: str) -> tuple[str, int, str] | None:
        if s.startswith("$"):
            s = s[1:]
        col = s[0] if s else ""
        s = s[1:]
        if s.startswith("$"):
            s = s[1:]
        digits = ""
        while s and s[0].isdigit():
            digits += s[0]
            s = s[1:]
        if not col or col not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" or not digits:
            return None
        return (col, int(digits), s)

    r1 = _parse_one(s)
    if r1 is None:
        return None
    col1, row1, s = r1
    if not s or s[0] != ":":
        return None
    s = s[1:]
    r2 = _parse_one(s)
    if r2 is None:
        return None
    col2, row2, _ = r2
    return (qualifier, col1, row1, col2, row2)


def _name_referenced(formula_text: str, name: str) -> bool:
    """Check if a formula text mentions a NAME token."""
    pattern = _re.compile(r"\b" + _re.escape(name) + r"\b")
    return bool(pattern.search(formula_text))


def _now_referenced(formula_text: str) -> bool:
    """Check if a formula text contains a NOW() call (syntactic, R27)."""
    return bool(_re.search(r"\bNOW\s*\(", formula_text))


def compute_reference_closure(wb, sheet_name: str, addr: str) -> set[tuple[str, str]]:
    """R10: compute the reference closure of a formula cell."""
    closure: set[tuple[str, str]] = set()
    queue: list[tuple[str, str]] = [(sheet_name, addr)]

    while queue:
        sn, a = queue.pop(0)
        if (sn, a) in closure:
            continue
        closure.add((sn, a))

        sheet = wb.sheets.get(sn)
        if sheet is None:
            continue

        content = sheet._cells.get(a)
        if content is None or not isinstance(content, str) or not content.startswith("="):
            continue

        formula_text = content[1:]
        ast = _parse(formula_text)
        if ast is None:
            continue

        ref_texts = _collect_ref_texts(formula_text)

        for rt in ref_texts:
            if ":" in rt:
                parsed = _parse_range_token(rt)
                if parsed is None:
                    continue
                qual, c1, r1, c2, r2 = parsed
                target_sheet = qual if qual is not None else sn
                if target_sheet not in wb.sheets:
                    continue
                for r in range(r1, r2 + 1):
                    for ci in range(ord(c1), ord(c2) + 1):
                        queue.append((target_sheet, f"{chr(ci)}{r}"))
            else:
                parsed = _parse_ref_token(rt)
                if parsed is None:
                    continue
                qual, col, row = parsed
                target_sheet = qual if qual is not None else sn
                if target_sheet not in wb.sheets:
                    continue
                queue.append((target_sheet, f"{col}{row}"))

        # Collect NAME references
        ident_pattern = _re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        for m in ident_pattern.finditer(formula_text):
            ident = m.group()
            if ident in _FUNC_NAMES:
                continue
            if _valid_addr(ident):
                continue
            if len(ident) >= 2 and len(ident) <= 32:
                if ident[0].isalpha() or ident[0] == "_":
                    if all(
                        c in _string_mod.ascii_uppercase + _string_mod.digits + "_"
                        for c in ident
                    ):
                        target_sheet_obj = wb.sheets.get(sn)
                        if target_sheet_obj is not None:
                            binding = target_sheet_obj._names.get(ident)
                            if binding is not None:
                                if ":" in binding:
                                    rp = _parse_range_token(binding)
                                    if rp is not None:
                                        _, rc1, rr1, rc2, rr2 = rp
                                        for r in range(rr1, rr2 + 1):
                                            for ci in range(ord(rc1), ord(rc2) + 1):
                                                queue.append((sn, f"{chr(ci)}{r}"))
                                else:
                                    if _valid_addr(binding):
                                        queue.append((sn, binding))

    return closure


def compute_touch_set(entry, wb) -> set[tuple[str, str]]:
    """R10: compute the touch set for a journal entry."""
    if entry.op == "set":
        return {(entry.sheet_name, entry.addr)}
    if entry.op == "copy":
        return {(entry.sheet_name, entry.dst)}
    if entry.op == "define_name":
        sheet = wb.sheets.get(entry.sheet_name)
        if sheet is None:
            return set()
        touched: set[tuple[str, str]] = set()
        for addr, content in sheet._cells.items():
            if isinstance(content, str) and content.startswith("="):
                if _name_referenced(content[1:], entry.name):
                    touched.add((entry.sheet_name, addr))
        return touched
    if entry.op == "add_sheet":
        touched: set[tuple[str, str]] = set()
        sheet_pattern = _re.compile(
            r"\b" + _re.escape(entry.sheet_name) + _re.escape("!")
        )
        for s_name, sheet in wb.sheets.items():
            for addr, content in sheet._cells.items():
                if isinstance(content, str) and content.startswith("="):
                    if sheet_pattern.search(content[1:]):
                        touched.add((s_name, addr))
        return touched
    if entry.op == "advance_clock":
        touched: set[tuple[str, str]] = set()
        for s_name, sheet in wb.sheets.items():
            for addr, content in sheet._cells.items():
                if isinstance(content, str) and content.startswith("="):
                    if _now_referenced(content[1:]):
                        touched.add((s_name, addr))
        return touched
    return set()


# ---------------------------------------------------------------------------
# Workbook
# ---------------------------------------------------------------------------


class Workbook:
    """In-memory multi-sheet spreadsheet engine (R21)."""

    def __init__(self) -> None:
        self.sheets: dict[str, Sheet] = {}
        self._sheet_order: list[str] = []
        self._clock: int = 0
        self._journal: list[_JournalEntry] = []
        self._redo_stack: list[_JournalEntry] = []
        self._name_eval_counts: dict[str, int] = {}

    # -- cache invalidation (R10) --------------------------------------------

    def _invalidate_caches_for_cell(self, sheet_name: str, addr: str) -> None:
        """Invalidate caches for all formula cells whose reference closure
        includes (sheet_name, addr)."""
        for s_name, sheet in self.sheets.items():
            for cell_addr, content in sheet._cells.items():
                if isinstance(content, str) and content.startswith("="):
                    closure = compute_reference_closure(self, s_name, cell_addr)
                    if (sheet_name, addr) in closure:
                        if cell_addr in sheet._eval_cache:
                            del sheet._eval_cache[cell_addr]

    # -- sheet management ----------------------------------------------------

    def _add_sheet_unlocked(self, name: str) -> Sheet:
        """Internal: create a sheet without journaling (for from_json)."""
        sheet = Sheet(self, name)
        self.sheets[name] = sheet
        self._sheet_order.append(name)
        return sheet

    def add_sheet(self, name: object) -> Sheet:
        """R21: create a new sheet."""
        if not isinstance(name, str):
            raise ValueError("Sheet name must be a str")
        if not _SHEET_NAME_RE.match(name):
            raise ValueError(f"Invalid sheet name: {name!r}")
        if name in self.sheets:
            raise ValueError(f"Duplicate sheet name: {name!r}")

        sheet = self._add_sheet_unlocked(name)
        entry = _AddSheetEntry(name)
        self._journal.append(entry)
        self._redo_stack.clear()
        return sheet

    def sheet(self, name: object) -> Sheet:
        """R21: return the handle of an existing sheet."""
        if not isinstance(name, str):
            raise ValueError("Sheet name must be a str")
        if name not in self.sheets:
            raise ValueError(f"Unknown sheet: {name!r}")
        return self.sheets[name]

    @property
    def sheet_names(self) -> list[str]:
        """R21: list of current sheet names in creation order."""
        return list(self._sheet_order)

    # -- clock ---------------------------------------------------------------

    @property
    def clock(self) -> int:
        """R26: read-only clock property."""
        return self._clock

    def advance_clock(self) -> int:
        """R26: increment clock by 1, return new value, journal entry."""
        old = self._clock
        self._clock += 1
        entry = _AdvanceClockEntry(old)
        self._journal.append(entry)
        self._redo_stack.clear()
        return self._clock

    # -- undo / redo ---------------------------------------------------------

    def undo(self) -> bool:
        """R19: revert the most recent journal entry."""
        if not self._journal:
            return False
        entry = self._journal.pop()
        self._undo_entry(entry)
        self._redo_stack.append(entry)
        return True

    def redo(self) -> bool:
        """R19: re-apply the most recently undone entry."""
        if not self._redo_stack:
            return False
        entry = self._redo_stack.pop()
        self._redo_entry(entry)
        self._journal.append(entry)
        return True

    def _undo_entry(self, entry: _JournalEntry) -> None:
        if entry.op == "set":
            sheet = self.sheets.get(entry.sheet_name)
            if sheet is not None:
                sheet._cells[entry.addr] = entry.old_content
                if entry.addr in sheet._eval_cache:
                    del sheet._eval_cache[entry.addr]

        elif entry.op == "copy":
            sheet = self.sheets.get(entry.sheet_name)
            if sheet is not None:
                sheet._cells[entry.dst] = entry.old_content
                if entry.dst in sheet._eval_cache:
                    del sheet._eval_cache[entry.dst]

        elif entry.op == "define_name":
            sheet = self.sheets.get(entry.sheet_name)
            if sheet is not None:
                if entry.old_binding is None:
                    sheet._names.pop(entry.name, None)
                else:
                    sheet._names[entry.name] = entry.old_binding

        elif entry.op == "add_sheet":
            sheet = self.sheets.pop(entry.sheet_name, None)
            if sheet is not None:
                self._name_eval_counts[entry.sheet_name] = sheet._eval_count
                if entry.sheet_name in self._sheet_order:
                    self._sheet_order.remove(entry.sheet_name)

        elif entry.op == "advance_clock":
            self._clock = entry.old_clock

    def _redo_entry(self, entry: _JournalEntry) -> None:
        if entry.op == "set":
            sheet = self.sheets.get(entry.sheet_name)
            if sheet is not None:
                sheet._cells[entry.addr] = entry.new_content
                if entry.addr in sheet._eval_cache:
                    del sheet._eval_cache[entry.addr]

        elif entry.op == "copy":
            # Redo re-applies the copy operation
            src_sheet_obj = self.sheets.get(entry.src_sheet)
            if src_sheet_obj is None:
                return
            src_content = src_sheet_obj._cells.get(entry.src_addr)
            if src_content is None:
                return
            if isinstance(src_content, bool):
                return

            sheet = self.sheets.get(entry.sheet_name)
            if sheet is None:
                return

            # Capture old content for potential further undo
            old_content = sheet._cells.get(entry.dst)

            if isinstance(src_content, int):
                sheet._cells[entry.dst] = src_content
            elif isinstance(src_content, str):
                if not src_content.startswith("="):
                    sheet._cells[entry.dst] = src_content
                else:
                    rewritten = _rewrite_formula(src_content[1:], entry.src_addr, entry.dst)
                    sheet._cells[entry.dst] = "=" + rewritten
            else:
                return

            if entry.dst in sheet._eval_cache:
                del sheet._eval_cache[entry.dst]

        elif entry.op == "define_name":
            sheet = self.sheets.get(entry.sheet_name)
            if sheet is not None:
                if entry.old_binding is None:
                    sheet._names.pop(entry.name, None)
                else:
                    sheet._names[entry.name] = entry.old_binding

        elif entry.op == "add_sheet":
            if entry.sheet_name not in self.sheets:
                sheet = Sheet(self, entry.sheet_name)
                if entry.sheet_name in self._name_eval_counts:
                    sheet._eval_count = self._name_eval_counts.pop(entry.sheet_name)
                self.sheets[entry.sheet_name] = sheet
                self._sheet_order.append(entry.sheet_name)

        elif entry.op == "advance_clock":
            self._clock = entry.old_clock

    # -- persistence ---------------------------------------------------------

    def to_json(self) -> str:
        """R24: serialize workbook to JSON string."""
        data: dict = {"clock": self._clock, "sheets": {}}
        for s_name in self._sheet_order:
            sheet = self.sheets[s_name]
            cells: dict[str, object] = {}
            for addr, content in sheet._cells.items():
                if content is None:
                    continue
                if isinstance(content, bool):
                    cells[addr] = int(content)
                elif isinstance(content, int):
                    cells[addr] = content
                elif isinstance(content, str):
                    cells[addr] = content
            names: dict[str, str] = dict(sheet._names)
            data["sheets"][s_name] = {"cells": cells, "names": names}
        return json.dumps(data)

    @classmethod
    def from_json(cls, s: object) -> "Workbook":
        """R24: deserialize a workbook from a JSON string."""
        if not isinstance(s, str):
            raise ValueError("from_json requires a str argument")

        try:
            data = json.loads(s)
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")

        wb = cls()

        clock = data.get("clock")
        if not isinstance(clock, int) or isinstance(clock, bool):
            raise ValueError("clock must be an int")
        if clock < 0:
            raise ValueError("clock must be non-negative")
        wb._clock = clock

        sheets_data = data.get("sheets")
        if not isinstance(sheets_data, dict):
            raise ValueError("sheets must be an object")

        for s_name, s_data in sheets_data.items():
            if not isinstance(s_name, str):
                raise ValueError("Sheet name must be a str")
            if not _SHEET_NAME_RE.match(s_name):
                raise ValueError(f"Invalid sheet name: {s_name!r}")

            if not isinstance(s_data, dict):
                raise ValueError(f"Sheet data must be an object: {s_name!r}")

            sheet = wb._add_sheet_unlocked(s_name)

            cells_data = s_data.get("cells")
            if not isinstance(cells_data, dict):
                raise ValueError(f"cells must be an object: {s_name!r}")

            for addr, content in cells_data.items():
                if not _ADDR_RE.match(addr):
                    raise ValueError(f"Invalid address: {addr!r}")
                if content is None:
                    continue
                if isinstance(content, bool):
                    raise ValueError(f"bool not allowed in stored cells: {addr}")
                if isinstance(content, float):
                    raise ValueError(f"float not allowed in stored cells: {addr}")
                if isinstance(content, int):
                    sheet._cells[addr] = content
                elif isinstance(content, str):
                    sheet._cells[addr] = content
                else:
                    raise ValueError(
                        f"Unsupported cell type: {type(content).__name__} at {addr}"
                    )

            names_data = s_data.get("names")
            if names_data is not None:
                if not isinstance(names_data, dict):
                    raise ValueError(f"names must be an object: {s_name!r}")
                for name, target in names_data.items():
                    if not isinstance(name, str) or not isinstance(target, str):
                        raise ValueError(
                            f"Name/target must be str: {name!r} -> {target!r}"
                        )
                    sheet._names[name] = target

        return wb


# ---------------------------------------------------------------------------
# Public evaluate function (called by Sheet.get)
# ---------------------------------------------------------------------------


def evaluate(formula_text: str, wb, host: str, ctx: _Ctx, addr: str | None = None) -> object:
    """Public evaluate function: parse and evaluate a formula text.

    This is the entry point called by Sheet.get().
    """
    from .evaluator import _eval_formula

    return _eval_formula(formula_text, addr or "", wb, host, ctx)
