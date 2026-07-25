"""Workbook and Sheet implementation — R21 surface."""

import json
import re

from gridcalc.formula import (
    PARSE_ERROR, DIV_ERROR, TYPE_ERROR, REF_ERROR,
    _ErrorValue, _ERROR_SET, parse_formula,
    _is_valid_address as _formula_is_valid_address,
    _parse_address, _strip_abs_ref, _parse_formula_ast, _ast_contains_now,
    _check_formula_bounds,
    _MAX_REACHED_FORMULA_CELLS,
)

# String representations of error sentinels, for cache lookup.
_ERROR_SET_STRINGS = {err.code for err in _ERROR_SET}


class _CopyEmptySourceError(ValueError, NotImplementedError):
    pass


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _is_valid_sheet_name(name):
    """Return True iff *name* is a valid sheet name per R21.

    Rules:
      - must be str or str subclass
      - 1-32 characters
      - first character: ASCII letter (A-Z, a-z)
      - remaining characters: ASCII letters, digits, underscore
      - normalized to plain str on storage
    """
    if not isinstance(name, str):
        return False
    if not name:
        return False
    if len(name) > 32:
        return False
    first = name[0]
    if not first.isascii() or not first.isalpha():
        return False
    for ch in name[1:]:
        if not ch.isascii():
            return False
        if not (ch.isalpha() or ch.isdigit() or ch == "_"):
            return False
    return True


# Reserved function names that cannot be used as names.
_RESERVED_NAMES = frozenset({"SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW"})


def _is_valid_name(name):
    """Return True iff *name* is a valid per-sheet name per R18.

    Rules:
      - must be str or str subclass
      - 2-32 characters
      - first character: ASCII letter (A-Z, a-z) or underscore
      - remaining characters: ASCII letters, digits, underscore
      - not REF-shaped (e.g. 'A1', 'Z99')
      - not one of the reserved function names (case-insensitive)
    """
    if not isinstance(name, str):
        return False
    if len(name) < 2 or len(name) > 32:
        return False
    first = name[0]
    if not first.isascii():
        return False
    if not (('A' <= first <= 'Z') or first == "_"):
        return False
    for ch in name[1:]:
        if not ch.isascii():
            return False
        if not (('A' <= ch <= 'Z') or ch.isdigit() or ch == "_"):
            return False
    if re.fullmatch(r"[A-Z][0-9]+", name):
        return False
    # Check for reserved function names (case-insensitive).
    if name.upper() in _RESERVED_NAMES:
        return False
    return True


def _is_valid_target(target):
    """Return True iff *target* is a valid unqualified address or range per R18.

    Rules:
      - must be str or str subclass
      - either a single valid address (per R1) or a range of two valid addresses
      - range endpoints must be well-ordered (start <= end)
    """
    if not isinstance(target, str):
        return False
    if ":" in target:
        # Range: split into two endpoints.
        parts = target.split(":")
        if len(parts) != 2:
            return False
        start, end = parts
        if not _is_valid_unqualified_address(start) or not _is_valid_unqualified_address(end):
            return False
        # Check well-ordered.
        start_col, start_row = _parse_address(start)
        end_col, end_row = _parse_address(end)
        if start_col > end_col or start_row > end_row:
            return False
        return True
    else:
        # Single address.
        return _is_valid_unqualified_address(target)


def _parse_qualified_cell_arg(text, default_sheet, workbook):
    if not isinstance(text, str):
        raise ValueError("Cell argument must be str")
    text = str(text)
    if "!" not in text:
        if not _is_valid_address(text):
            raise ValueError(f"Invalid cell argument: {text!r}")
        return default_sheet, text
    if text.count("!") != 1:
        raise ValueError(f"Invalid qualified cell argument: {text!r}")
    sheet_name, addr = text.split("!")
    if not _is_valid_sheet_name(sheet_name) or not _is_valid_address(addr):
        raise ValueError(f"Invalid qualified cell argument: {text!r}")
    if sheet_name not in workbook._sheets:
        raise ValueError(f"Unknown sheet: {sheet_name!r}")
    return sheet_name, addr


def _is_valid_target_for_workbook(target, workbook):
    if not isinstance(target, str):
        return False
    target = str(target)
    if "!" not in target:
        return _is_valid_target(target)
    if target.count("!") != 1:
        return False
    sheet_name, rest = target.split("!")
    if not _is_valid_sheet_name(sheet_name) or sheet_name not in workbook._sheets:
        return False
    return _is_valid_target(rest)


def _split_name_target(target):
    sheet_name = None
    rest = target
    if "!" in target:
        sheet_name, rest = target.split("!", 1)
    if ":" in rest:
        ref1, ref2 = rest.split(":", 1)
        return sheet_name, ref1, ref2
    return sheet_name, rest, None


def _normalize_str(value):
    """Normalize a str/str-subclass argument to plain str."""
    if isinstance(value, str):
        return str(value)
    return value


def _is_valid_unqualified_address(addr):
    if not isinstance(addr, str):
        return False
    return bool(re.fullmatch(r"[A-Z]([1-9]|[1-9][0-9])", addr))


