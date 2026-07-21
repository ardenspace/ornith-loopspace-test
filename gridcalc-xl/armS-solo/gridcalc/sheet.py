"""Sheet class for gridcalc.

A Sheet holds cells (empty / int / str-literal / formula-text), per-sheet
named ranges, an evaluation counter, and a result cache.
"""

from __future__ import annotations

import re
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

# ---------------------------------------------------------------------------
# Address validation (R1)
# ---------------------------------------------------------------------------

_ADDR_RE = re.compile(r"^[A-Z][1-9][0-9]?$")


def _check_addr(addr: object) -> str:
    """Validate an address argument to set/get.  Raises ValueError on
    invalid input.  Returns the validated address string."""
    if not isinstance(addr, str):
        raise ValueError(f"Address must be a str, got {type(addr).__name__}")
    if not _ADDR_RE.match(addr):
        raise ValueError(f"Invalid address: {addr!r}")
    return addr


def _check_addr_unqualified(addr: object) -> str:
    """Same as _check_addr but also rejects qualified forms like 'S1!A1'."""
    if not isinstance(addr, str):
        raise ValueError(f"Address must be a str, got {type(addr).__name__}")
    if "!" in addr:
        raise ValueError(f"Qualified address not allowed here: {addr!r}")
    if not _ADDR_RE.match(addr):
        raise ValueError(f"Invalid address: {addr!r}")
    return addr


# ---------------------------------------------------------------------------
# Copy-rewrite helpers (R17)
# ---------------------------------------------------------------------------


def _col_index(col: str) -> int:
    return ord(col) - ord("A")


def _index_col(i: int) -> str:
    return chr(ord("A") + i)


def _ref_shift(text: str, dcol: int, drow: int) -> str:
    """Shift a REF token text by (dcol, drow).  Returns the rewritten
    text, or '#REF!' if any component leaves the grid."""
    s = text
    abs_col = False
    abs_row = False

    if s.startswith("$"):
        abs_col = True
        s = s[1:]

    col = s[0]
    s = s[1:]

    if s.startswith("$"):
        abs_row = True
        s = s[1:]

    digits = s
    row = int(digits)

    if abs_col:
        new_col = col
    else:
        ci = _col_index(col) + dcol
        if ci < 0 or ci > 25:
            return "#REF!"
        new_col = _index_col(ci)

    if abs_row:
        new_row = row
    else:
        new_row = row + drow
        if new_row < 1 or new_row > 99:
            return "#REF!"

    prefix = "$" if abs_col else ""
    mid = "$" if abs_row else ""
    return f"{prefix}{new_col}{mid}{new_row}"


# Regex patterns for copy rewriting
_QUAL_REF_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)!(\$?[A-Z]\$?[0-9]+)")
_UNQUAL_REF_RE = re.compile(r"(\$?[A-Z]\$?[0-9]+)")


def _rewrite_formula(src_text: str, src_addr: str, dst_addr: str) -> str:
    """Rewrite a formula text by shifting REF tokens per R17.

    All characters outside REF tokens (operators, whitespace, STRING
    contents, NAME tokens, INTs, function names) are preserved exactly.
    """
    dcol = _col_index(dst_addr[0]) - _col_index(src_addr[0])
    drow = int(dst_addr[1:]) - int(src_addr[1:])

    result: list[str] = []
    i = 0
    n = len(src_text)

    while i < n:
        c = src_text[i]

        # String literal — preserve verbatim
        if c == '"':
            j = i + 1
            while j < n and src_text[j] != '"':
                j += 1
            if j >= n:
                result.append(src_text[i:])
                break
            result.append(src_text[i : j + 1])
            i = j + 1
            continue

        # #REF! token — preserve verbatim
        if src_text[i : i + 5] == "#REF!":
            result.append("#REF!")
            i += 5
            continue

        # Try to match a qualified REF or RANGE
        m = _QUAL_REF_RE.match(src_text, i)
        if m:
            qualifier = m.group(1)
            ref_text = m.group(2)
            ref_end = m.end()

            # Check if this is a range (followed by :)
            j = ref_end
            while j < n and src_text[j] in (" ", "\t"):
                j += 1

            if j < n and src_text[j] == ":":
                # It's a range — find the end ref
                j += 1  # skip :
                while j < n and src_text[j] in (" ", "\t"):
                    j += 1

                m2 = _UNQUAL_REF_RE.match(src_text, j)
                if m2:
                    ref2_text = m2.group(1)
                    range_end = m2.end()

                    # Rewrite both refs
                    rewritten1 = _ref_shift(ref_text, dcol, drow)
                    rewritten2 = _ref_shift(ref2_text, dcol, drow)

                    if rewritten1 == "#REF!" or rewritten2 == "#REF!":
                        # Replace entire range expression with #REF!
                        result.append("#REF!")
                    else:
                        # Preserve qualifier, rewrite refs, preserve whitespace around :
                        qual_part = src_text[i : i + len(qualifier) + 1]  # "SHEET!"
                        between = src_text[ref_end:j + 1]  # " : " (including :)
                        result.append(f"{qual_part}{rewritten1}{between}{rewritten2}")

                    i = range_end
                    continue

            # Not a range — just a qualified ref
            rewritten = _ref_shift(ref_text, dcol, drow)
            qual_part = src_text[i : i + len(qualifier) + 1]  # "SHEET!"
            if rewritten == "#REF!":
                result.append(f"{qual_part}#REF!")
            else:
                result.append(f"{qual_part}{rewritten}")
            i = ref_end
            continue

        # Try to match an unqualified REF
        m = _UNQUAL_REF_RE.match(src_text, i)
        if m:
            ref_text = m.group(1)
            ref_end = m.end()

            # Check if this is a range
            j = ref_end
            while j < n and src_text[j] in (" ", "\t"):
                j += 1

            if j < n and src_text[j] == ":":
                j += 1
                while j < n and src_text[j] in (" ", "\t"):
                    j += 1

                m2 = _UNQUAL_REF_RE.match(src_text, j)
                if m2:
                    ref2_text = m2.group(1)
                    range_end = m2.end()

                    rewritten1 = _ref_shift(ref_text, dcol, drow)
                    rewritten2 = _ref_shift(ref2_text, dcol, drow)

                    if rewritten1 == "#REF!" or rewritten2 == "#REF!":
                        result.append("#REF!")
                    else:
                        between = src_text[ref_end:j + 1]
                        result.append(f"{rewritten1}{between}{rewritten2}")
                    i = range_end
                    continue

            # Just a ref
            rewritten = _ref_shift(ref_text, dcol, drow)
            if rewritten == "#REF!":
                result.append("#REF!")
            else:
                result.append(rewritten)
            i = ref_end
            continue

        # Other character — preserve
        result.append(c)
        i += 1

    return "".join(result)


