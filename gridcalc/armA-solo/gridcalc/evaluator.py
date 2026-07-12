"""Formula evaluator for gridcalc.

Evaluates parsed ASTs against a Sheet, handling references, functions,
cycles, and errors.
"""

from __future__ import annotations

from gridcalc.parser import (
    PARSE_ERROR, IntLit, Ref, FuncCall, BinOp, UnaryMinus, parse,
)

# Error strings (R5)
ERR_PARSE = "#PARSE!"
ERR_REF = "#REF!"
ERR_TYPE = "#TYPE!"
ERR_DIV = "#DIV!"
ERR_CYCLE = "#CYCLE!"

_MAX_ADDR_ROW = 99
_MAX_ADDR_COL = 26  # A-Z


def _valid_addr(addr: str) -> bool:
    """Check if addr is a valid grid cell address (single uppercase letter + 1-2 digit row 1-99)."""
    if len(addr) < 2:
        return False
    col = addr[0]
    row_str = addr[1:]
    if not col.isalpha() or not col.isupper():
        return False
    if not row_str.isdigit():
        return False
    if len(row_str) > 2:
        return False
    # no leading zeros in row
    if len(row_str) == 2 and row_str[0] == "0":
        return False
    row = int(row_str)
    return 1 <= row <= _MAX_ADDR_ROW


def _addr_to_key(addr: str) -> str:
    """Normalize address to canonical form for storage lookups."""
    return addr  # already canonical from validation


def _parse_addr(addr: str):
    """Parse address into (col_letter, row_int). Returns None if invalid."""
    if not _valid_addr(addr):
        return None
    return addr[0], int(addr[1:])


class _EvalState:
    """Holds evaluation context: cycle detection, eval_count, etc."""

    def __init__(self, sheet, count_ref: list[int]):
        self.sheet = sheet
        self.count = count_ref  # mutable counter [int]
        self.in_progress: set[str] = set()  # cells currently being evaluated


def _eval_node(node, state: _EvalState):
    """Evaluate an AST node. Returns int or error string."""
    if node is PARSE_ERROR:
        return ERR_PARSE

    if isinstance(node, IntLit):
        return node.value

    if isinstance(node, UnaryMinus):
        val = _eval_node(node.operand, state)
        if isinstance(val, str):
            return val
        return -val

    if isinstance(node, BinOp):
        left = _eval_node(node.left, state)
        if isinstance(left, str):
            return left  # short-circuit
        right = _eval_node(node.right, state)
        if isinstance(right, str):
            return right  # short-circuit
        op = node.op
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                return ERR_DIV
            # truncation toward zero
            return int(left / right)
        # comparison operators
        if op == "=":
            return 1 if left == right else 0
        if op == "<>":
            return 1 if left != right else 0
        if op == "<":
            return 1 if left < right else 0
        if op == "<=":
            return 1 if left <= right else 0
        if op == ">":
            return 1 if left > right else 0
        if op == ">=":
            return 1 if left >= right else 0
        return ERR_PARSE

    if isinstance(node, Ref):
        return _eval_ref(node.addr, state)

    if isinstance(node, FuncCall):
        return _eval_func(node, state)

    return ERR_PARSE


def _eval_ref(addr: str, state: _EvalState):
    """Evaluate a single cell reference."""
    parsed = _parse_addr(addr)
    if parsed is None:
        return ERR_REF

    col, row = parsed
    cell = state.sheet._cells.get(addr)

    if cell is None:
        # empty cell → 0
        return 0

    if cell._is_formula:
        # formula cell
        if addr in state.in_progress:
            return ERR_CYCLE
        state.in_progress.add(addr)
        state.count[0] += 1
        try:
            result = _eval_node(cell._ast, state)
        finally:
            state.in_progress.discard(addr)
        # cache result
        cell._cached = result
        cell._has_cache = True
        return result
    else:
        # literal cell
        if isinstance(cell._value, str):
            return ERR_TYPE
        return cell._value  # int

    return 0


def _iter_range(tl_addr: str, br_addr: str):
    """Iterate range cells in row-major order. Returns list of addresses."""
    tl_parsed = _parse_addr(tl_addr)
    br_parsed = _parse_addr(br_addr)
    if tl_parsed is None or br_parsed is None:
        return None  # invalid

    tl_col, tl_row = tl_parsed
    br_col, br_row = br_parsed

    # validate column range
    tl_col_ord = ord(tl_col) - ord("A") + 1
    br_col_ord = ord(br_col) - ord("A") + 1
    if tl_col_ord > br_col_ord or tl_row > br_row:
        return None

    cells = []
    for r in range(tl_row, br_row + 1):
        for c_ord in range(tl_col_ord, br_col_ord + 1):
            c_letter = chr(ord("A") + c_ord - 1)
            cells.append(f"{c_letter}{r}")
    return cells


def _eval_func(node: FuncCall, state: _EvalState):
    """Evaluate a function call."""
    name = node.name
    range_cells = _iter_range(node.range_ref_tl, node.range_ref_br)
    if range_cells is None:
        return ERR_REF

    if name == "COUNT":
        # COUNT: structural, no evaluation, no cycle detection, no eval_count
        count = 0
        for addr in range_cells:
            cell = state.sheet._cells.get(addr)
            if cell is not None:
                count += 1
        return count

    # SUM, MIN, MAX
    values = []
    for addr in range_cells:
        cell = state.sheet._cells.get(addr)
        if cell is None:
            # empty cell: skip for SUM/MIN/MAX
            continue
        if cell._is_formula:
            if addr in state.in_progress:
                return ERR_CYCLE
            state.in_progress.add(addr)
            state.count[0] += 1
            try:
                result = _eval_node(cell._ast, state)
            finally:
                state.in_progress.discard(addr)
            cell._cached = result
            cell._has_cache = True
        else:
            # literal cell: string → #TYPE! for SUM/MIN/MAX
            if isinstance(cell._value, str):
                return ERR_TYPE
            result = cell._value
        if isinstance(result, str):
            return result  # first error wins (from formula evaluation)
        values.append(result)

    if name == "SUM":
        return sum(values) if values else 0
    if name == "MIN":
        if not values:
            return ERR_TYPE
        return min(values)
    if name == "MAX":
        if not values:
            return ERR_TYPE
        return max(values)

    return ERR_PARSE


def evaluate(ast, sheet, count_ref: list[int]):
    """Evaluate a parsed AST against a sheet. Returns int or error string."""
    state = _EvalState(sheet, count_ref)
    return _eval_node(ast, state)