# ---------------------------------------------------------------------------
# Address validation (R1)
# ---------------------------------------------------------------------------

# Valid address pattern: exactly one uppercase A-Z followed by row 1-99
# with no leading zeros.
#   - one digit:        1-9
#   - two digits:       10-99 (first digit 1-9, second 0-9)
_ADDRESS_PATTERN = r"[A-Z]([1-9]|[1-9][0-9])"


def _is_valid_address(addr):
    """Return True iff *addr* is a valid cell address per R1.

    Rules:
      - must be str or str subclass
      - exactly one uppercase letter A-Z
      - followed by ASCII digits representing integer 1-99
      - no leading zeros (so 'A01' is invalid, 'A1' is valid)
      - no qualified forms (e.g. 'S1!A1')
      - no leading/trailing whitespace or newlines
    """
    if not isinstance(addr, str):
        return False
    return bool(re.fullmatch(r"[A-Z]([1-9]|[1-9][0-9])", addr))


def _parse_copy_ref(text, i):
    n = len(text)
    if text.startswith(REF_ERROR, i):
        return {
            "start": i, "end": i + len(REF_ERROR), "text": REF_ERROR,
            "ref_error": True,
        }
    j = i
    col_abs = False
    row_abs = False
    if j < n and text[j] == '$':
        col_abs = True
        j += 1
    if j >= n or not ('A' <= text[j] <= 'Z'):
        return None
    if j + 1 < n and 'A' <= text[j + 1] <= 'Z':
        return None
    col = text[j]
    j += 1
    if j < n and text[j] == '$':
        row_abs = True
        j += 1
    digit_start = j
    while j < n and '0' <= text[j] <= '9':
        j += 1
    if j == digit_start:
        return None
    if j < n and (text[j].isalnum() or text[j] == '_'):
        return None
    return {
        "start": i, "end": j, "text": text[i:j], "ref_error": False,
        "col_abs": col_abs, "row_abs": row_abs, "col": col,
        "row_text": text[digit_start:j], "prefix": "",
    }


def _parse_qualified_copy_ref(text, i):
    n = len(text)
    if i > 0 and (text[i - 1].isalnum() or text[i - 1] in ('_', '$')):
        return None
    j = i
    if j >= n or not text[j].isalpha() or not text[j].isascii():
        return None
    j += 1
    while j < n and (text[j].isalpha() or text[j].isdigit() or text[j] == '_') and text[j].isascii():
        j += 1
    bang = j
    while bang < n and text[bang] in (' ', '\t'):
        bang += 1
    if bang >= n or text[bang] != '!':
        return None
    ref_start = bang + 1
    while ref_start < n and text[ref_start] in (' ', '\t'):
        ref_start += 1
    ref = _parse_copy_ref(text, ref_start)
    if ref is None or ref["ref_error"]:
        return None
    ref = dict(ref)
    ref["start"] = i
    ref["end"] = ref["end"]
    ref["text"] = text[i:ref["end"]]
    ref["bare_text"] = text[ref_start:ref["end"]]
    ref["prefix"] = text[i:ref_start]
    return ref


def _copy_ref_tokens(text):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 1
            i += 1
            continue
        qref = _parse_qualified_copy_ref(text, i)
        if qref is not None:
            tokens.append(qref)
            i = qref["end"]
            continue
        if ch == '#' or ch == '$' or ('A' <= ch <= 'Z'):
            prev = text[i - 1] if i > 0 else ''
            if prev and (prev.isalnum() or prev in ('_', '$')):
                i += 1
                continue
            ref = _parse_copy_ref(text, i)
            if ref is not None:
                tokens.append(ref)
                i = ref["end"]
                continue
        i += 1
    return tokens


def _shift_copy_ref(ref, delta_col, delta_row):
    if ref["ref_error"]:
        return REF_ERROR, False
    unmarked = _strip_abs_ref(ref.get("bare_text", ref["text"]))
    if not _formula_is_valid_address(unmarked):
        return ref["text"], False
    col_ord = ord(ref["col"])
    row = int(ref["row_text"])
    if not ref["col_abs"]:
        col_ord += delta_col
    if not ref["row_abs"]:
        row += delta_row
    if col_ord < ord('A') or col_ord > ord('Z') or row < 1 or row > 99:
        return REF_ERROR, True
    col_part = ("$" if ref["col_abs"] else "") + chr(col_ord)
    row_part = ("$" if ref["row_abs"] else "") + str(row)
    return ref.get("prefix", "") + col_part + row_part, False