# ---------------------------------------------------------------------------
# Sheet
# ---------------------------------------------------------------------------


class Sheet:
    """In-memory spreadsheet sheet."""

    __slots__ = ("_wb", "_name", "_cells", "_names", "_eval_count", "_eval_cache")

    def __init__(self, wb, name: str) -> None:
        self._wb = wb
        self._name = name
        self._cells: dict[str, object] = {}
        self._names: dict[str, str] = {}
        self._eval_count: int = 0
        self._eval_cache: dict[str, tuple[int, object]] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def eval_count(self) -> int:
        """R21: eval_count property. Raises ValueError if sheet doesn't exist."""
        if self._name not in self._wb.sheets:
            raise ValueError(f"Sheet {self._name!r} no longer exists")
        return self._eval_count

    def get(self, addr: object) -> object:
        """R1/R2: get cell value (evaluate formula if needed)."""
        addr = _check_addr_unqualified(addr)
        content = self._cells.get(addr)
        if content is None:
            return None
        if isinstance(content, bool):
            return int(content)
        if isinstance(content, int):
            return content
        if isinstance(content, str):
            if content.startswith("="):
                # Evaluate formula
                from .evaluator import _Ctx, _eval_formula

                ctx = _Ctx(self._wb, self._name, self._wb.clock)
                return _eval_formula(content[1:], addr, self._wb, self._name, ctx)
            return content
        return content

    def set(self, addr: object, raw: object) -> None:
        """R2: store a value."""
        addr = _check_addr_unqualified(addr)

        if isinstance(raw, bool):
            raise ValueError("bool is not a valid raw value")
        if isinstance(raw, int):
            value: object = raw
        elif isinstance(raw, str):
            if raw.startswith("="):
                value = raw  # formula text (with leading =)
            else:
                value = raw  # string literal (including empty string)
        else:
            raise ValueError(f"Unsupported raw type: {type(raw).__name__}")

        # Capture old content for journaling
        old_content = self._cells.get(addr)

        self._cells[addr] = value
        # Invalidate cache for this cell
        if addr in self._eval_cache:
            del self._eval_cache[addr]

        # Invalidate caches for cells whose closure includes this cell
        self._wb._invalidate_caches_for_cell(self._name, addr)

        # Journal the operation
        from .workbook import _SetEntry
        entry = _SetEntry(self._name, addr, old_content, value)
        self._wb._journal.append(entry)
        self._wb._redo_stack.clear()

    def copy(self, src: object, dst: object) -> None:
        """R17: copy cell content from src to dst with reference rewriting."""
        # R23: accept qualified addresses
        src_parsed = self._parse_copy_addr(src)
        dst_parsed = self._parse_copy_addr(dst)

        src_sheet, src_addr = src_parsed
        dst_sheet, dst_addr = dst_parsed

        # Validate dst is on this sheet
        if dst_sheet != self._name:
            raise ValueError(f"Destination must be on this sheet: {dst!r}")

        # Get source content from the correct sheet
        src_sheet_obj = self._wb.sheets.get(src_sheet)
        if src_sheet_obj is None:
            raise ValueError(f"Source sheet does not exist: {src_sheet!r}")
        src_content = src_sheet_obj._cells.get(src_addr)
        if src_content is None:
            raise ValueError(f"Source cell {src_addr} is empty")

        if isinstance(src_content, bool):
            raise ValueError("Source cell contains bool")

        # Capture old content for journaling
        old_content = self._cells.get(dst_addr)

        if isinstance(src_content, int):
            # Literal int — copy as-is
            self._cells[dst_addr] = src_content
            if dst_addr in self._eval_cache:
                del self._eval_cache[dst_addr]
        elif isinstance(src_content, str):
            if not src_content.startswith("="):
                # String literal — copy as-is
                self._cells[dst_addr] = src_content
                if dst_addr in self._eval_cache:
                    del self._eval_cache[dst_addr]
            else:
                # Formula — rewrite references
                rewritten = _rewrite_formula(src_content[1:], src_addr, dst_addr)
                self._cells[dst_addr] = "=" + rewritten
                if dst_addr in self._eval_cache:
                    del self._eval_cache[dst_addr]

        # Journal the operation
        from .workbook import _CopyEntry
        entry = _CopyEntry(self._name, dst_addr, dst_sheet, old_content, src_sheet, src_addr, src_content)
        self._wb._journal.append(entry)
        self._wb._redo_stack.clear()

    def _parse_copy_addr(self, addr: object) -> tuple[str, str]:
        """Parse a copy address (may be qualified per R23)."""
        if not isinstance(addr, str):
            raise ValueError(f"Address must be a str, got {type(addr).__name__}")

        if "!" in addr:
            # Qualified address
            if " " in addr or "\t" in addr:
                raise ValueError(f"Whitespace in qualified address: {addr!r}")
            parts = addr.split("!", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid qualified address: {addr!r}")
            sheet_qual, addr_part = parts
            if not sheet_qual or len(sheet_qual) > 32:
                raise ValueError(f"Invalid sheet name in address: {sheet_qual!r}")
            if not sheet_qual[0].isalpha():
                raise ValueError(f"Invalid sheet name start: {sheet_qual!r}")
            if not all(c in _string_mod.ascii_letters + _string_mod.digits + "_" for c in sheet_qual):
                raise ValueError(f"Invalid sheet name chars: {sheet_qual!r}")
            # Validate the address part
            from .evaluator import _valid_addr
            if not _valid_addr(addr_part):
                raise ValueError(f"Invalid address in qualified address: {addr_part!r}")
            return (sheet_qual, addr_part)
        else:
            # Unqualified address - must be on this sheet
            from .evaluator import _valid_addr
            if not _valid_addr(addr):
                raise ValueError(f"Invalid address: {addr!r}")
            return (self._name, addr)

    def define_name(self, name: object, target: object) -> None:
        """R18: bind a named range."""
        if not isinstance(name, str):
            raise ValueError("Name must be a str")
        if not isinstance(target, str):
            raise ValueError("Target must be a str")

        # Validate name (R18)
        if len(name) < 2 or len(name) > 32:
            raise ValueError(f"Invalid name length: {name!r}")
        if not (name[0].isalpha() or name[0] == "_"):
            raise ValueError(f"Invalid name start: {name!r}")

        if not all(c in _string_mod.ascii_letters + _string_mod.digits + "_" for c in name):
            raise ValueError(f"Invalid name characters: {name!r}")
        if _valid_addr(name):
            raise ValueError(f"Name matches REF shape: {name!r}")
        _FUNC = {"SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW"}
        if name in _FUNC:
            raise ValueError(f"Name is a function name: {name!r}")

        # Validate target
        if "!" in target:
            # Qualified target (R23)
            if " " in target or "\t" in target:
                raise ValueError(f"Whitespace in qualified target: {target!r}")
            parts = target.split("!", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid qualified target: {target!r}")
            sheet_qual, addr_part = parts
            if not sheet_qual or len(sheet_qual) > 32:
                raise ValueError(f"Invalid sheet name in target: {sheet_qual!r}")
            if not sheet_qual[0].isalpha():
                raise ValueError(f"Invalid sheet name start: {sheet_qual!r}")
            if not all(c in _string_mod.ascii_letters + _string_mod.digits + "_" for c in sheet_qual):
                raise ValueError(f"Invalid sheet name chars: {sheet_qual!r}")
            # Check sheet exists
            if sheet_qual not in self._wb.sheets:
                raise ValueError(f"Sheet does not exist: {sheet_qual!r}")
            # Validate the address part
            if ":" in addr_part:
                range_parts = addr_part.split(":")
                if len(range_parts) != 2:
                    raise ValueError(f"Invalid range in target: {target!r}")
                for rp in range_parts:
                    if not _valid_addr(rp):
                        raise ValueError(f"Invalid address in target: {rp!r}")
            else:
                if not _valid_addr(addr_part):
                    raise ValueError(f"Invalid address in target: {addr_part!r}")
            self._names[name] = target
            return

        # Unqualified target
        if ":" in target:
            range_parts = target.split(":")
            if len(range_parts) != 2:
                raise ValueError(f"Invalid range: {target!r}")
            for rp in range_parts:
                if not _valid_addr(rp):
                    raise ValueError(f"Invalid address in range: {rp!r}")
        else:
            if not _valid_addr(target):
                raise ValueError(f"Invalid address: {target!r}")

        self._names[name] = target
