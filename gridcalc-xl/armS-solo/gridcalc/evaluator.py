"""Formula evaluator for gridcalc.

Evaluates an AST produced by the parser in the context of a Workbook,
tracking cycles, caching results, and enforcing the typed error-ordering
rules (R5, R13).
"""

from __future__ import annotations

import re as _re
import string as _string_mod

from .ast import (
    BinOp,
    FuncCall,
    HashRef,
    IntLit,
    Name,
    Range,
    Ref,
    StringLit,
    UnaryMinus,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_INT = (2**63) - 1
_MAX_STR_LEN = 4096

_ERR_REF = "#REF!"
_ERR_TYPE = "#TYPE!"
_ERR_DIV = "#DIV!"
_ERR_CYCLE = "#CYCLE!"
_ERR_PARSE = "#PARSE!"
_ERR_NAME = "#NAME!"

_ERROR_STRINGS = frozenset({_ERR_REF, _ERR_TYPE, _ERR_DIV, _ERR_CYCLE, _ERR_PARSE, _ERR_NAME})

_VALID_COLS = set(_string_mod.ascii_uppercase)

# R27: Syntactic check for NOW() in formula text.
_NOW_RE = _re.compile(r"\bNOW\s*\(")


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def _is_err(val: object) -> bool:
    """Check if a value is an error string (e.g., #REF!, #TYPE!, #CYCLE!)."""
    return val in _ERROR_STRINGS


# ---------------------------------------------------------------------------
# Address validation (R1)
# ---------------------------------------------------------------------------


def _valid_addr(addr: str) -> bool:
    if not isinstance(addr, str) or len(addr) < 2:
        return False
    if addr[0] not in _VALID_COLS:
        return False
    digits = addr[1:]
    if not digits.isdigit():
        return False
    if len(digits) > 2:
        return False
    if len(digits) == 2 and digits[0] == "0":
        return False
    return 1 <= int(digits) <= 99


# ---------------------------------------------------------------------------
# Volatility check (R27)
# ---------------------------------------------------------------------------


def _formula_has_now(formula_text: str) -> bool:
    """Check if a formula text contains a NOW() call (syntactic, R27)."""
    return bool(_NOW_RE.search(formula_text))


# ---------------------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------------------


def _ref_key(ref: Ref, hosting: str) -> tuple[str, str] | None:
    """Resolve a Ref to (sheet, addr).  Returns None on invalid ref."""
    if ref.col not in _VALID_COLS:
        return None
    if ref.row < 1 or ref.row > 99:
        return None
    # Check for leading zero in the original row string
    if getattr(ref, '_has_leading_zero', False):
        return None

    sheet = ref.qualifier if ref.qualifier is not None else hosting
    return (sheet, f"{ref.col}{ref.row}")


def _range_cells(rng: Range, hosting: str, wb) -> list[tuple[str, str]] | None:
    """Resolve a Range to row-major (sheet, addr) list.  None on invalid."""
    sk = _ref_key(rng.start, hosting)
    if sk is None:
        return None
    ek = _ref_key(rng.end, hosting)
    if ek is None:
        return None
    ss, sa = sk
    es, ea = ek
    if ss != es:
        return None
    sc, sr = sa[0], int(sa[1:])
    ec, er = ea[0], int(ea[1:])
    if sc > ec or sr > er:
        return None
    out: list[tuple[str, str]] = []
    for r in range(sr, er + 1):
        for ci in range(ord(sc), ord(ec) + 1):
            out.append((ss, f"{chr(ci)}{r}"))
    return out


# ---------------------------------------------------------------------------
# Name resolution helpers
# ---------------------------------------------------------------------------


def _name_cells(name_str: str, sheet_name: str, wb) -> list[tuple[str, str]] | str | None:
    """Resolve a name binding string to cells.

    Returns:
      - list of (sheet, addr) for valid range/single-address
      - ``None`` if the binding string is malformed (treat as no cells)
      - ``#REF!`` / ``#NAME!`` for definitive errors
    """
    if ":" in name_str:
        parts = name_str.split(":")
        if len(parts) != 2:
            return _ERR_REF
        if not _valid_addr(parts[0]) or not _valid_addr(parts[1]):
            return _ERR_REF
        c1, r1 = parts[0][0], int(parts[0][1:])
        c2, r2 = parts[1][0], int(parts[1][1:])
        if c1 > c2 or r1 > r2:
            return _ERR_REF
        cells: list[tuple[str, str]] = []
        for r in range(r1, r2 + 1):
            for ci in range(ord(c1), ord(c2) + 1):
                cells.append((sheet_name, f"{chr(ci)}{r}"))
        return cells
    else:
        if not _valid_addr(name_str):
            return _ERR_REF
        return [(sheet_name, name_str)]


def _name_as_primary(name_str: str, sheet_name: str, wb, ctx) -> object:
    """Evaluate a NAME used as a primary expression (R18).

    Single address or 1x1 range → typed value of that cell.
    Larger range → ``#REF!``.
    """
    result = _name_cells(name_str, sheet_name, wb)
    if result is None or isinstance(result, str):
        return result
    if len(result) == 1:
        _, addr = result[0]
        return _get_cell(addr, wb, sheet_name, ctx)
    return _ERR_REF


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


class _Ctx:
    __slots__ = ("wb", "host", "clock", "evaluating", "_reached")

    def __init__(self, wb, host: str, clock: int):
        self.wb = wb
        self.host = host
        self.clock = clock
        self.evaluating: set[tuple[str, str]] = set()
        self._reached: int = 0


# ---------------------------------------------------------------------------
# Cell access
# ---------------------------------------------------------------------------


def _get_cell(addr: str, wb, host: str, ctx: _Ctx) -> object:
    """Read a cell by plain address on *host* sheet (used for name targets
    and range member evaluation)."""
    sheet = wb.sheets.get(host)
    if sheet is None:
        return _ERR_REF
    ctx._reached += 1

    content = sheet._cells.get(addr)
    if content is None:
        return 0
    if isinstance(content, bool):
        return int(content)
    if isinstance(content, int):
        return content
    if isinstance(content, str):
        if content.startswith("="):
            return _eval_formula(content[1:], addr, wb, host, ctx)
        return content
    return 0


def _get_cell_keyed(key: tuple[str, str], wb, ctx: _Ctx) -> object:
    """Read a cell by (sheet, addr) key."""
    s_name, addr = key
    sheet = wb.sheets.get(s_name)
    if sheet is None:
        return _ERR_REF
    ctx._reached += 1

    content = sheet._cells.get(addr)
    if content is None:
        return 0
    if isinstance(content, bool):
        return int(content)
    if isinstance(content, int):
        return content
    if isinstance(content, str):
        if content.startswith("="):
            return _eval_formula(content[1:], addr, wb, s_name, ctx)
        return content
    return 0


def _eval_formula(text: str, addr: str, wb, host: str, ctx: _Ctx) -> object:
    """Parse and evaluate a formula text (without leading '=')."""
    from .parser import parse as _parse

    sheet = wb.sheets.get(host)

    # Check cache — for volatile cells, only use cache if clock matches
    if sheet is not None and addr in sheet._eval_cache:
        cached_clock, cached_val = sheet._eval_cache[addr]
        if cached_clock == ctx.clock:
            return cached_val
        # Clock changed — for volatile cells, we need to re-evaluate
        # For non-volatile cells, the cache is still valid
        if not _formula_has_now(text):
            return cached_val
        # Volatile cell with changed clock — fall through to re-evaluate

    # Increment counter for this formula cell evaluation
    if sheet is not None:
        sheet._eval_count += 1

    ctx._reached += 1

    key = (host, addr)
    if key in ctx.evaluating:
        return _ERR_CYCLE

    ctx.evaluating.add(key)
    try:
        ast = _parse(text)
        if ast is None:
            result = _ERR_PARSE
        else:
            result = _ev(ast, wb, host, ctx)
        # Store with current clock value
        if sheet is not None:
            sheet._eval_cache[addr] = (ctx.clock, result)
        return result
    finally:
        ctx.evaluating.discard(key)


# ---------------------------------------------------------------------------
# AST evaluation
# ---------------------------------------------------------------------------


def _ev(node, wb, host: str, ctx: _Ctx) -> object:
    if isinstance(node, IntLit):
        return node.value
    if isinstance(node, StringLit):
        return node.value
    if isinstance(node, HashRef):
        return _ERR_REF
    if isinstance(node, Ref):
        return _ev_ref(node, wb, host, ctx)
    if isinstance(node, Name):
        return _ev_name(node, wb, host, ctx)
    if isinstance(node, UnaryMinus):
        v = _ev(node.operand, wb, host, ctx)
        if _is_err(v):
            return v
        if not isinstance(v, int) or isinstance(v, bool):
            return _ERR_TYPE
        return -v
    if isinstance(node, BinOp):
        return _ev_binop(node, wb, host, ctx)
    if isinstance(node, FuncCall):
        return _ev_func(node, wb, host, ctx)
    if isinstance(node, Range):
        return _ERR_REF  # ranges only inside function args
    return _ERR_PARSE


def _ev_ref(ref: Ref, wb, host: str, ctx: _Ctx) -> object:
    key = _ref_key(ref, host)
    if key is None:
        return _ERR_REF
    return _get_cell_keyed(key, wb, ctx)


def _ev_name(node: Name, wb, host: str, ctx: _Ctx) -> object:
    sheet = wb.sheets.get(host)
    if sheet is None:
        return _ERR_NAME
    binding = sheet._names.get(node.name)
    if binding is None:
        return _ERR_NAME
    return _name_as_primary(binding, host, wb, ctx)


def _ev_binop(node: BinOp, wb, host: str, ctx: _Ctx) -> object:
    op = node.op
    left = _ev(node.left, wb, host, ctx)
    if _is_err(left):
        return left
    right = _ev(node.right, wb, host, ctx)
    if _is_err(right):
        return right

    if op in ("+", "-", "*", "/"):
        if not isinstance(left, int) or isinstance(left, bool):
            return _ERR_TYPE
        if not isinstance(right, int) or isinstance(right, bool):
            return _ERR_TYPE
        result = _arith(op, left, right)
        if _is_err(result):
            return result
        return result

    if op in ("=", "<>", "<", "<=", ">", ">="):
        return _cmp(op, left, right)

    return _ERR_PARSE


def _arith(op: str, a: int, b: int) -> int | str:
    if op == "+":
        r = a + b
    elif op == "-":
        r = a - b
    elif op == "*":
        r = a * b
    elif op == "/":
        if b == 0:
            return _ERR_DIV
        # Truncate toward zero
        r = int(a / b)
    else:
        return _ERR_PARSE
    if abs(r) > _MAX_INT:
        return _ERR_TYPE
    return r


def _cmp(op: str, a: object, b: object) -> int | str:
    a_int = isinstance(a, int) and not isinstance(a, bool)
    b_int = isinstance(b, int) and not isinstance(b, bool)
    a_str = isinstance(a, str)
    b_str = isinstance(b, str)
    if not (a_int and b_int) and not (a_str and b_str):
        return _ERR_TYPE
    if op == "=":
        return 1 if a == b else 0
    if op == "<>":
        return 1 if a != b else 0
    if op == "<":
        return 1 if a < b else 0
    if op == "<=":
        return 1 if a <= b else 0
    if op == ">":
        return 1 if a > b else 0
    if op == ">=":
        return 1 if a >= b else 0
    return _ERR_PARSE


def _ev_func(node: FuncCall, wb, host: str, ctx: _Ctx) -> object:
    name = node.name
    if name == "NOW":
        return ctx.clock
    if name in ("SUM", "MIN", "MAX", "COUNT"):
        return _ev_agg(name, node.args[0], wb, host, ctx)
    if name == "CONCAT":
        return _ev_concat(node.args, wb, host, ctx)
    if name == "LEN":
        return _ev_len(node.args[0], wb, host, ctx)
    if name == "IF":
        return _ev_if(node.args, wb, host, ctx)
    return _ERR_PARSE


def _ev_range_arg(arg, wb, host: str, ctx: _Ctx) -> list[tuple[str, str]] | str | None:
    """Evaluate a RANGE-ARG.  Returns cell list, error string, or None."""
    if isinstance(arg, HashRef):
        return _ERR_REF
    if isinstance(arg, Range):
        cells = _range_cells(arg, host, wb)
        return cells if cells is not None else _ERR_REF
    if isinstance(arg, Name):
        sheet = wb.sheets.get(host)
        if sheet is None:
            return _ERR_NAME
        binding = sheet._names.get(arg.name)
        if binding is None:
            return None
        result = _name_cells(binding, host, wb)
        if isinstance(result, str):
            return result
        return result if result is not None else None
    return _ERR_REF


def _ev_agg(name: str, arg, wb, host: str, ctx: _Ctx) -> object:
    result = _ev_range_arg(arg, wb, host, ctx)
    if isinstance(result, str):
        return result
    if result is None:
        return _ERR_TYPE if name != "COUNT" else 0

    if name == "COUNT":
        # COUNT returns the number of non-empty cells
        count = 0
        for key in result:
            s_name, addr = key
            sheet = wb.sheets.get(s_name)
            if sheet is None:
                continue
            content = sheet._cells.get(addr)
            if content is not None:
                count += 1
        return count

    vals: list[int] = []
    for key in result:
        v = _get_cell_keyed(key, wb, ctx)
        if _is_err(v):
            return v
        if not isinstance(v, int) or isinstance(v, bool):
            return _ERR_TYPE
        vals.append(v)

    if name == "SUM":
        return sum(vals) if vals else 0
    if name == "MIN":
        return min(vals) if vals else _ERR_TYPE
    if name == "MAX":
        return max(vals) if vals else _ERR_TYPE
    return _ERR_PARSE


def _ev_concat(args, wb, host: str, ctx: _Ctx) -> str | str:
    parts: list[str] = []
    for a in args:
        v = _ev(a, wb, host, ctx)
        if _is_err(v):
            return v
        if isinstance(v, bool):
            v = int(v)
        if isinstance(v, int):
            s = str(v)
        elif isinstance(v, str):
            s = v
        else:
            return _ERR_TYPE
        if len(s) > _MAX_STR_LEN:
            return _ERR_TYPE
        parts.append(s)
    out = "".join(parts)
    if len(out) > _MAX_STR_LEN:
        return _ERR_TYPE
    return out


def _ev_len(arg, wb, host: str, ctx: _Ctx) -> int | str:
    v = _ev(arg, wb, host, ctx)
    if _is_err(v):
        return v
    if isinstance(v, bool):
        v = int(v)
    if isinstance(v, int):
        return len(str(v))
    if isinstance(v, str):
        return len(v)
    return _ERR_TYPE


def _ev_if(args, wb, host: str, ctx: _Ctx) -> object:
    cond = _ev(args[0], wb, host, ctx)
    if _is_err(cond):
        return cond
    if isinstance(cond, str):
        return _ERR_TYPE
    if not isinstance(cond, int) or isinstance(cond, bool):
        return _ERR_TYPE
    branch = args[1] if cond != 0 else args[2]
    return _ev(branch, wb, host, ctx)