def _rewrite_formula_for_copy(text, delta_col, delta_row):
    tokens = _copy_ref_tokens(text)
    pieces = []
    pos = 0
    i = 0
    while i < len(tokens):
        first = tokens[i]
        if i + 1 < len(tokens):
            second = tokens[i + 1]
            between = text[first["end"]:second["start"]]
            stripped = between.strip(' \t')
            if stripped == ':' and len(stripped) == len(between.replace(' ', '').replace('\t', '')):
                first_text, first_left = _shift_copy_ref(first, delta_col, delta_row)
                second_text, second_left = _shift_copy_ref(second, delta_col, delta_row)
                pieces.append(text[pos:first["start"]])
                if first_left or second_left:
                    pieces.append(REF_ERROR)
                else:
                    pieces.append(first_text)
                    pieces.append(between)
                    pieces.append(second_text)
                pos = second["end"]
                i += 2
                continue
        shifted, left_grid = _shift_copy_ref(first, delta_col, delta_row)
        pieces.append(text[pos:first["start"]])
        pieces.append(REF_ERROR if left_grid else shifted)
        pos = first["end"]
        i += 1
    pieces.append(text[pos:])
    return ''.join(pieces)


# ---------------------------------------------------------------------------
# Sheet handle
# ---------------------------------------------------------------------------

class _SheetState:
    __slots__ = ("cells", "cache", "names", "eval_count", "reverse_deps",
                 "identity_closure_cache", "handle")

    def __init__(self):
        self.cells = {}
        self.cache = {}
        self.names = {}
        self.eval_count = 0
        self.reverse_deps = {}
        self.identity_closure_cache = {}
        self.handle = None


class _SheetHandle:
    """Internal sheet handle. Public surface: set, get, copy, define_name,
    eval_count. All other methods/attrs are private (underscore-prefixed)."""

    __slots__ = ("_name", "_workbook", "_state")

    def __init__(self, name, workbook, state):
        self._name = name
        self._workbook = workbook
        self._state = state

    def _current_state(self):
        self._check_sheet_exists()
        return self._workbook._sheets[self._name]

    @property
    def _cells(self):
        return self._current_state().cells

    @property
    def _cache(self):
        return self._current_state().cache

    @property
    def _names(self):
        return self._current_state().names

    @property
    def _eval_count(self):
        return self._current_state().eval_count

    @_eval_count.setter
    def _eval_count(self, value):
        self._current_state().eval_count = value

    @property
    def _reverse_deps(self):
        return self._current_state().reverse_deps

    @property
    def _closure_cache(self):
        return {
            addr: {
                target_addr for target_sheet, target_addr in closure
                if target_sheet == self._name and target_addr != addr
            }
            for addr, closure in self._identity_closure_cache.items()
        }

    @property
    def _identity_closure_cache(self):
        return self._current_state().identity_closure_cache

    def _check_sheet_exists(self):
        """Raise ValueError if the sheet this handle refers to no longer exists."""
        if self._name not in self._workbook._sheets:
            raise ValueError(
                f"Sheet {self._name!r} no longer exists"
            )



    @property
    def eval_count(self):
        self._check_sheet_exists()
        return self._eval_count

    def _replace_cell(self, addr, value):
        self._remove_reverse_deps_for(addr)
        if value is None:
            self._cells.pop(addr, None)
            self._invalidate_dependents(addr)
        else:
            self._cells[addr] = value
            self._invalidate_dependents(addr, value)

    def set(self, addr, raw):
        """Store a literal value at *addr*.

        Accepts:
          - plain int (stored as int)
          - int subclasses except bool (normalized to plain int)
          - plain str (stored as str)
          - str subclasses (normalized to plain str)

        Rejects:
          - bool (despite being int subclass)
          - invalid addresses
          - other types

        Returns None on success. Raises ValueError on failure, leaving
        observable state unchanged.
        """
        # Normalize address to plain str.
        if not isinstance(addr, str):
            raise ValueError(f"Address must be str, got {type(addr).__name__}")
        addr = str(addr)

        # Validate address first.
        if not _is_valid_address(addr):
            raise ValueError(f"Invalid address: {addr!r}")

        # Check that the sheet still exists.
        self._check_sheet_exists()

        # Validate and normalize raw value.
        # Check bool first because bool is a subclass of int.
        if isinstance(raw, bool):
            raise ValueError(
                f"bool values are not accepted; got {type(raw).__name__}"
            )

        if isinstance(raw, int):
            # Accepted int subclass (not bool); normalize to plain int.
            normalized = int(raw)
        elif isinstance(raw, str):
            # Accepted str/str-subclass; normalize to plain str.
            normalized = str(raw)
        else:
            raise ValueError(
                f"Unsupported raw type: {type(raw).__name__}"
            )

        # Store the value and invalidate affected cached results.
        # Per R10: only invalidate formula cells whose closure includes *addr*.
        # Capture old value for journaling (None if never set).
        old_value = self._cells.get(addr)
        self._cells[addr] = normalized

        # Journal the successful set operation.
        self._workbook._journal.append(
            ("set", self._name, addr, old_value, normalized)
        )
        # New journaled op clears redo stack.
        self._workbook._redo_stack.clear()

        # If this cell was previously a formula, remove its old reverse deps.
        self._remove_reverse_deps_for(addr)

        # Invalidate cached results for all formula cells that depend on *addr*.
        self._invalidate_dependents(addr, normalized)

        return None

    def get(self, addr):
        """Retrieve the value at *addr*.

        Returns:
          - None if the cell has never been set
          - The stored int for literal int cells
          - The stored str for literal str cells (unchanged)
          - The evaluated int or error sentinel for formula cells
            (str values whose first character is '=')

        Raises ValueError if *addr* is not a valid address, leaving all
        observable state unchanged.
        """
        # Normalize address to plain str.
        if not isinstance(addr, str):
            raise ValueError(f"Address must be str, got {type(addr).__name__}")
        addr = str(addr)

        # Validate address first.
        if not _is_valid_address(addr):
            raise ValueError(f"Invalid address: {addr!r}")

        # Check that the sheet still exists.
        self._check_sheet_exists()

        result = self._workbook._evaluate_cell(self._name, addr, set(), [0])
        if result[0] == "error":
            return result[1]
        return result[1]

    def copy(self, src, dst):
        # Normalize addresses to plain str.
        if not isinstance(src, str):
            raise ValueError(f"Source address must be str, got {type(src).__name__}")
        if not isinstance(dst, str):
            raise ValueError(f"Destination address must be str, got {type(dst).__name__}")
        src = str(src)
        dst = str(dst)

        self._check_sheet_exists()
        src_sheet_name, src_addr = _parse_qualified_cell_arg(src, self._name, self._workbook)
        dst_sheet_name, dst_addr = _parse_qualified_cell_arg(dst, self._name, self._workbook)
        src_state = self._workbook._sheets[src_sheet_name]
        dst_state = self._workbook._sheets[dst_sheet_name]
        if src_addr not in src_state.cells:
            raise _CopyEmptySourceError(f"Cannot copy empty source cell: {src!r}")

        old_value = dst_state.cells.get(dst_addr)
        src_value = src_state.cells[src_addr]
        if isinstance(src_value, str) and src_value.startswith("="):
            formula_text = src_value[1:]
            if _parse_formula_ast(formula_text) is not None:
                src_col, src_row = _parse_address(src_addr)
                dst_col, dst_row = _parse_address(dst_addr)
                delta_col = ord(dst_col) - ord(src_col)
                delta_row = dst_row - src_row
                new_value = "=" + _rewrite_formula_for_copy(
                    formula_text, delta_col, delta_row
                )
            else:
                new_value = src_value
        else:
            new_value = src_value

        dst_state.cells[dst_addr] = new_value
        self._workbook._journal.append(
            ("copy", dst_sheet_name, dst_addr, old_value, new_value)
        )
        self._workbook._redo_stack.clear()

        dst_state.handle._remove_reverse_deps_for(dst_addr)
        self._workbook._invalidate_identity(dst_sheet_name, dst_addr)
        return None

    def define_name(self, name, target):
        """Bind a per-sheet name to a target address or range per R18.

        Returns None on success. Raises ValueError on invalid name, target,
        or non-string arguments, leaving all observable state unchanged.
        Successful definition journals the operation and invalidates formula
        cells that mention the name (even on redefinition to the same target).
        """
        # Normalize name and target to plain str.
        if not isinstance(name, str):
            raise ValueError(f"Name must be str, got {type(name).__name__}")
        if not isinstance(target, str):
            raise ValueError(f"Target must be str, got {type(target).__name__}")
        name = str(name)
        target = str(target)

        self._check_sheet_exists()

        # Validate name.
        if not _is_valid_name(name):
            raise ValueError(f"Invalid name: {name!r}")

        # Validate target.
        if not _is_valid_target_for_workbook(target, self._workbook):
            raise ValueError(f"Invalid target: {target!r}")

        # Capture old binding for journaling (None if undefined).
        old_binding = self._names.get(name)

        # Store the new binding.
        self._names[name] = target

        # Journal the successful define_name operation.
        self._workbook._journal.append(
            ("define_name", self._name, name, old_binding, target)
        )
        # New journaled op clears redo stack.
        self._workbook._redo_stack.clear()

        # Invalidate formula cells that mention this name on this sheet.
        self._invalidate_names_dependents(name)

        return None

    def _invalidate_names_dependents(self, name):
        """Invalidate cached results for all formula cells that mention *name*.

        Walks all formula cells on this sheet and checks if their parsed AST
        contains a NAME token matching *name*. If so, invalidates the cache.
        """
        # Collect all formula cell addresses on this sheet.
        formula_cells = [
            addr for addr, value in self._cells.items()
            if isinstance(value, str) and value.startswith("=")
        ]

        for addr in formula_cells:
            formula_text = self._cells[addr][1:]  # Strip leading '='
            if self._formula_mentions_name(formula_text, name):
                self._cache.pop(addr, None)
                self._invalidate_dependents(addr)

    def _formula_mentions_name(self, formula_text, name):
        """Check if a formula text mentions a specific name.

        Parses the formula and checks if any NAME token matches *name*.
        """
        from gridcalc.formula import _tokenize, _parse_expr

        tokens = _tokenize(formula_text)
        if tokens is None:
            return False

        # Walk tokens to find NAME tokens.
        for tok_type, tok_val in tokens:
            if tok_type == "NAME" and tok_val == name:
                return True

        return False

    def _invalidate_dependents(self, addr, new_value=None):
        """Invalidate cached results for all formula cells that depend on *addr*.

        Also invalidates the cell itself; edits can replace a cached formula
        with a literal or empty value.
        """
        self._workbook._invalidate_identity(self._name, addr)

    def _remove_reverse_deps_for(self, addr):
        identity = (self._name, addr)
        old_closure = self._identity_closure_cache.pop(addr, set())
        for sheet_state in self._workbook._sheets.values():
            for cell_in_closure in old_closure:
                dependents = sheet_state.reverse_deps.get(cell_in_closure)
                if dependents is not None:
                    dependents.discard(identity)
                    if not dependents:
                        del sheet_state.reverse_deps[cell_in_closure]

# ---------------------------------------------------------------------------
# Workbook
# ---------------------------------------------------------------------------

class Workbook:
    """In-memory multi-sheet spreadsheet engine.

    Public surface per R21: add_sheet, sheet, sheet_names, undo, redo,
    advance_clock, clock, to_json, from_json.
    """

    __slots__ = ("_sheets", "_order", "_clock", "_journal", "_redo_stack", "_eval_counts")

    def __init__(self):
        self._sheets = {}      # name -> _SheetState
        self._order = []       # creation-order list of names
        self._clock = 0
        self._journal = []     # list of journal entries
        self._redo_stack = []  # list of journal entries
        self._eval_counts = {} # name -> cumulative eval_count (lifetime)

    def _public_to_kind(self, value):
        if isinstance(value, _ErrorValue):
            return ("error", value.code)
        if isinstance(value, int):
            return ("int", value)
        if isinstance(value, str):
            return ("str", value)
        return ("empty", None)

    def _evaluate_cell(self, sheet_name, addr, in_progress, reached_formula_cells):
        if sheet_name not in self._sheets:
            return ("error", REF_ERROR)
        if not _is_valid_address(addr):
            return ("invalid", None)
        identity = (sheet_name, addr)
        state = self._sheets[sheet_name]
        if identity in in_progress:
            return ("error", "#CYCLE!")
        raw = state.cells.get(addr)
        if raw is None:
            return ("empty", None)
        if isinstance(raw, int):
            return ("int", raw)
        if not (isinstance(raw, str) and raw.startswith("=")):
            return ("str", raw)

        formula_text = raw[1:]
        if not _check_formula_bounds(formula_text):
            result = _ErrorValue(PARSE_ERROR)
            state.cache[addr] = result
            return ("error", PARSE_ERROR)
        reached_formula_cells[0] += 1
        if reached_formula_cells[0] > _MAX_REACHED_FORMULA_CELLS:
            result = _ErrorValue(PARSE_ERROR)
            state.cache[addr] = result
            return ("error", PARSE_ERROR)
        if addr in state.cache:
            closure = state.identity_closure_cache.get(addr)
            if closure is not None:
                extra_formula_cells = 0
                for target_sheet, target_addr in closure:
                    if (target_sheet, target_addr) == identity:
                        continue
                    if target_sheet not in self._sheets:
                        continue
                    target_raw = self._sheets[target_sheet].cells.get(target_addr)
                    if isinstance(target_raw, str) and target_raw.startswith("="):
                        extra_formula_cells += 1
                reached_formula_cells[0] += extra_formula_cells
                if reached_formula_cells[0] > _MAX_REACHED_FORMULA_CELLS:
                    return ("error", PARSE_ERROR)
            return self._public_to_kind(state.cache[addr])

        def _resolve_ref(ref_addr, sheet_qualifier=None):
            target_sheet = sheet_qualifier if sheet_qualifier is not None else sheet_name
            return self._evaluate_cell(target_sheet, _strip_abs_ref(ref_addr), in_progress, reached_formula_cells)

        def _resolve_count_ref(ref_addr, sheet_qualifier=None):
            target_sheet = sheet_qualifier if sheet_qualifier is not None else sheet_name
            if target_sheet not in self._sheets or not _is_valid_address(ref_addr):
                return ("invalid", None)
            value = self._sheets[target_sheet].cells.get(_strip_abs_ref(ref_addr))
            if value is None:
                return ("empty", None)
            if isinstance(value, int):
                return ("int", value)
            if isinstance(value, str):
                return ("formula", None) if value.startswith("=") else ("str", value)
            return ("empty", None)

        def _resolve_name(name):
            names = state.names
            if name not in names:
                return ("invalid", None)
            target = names[name]
            target_sheet, ref1, ref2 = _split_name_target(target)
            if target_sheet is not None and target_sheet not in self._sheets:
                return ("invalid", None)
            prefix = f"{target_sheet}!" if target_sheet is not None else ""
            if ref2 is None or ref1 == ref2:
                return ("cell", prefix + ref1)
            return ("range", prefix + ref1 + ":" + ref2)

        state.eval_count += 1
        in_progress.add(identity)
        try:
            result = parse_formula(
                formula_text,
                resolve_ref=_resolve_ref,
                eval_count=[0],
                resolve_count_ref=_resolve_count_ref,
                resolve_name=_resolve_name,
                resolve_now=lambda: self._clock,
            )
        finally:
            in_progress.discard(identity)

        state.cache[addr] = result
        self._store_closure(sheet_name, addr, formula_text)
        return self._public_to_kind(result)

    def _store_closure(self, sheet_name, addr, formula_text):
        state = self._sheets[sheet_name]
        state.handle._remove_reverse_deps_for(addr)
        identity = (sheet_name, addr)
        closure = {identity}
        closure.update(self._compute_closure_identity(sheet_name, formula_text, set()))
        state.identity_closure_cache[addr] = closure
        for cell_identity in closure:
            state.reverse_deps.setdefault(cell_identity, set()).add(identity)

    def _compute_closure_identity(self, sheet_name, formula_text, visited):
        from gridcalc.formula import _tokenize, _parse_expr

        def direct_references(current_sheet, current_formula_text):
            tokens = _tokenize(current_formula_text)
            if tokens is None:
                return []
            pos = [0]
            ast_node = _parse_expr(tokens, pos)
            if ast_node is None or pos[0] != len(tokens):
                return []

            refs = []
            seen_refs = set()

            def add_identity(target_sheet, target_addr):
                identity = (target_sheet, _strip_abs_ref(target_addr))
                if identity not in seen_refs:
                    seen_refs.add(identity)
                    refs.append(identity)

            def add_cell(target_sheet, target_addr):
                if target_sheet in self._sheets and _formula_is_valid_address(target_addr):
                    add_identity(target_sheet, target_addr)

            def add_range(target_sheet, ref1, ref2):
                if target_sheet not in self._sheets:
                    return
                if not (_formula_is_valid_address(ref1) and _formula_is_valid_address(ref2)):
                    return
                col1, row1 = _parse_address(ref1)
                col2, row2 = _parse_address(ref2)
                if col1 > col2 or row1 > row2:
                    return
                for row in range(row1, row2 + 1):
                    for col_ord in range(ord(col1), ord(col2) + 1):
                        add_identity(target_sheet, f"{chr(col_ord)}{row}")

            def add_name(name):
                names = self._sheets[current_sheet].names
                if name not in names:
                    return
                target_sheet, ref1, ref2 = _split_name_target(names[name])
                target_sheet = target_sheet if target_sheet is not None else current_sheet
                if ref2 is None:
                    add_cell(target_sheet, ref1)
                else:
                    add_range(target_sheet, ref1, ref2)

            def walk(node):
                if node is None:
                    return
                kind = node[0]
                if kind == "REF":
                    add_cell(current_sheet, node[1])
                elif kind == "QREF":
                    add_cell(node[1], node[2])
                elif kind == "RANGE":
                    add_range(current_sheet, node[1], node[2])
                elif kind == "QRANGE":
                    add_range(node[1], node[2], node[3])
                elif kind == "NAME":
                    add_name(node[1])
                elif kind == "FUNC":
                    arg = node[2]
                    if isinstance(arg, list):
                        for child in arg:
                            walk(child)
                    elif isinstance(arg, tuple) and len(arg) == 2 and arg[0] == "NAME":
                        add_name(arg[1])
                    else:
                        walk(arg)
                elif kind in ("ADD", "MUL", "CMP"):
                    walk(node[2])
                    walk(node[3])
                elif kind == "NEG":
                    walk(node[1])
                elif kind == "IF":
                    walk(node[1])
                    walk(node[2])
                    walk(node[3])

            walk(ast_node)
            return refs

        closure = set()
        stack = [(sheet_name, formula_text)]
        formula_members = 0

        while stack:
            current_sheet, current_formula_text = stack.pop()
            for target_identity in direct_references(current_sheet, current_formula_text):
                target_sheet, target_addr = target_identity
                raw = self._sheets[target_sheet].cells.get(target_addr)
                is_formula = isinstance(raw, str) and raw.startswith("=")
                is_new = target_identity not in closure
                if is_formula and is_new:
                    if formula_members >= _MAX_REACHED_FORMULA_CELLS - 1:
                        continue
                    formula_members += 1
                closure.add(target_identity)
                if is_formula and target_identity not in visited:
                    visited.add(target_identity)
                    stack.append((target_sheet, raw[1:]))

        return closure

    def _invalidate_identity(self, sheet_name, addr):
        identity = (sheet_name, addr)
        if sheet_name in self._sheets:
            self._sheets[sheet_name].cache.pop(addr, None)
        for state in self._sheets.values():
            for dep_sheet, dep_addr in list(state.reverse_deps.get(identity, set())):
                if dep_sheet in self._sheets:
                    self._sheets[dep_sheet].cache.pop(dep_addr, None)

    def _invalidate_all_formula_caches(self):
        for state in self._sheets.values():
            state.cache.clear()

    def _formula_text_contains_now(self, formula_text):
        ast_node = _parse_formula_ast(formula_text)
        return ast_node is not None and _ast_contains_now(ast_node)

    def _formula_cell_is_volatile(self, sheet_name, addr):
        if sheet_name not in self._sheets:
            return False
        raw = self._sheets[sheet_name].cells.get(addr)
        if not (isinstance(raw, str) and raw.startswith("=")):
            return False
        formula_text = raw[1:]
        if _parse_formula_ast(formula_text) is None:
            return False
        if self._formula_text_contains_now(formula_text):
            return True
        closure = self._compute_closure_identity(sheet_name, formula_text, set())
        for target_sheet, target_addr in closure:
            if target_sheet not in self._sheets:
                continue
            target_raw = self._sheets[target_sheet].cells.get(target_addr)
            if isinstance(target_raw, str) and target_raw.startswith("="):
                if self._formula_text_contains_now(target_raw[1:]):
                    return True
        return False

    def _invalidate_volatile_formula_caches(self):
        volatile_cells = []
        for sheet_name, state in self._sheets.items():
            for addr, raw in state.cells.items():
                if isinstance(raw, str) and raw.startswith("="):
                    if self._formula_cell_is_volatile(sheet_name, addr):
                        volatile_cells.append((sheet_name, addr))
        for sheet_name, addr in volatile_cells:
            self._sheets[sheet_name].cache.pop(addr, None)

    def _invalidate_sheet_qualifier(self, sheet_name):
        """Invalidate all formula cells that mention *sheet_name* as a qualifier.

        Scans parsed formula cells across all sheets instead of depending on
        closure entries, because absent qualified sheets contribute no closure
        members.
        """
        for sheet_state in self._sheets.values():
            handle = sheet_state.handle
            formula_addrs = [
                addr for addr, value in sheet_state.cells.items()
                if isinstance(value, str) and value.startswith("=")
            ]
            for addr in formula_addrs:
                formula_text = sheet_state.cells[addr][1:]
                if self._formula_mentions_sheet_qualifier(formula_text, sheet_name):
                    handle._cache.pop(addr, None)
                    handle._invalidate_dependents(addr)

    def _formula_mentions_sheet_qualifier(self, formula_text, sheet_name):
        if _parse_formula_ast(formula_text) is None:
            return False
        from gridcalc.formula import _tokenize
        tokens = _tokenize(formula_text)
        if tokens is None:
            return False
        return any(tok_type == "SHEET" and tok_val == sheet_name for tok_type, tok_val in tokens)

    # -- sheet management ---------------------------------------------------

    def add_sheet(self, name):
        """Create a new empty sheet. Returns its handle."""
        if not isinstance(name, str):
            raise ValueError(
                f"Sheet name must be str, got {type(name).__name__}"
            )
        plain = str(name)
        if not _is_valid_sheet_name(plain):
            raise ValueError(
                f"Invalid sheet name: {plain!r}"
            )
        if plain in self._sheets:
            raise ValueError(f"Duplicate sheet name: {plain!r}")
        state = _SheetState()
        handle = _SheetHandle(plain, self, state)
        state.handle = handle
        # Restore eval_count from previous lifetime if it exists.
        if plain in self._eval_counts:
            state.eval_count = self._eval_counts[plain]
        self._sheets[plain] = state
        self._order.append(plain)
        # Journal the add_sheet with its state for redo reuse.
        self._journal.append(("add_sheet", plain, state))
        # New journaled op clears redo stack.
        self._redo_stack.clear()
        # Invalidate formula cells that mention this sheet as a qualifier.
        self._invalidate_sheet_qualifier(plain)
        return handle

    def sheet(self, name):
        """Return the handle for an existing sheet."""
        if not isinstance(name, str):
            raise ValueError(f"Sheet name must be str, got {type(name).__name__}")
        plain = str(name)
        if not _is_valid_sheet_name(plain):
            raise ValueError(f"Invalid sheet name: {plain!r}")
        if plain not in self._sheets:
            raise ValueError(f"Unknown sheet: {plain!r}")
        return self._sheets[plain].handle

    @property
    def sheet_names(self):
        """Return a fresh list of current sheet names in creation order."""
        return list(self._order)

    # -- clock --------------------------------------------------------------

    @property
    def clock(self):
        """Read-only clock value."""
        return self._clock

    def advance_clock(self):
        """Increment clock by 1, return new value, journal the change."""
        old = self._clock
        self._clock += 1
        self._invalidate_volatile_formula_caches()
        self._journal.append(("advance_clock", old, self._clock))
        self._redo_stack.clear()
        return self._clock

    # -- undo / redo --------------------------------------------------------

    def undo(self):
        """Revert the most recent journal entry. Return True on success."""
        if not self._journal:
            return False
        entry = self._journal.pop()
        self._redo_stack.append(entry)
        self._revert_entry(entry)
        return True

    def redo(self):
        """Re-apply the most recently undone entry. Return True on success."""
        if not self._redo_stack:
            return False
        entry = self._redo_stack.pop()
        self._journal.append(entry)
        self._apply_entry(entry)
        return True

    def _revert_entry(self, entry):
        """Revert a single journal entry."""
        op = entry[0]
        if op == "add_sheet":
            name = entry[1]
            state = self._sheets[name]
            # Save eval_count to lifetime dict before removing.
            self._eval_counts[name] = state.eval_count
            self._sheets.pop(name)
            self._order.remove(name)
            # Invalidate formula cells that mention this sheet as a qualifier.
            self._invalidate_sheet_qualifier(name)
        elif op in ("set", "copy"):
            _, sheet_name, addr, old_value, _new_value = entry
            handle = self._sheets[sheet_name].handle
            handle._replace_cell(addr, old_value)
        elif op == "define_name":
            _, sheet_name, name, old_binding, _new_binding = entry
            handle = self._sheets[sheet_name].handle
            if old_binding is None:
                # Restore to undefined state.
                handle._names.pop(name, None)
            else:
                handle._names[name] = old_binding
            # Invalidate formula cells that mention this name.
            handle._invalidate_names_dependents(name)
        elif op == "advance_clock":
            prev = entry[1]
            self._clock = prev
            self._invalidate_volatile_formula_caches()

    def _apply_entry(self, entry):
        """Re-apply a single journal entry."""
        op = entry[0]
        if op == "add_sheet":
            name = entry[1]
            state = entry[2]
            self._sheets[name] = state
            self._order.append(name)
            # Invalidate formula cells that mention this sheet as a qualifier.
            self._invalidate_sheet_qualifier(name)
        elif op in ("set", "copy"):
            _, sheet_name, addr, _old_value, new_value = entry
            handle = self._sheets[sheet_name].handle
            handle._replace_cell(addr, new_value)
        elif op == "define_name":
            _, sheet_name, name, _old_binding, new_binding = entry
            handle = self._sheets[sheet_name].handle
            handle._names[name] = new_binding
            # Invalidate formula cells that mention this name.
            handle._invalidate_names_dependents(name)
        elif op == "advance_clock":
            new_val = entry[2]
            self._clock = new_val
            self._invalidate_volatile_formula_caches()

    # -- persistence --------------------------------------------------------

    def to_json(self):
        """Serialize workbook state to a JSON string."""
        sheets = []
        for name in self._order:
            state = self._sheets[name]
            sheets.append({
                "name": name,
                "cells": dict(state.cells),
                "names": dict(state.names),
            })
        return json.dumps(
            {"version": 1, "clock": self._clock, "sheets": sheets},
            allow_nan=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, s):
        """Deserialize a workbook from a JSON string."""
        if not isinstance(s, str):
            raise ValueError("Workbook JSON input must be str")

        def reject_duplicate_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"Duplicate JSON object key: {key!r}")
                result[key] = value
            return result

        def reject_float(_text):
            raise ValueError("JSON floats are not accepted")

        data = json.loads(
            s,
            object_pairs_hook=reject_duplicate_keys,
            parse_float=reject_float,
            parse_constant=reject_float,
        )

        if not isinstance(data, dict) or set(data) != {"version", "clock", "sheets"}:
            raise ValueError("Invalid workbook JSON schema")
        if data["version"] != 1:
            raise ValueError("Unsupported workbook JSON version")
        clock = data["clock"]
        if isinstance(clock, bool) or not isinstance(clock, int) or clock < 0:
            raise ValueError("Invalid workbook clock")
        sheets_data = data["sheets"]
        if not isinstance(sheets_data, list):
            raise ValueError("Invalid workbook sheets")

        wb = cls()
        wb._clock = clock
        seen_names = set()

        for sheet_data in sheets_data:
            if not isinstance(sheet_data, dict) or set(sheet_data) != {"name", "cells", "names"}:
                raise ValueError("Invalid sheet schema")
            sheet_name = sheet_data["name"]
            if not _is_valid_sheet_name(sheet_name):
                raise ValueError("Invalid sheet name")
            sheet_name = str(sheet_name)
            if sheet_name in seen_names:
                raise ValueError("Duplicate sheet name")
            cells = sheet_data["cells"]
            names = sheet_data["names"]
            if not isinstance(cells, dict) or not isinstance(names, dict):
                raise ValueError("Invalid sheet schema")

            state = _SheetState()
            handle = _SheetHandle(sheet_name, wb, state)
            state.handle = handle

            for addr, value in cells.items():
                if not _is_valid_address(addr):
                    raise ValueError("Invalid cell address")
                if isinstance(value, bool) or not isinstance(value, (int, str)):
                    raise ValueError("Invalid cell value")
                state.cells[str(addr)] = int(value) if isinstance(value, int) else str(value)

            wb._sheets[sheet_name] = state
            wb._order.append(sheet_name)
            seen_names.add(sheet_name)

        for sheet_data in sheets_data:
            sheet_name = str(sheet_data["name"])
            state = wb._sheets[sheet_name]
            for name, target in sheet_data["names"].items():
                if not _is_valid_name(name):
                    raise ValueError("Invalid name binding")
                if not _is_valid_target_for_workbook(target, wb):
                    raise ValueError("Invalid name target")
                state.names[str(name)] = str(target)

        return wb
