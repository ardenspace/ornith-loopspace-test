import sys

from gridcalc.parser import parse, INT_T, REF_T, ADD, SUB, MUL, DIV, NEG, EQ, NEQ, LT, LTE, GT, GTE, FUNC_T, RANGE_T, SUM_T, MIN_T, MAX_T, COUNT_T
from gridcalc.sheet import Sheet, _validate_address

# R12: Raise recursion limit to handle 256-cell reference chains and deep formula nesting.
# Default is 1000, which is insufficient for the R12 bounds.
sys.setrecursionlimit(10000)

# Error markers
PARSE_ERROR = "#PARSE!"
REF_ERROR = "#REF!"
TYPE_ERROR = "#TYPE!"
DIV_ERROR = "#DIV!"
CYCLE_ERROR = "#CYCLE!"


def _is_valid_ref(ref: str) -> bool:
    """Check if a reference denotes a valid grid cell (A1-Z99, no leading zeros in row)."""
    if len(ref) < 2:
        return False
    col = ref[0]
    row_str = ref[1:]
    if not col.isalpha() or not col.isupper():
        return False
    if not row_str.isdigit():
        return False
    row = int(row_str)
    # No leading zeros (except for single digit 0, but row 0 is invalid)
    if len(row_str) > 1 and row_str[0] == '0':
        return False
    if row < 1 or row > 99:
        return False
    return True


def _ref_to_coords(ref: str) -> tuple:
    """Convert a reference string to (col_idx, row_idx) tuple (0-indexed)."""
    col = ord(ref[0]) - ord('A')
    row = int(ref[1:]) - 1
    return (col, row)


def _coords_to_ref(col_idx: int, row_idx: int) -> str:
    """Convert (col_idx, row_idx) to reference string."""
    col = chr(ord('A') + col_idx)
    row = row_idx + 1
    return f"{col}{row}"


def _evaluate_node(node, sheet: Sheet, cycle_set: set = None) -> object:
    """Recursively evaluate an AST node. Returns int or error string."""
    if node is None:
        return PARSE_ERROR

    node_type = node[0]

    # Base cases: literals
    if node_type == INT_T:
        return node[1]
    elif node_type == REF_T:
        ref = node[1]
        if not _is_valid_ref(ref):
            return REF_ERROR
        # Check for cycles
        if cycle_set is not None and ref in cycle_set:
            return CYCLE_ERROR
        # Read from sheet, propagating cycle_set for nested formula evaluation
        raw = sheet.get(ref, cycle_set)
        if raw is None:
            return 0  # Empty cell contributes 0
        if isinstance(raw, str):
            # Propagate error strings (#CYCLE!, #TYPE!, etc.) directly
            if raw.startswith("#"):
                return raw
            return TYPE_ERROR  # String cell yields #TYPE! in numeric context
        if isinstance(raw, int):
            return raw
        return TYPE_ERROR
    elif node_type == FUNC_T:
        # Function call: (FUNC_T, func_name, RANGE_T, ref1, ref2)
        func_name = node[1]
        ref1 = node[3]
        ref2 = node[4]

        # Validate range endpoints
        if not _is_valid_ref(ref1) or not _is_valid_ref(ref2):
            return REF_ERROR

        col1, row1 = _ref_to_coords(ref1)
        col2, row2 = _ref_to_coords(ref2)

        # Check if range is valid (TL <= BR)
        if col1 > col2 or row1 > row2:
            return REF_ERROR

        # Evaluate the range
        if func_name == COUNT_T:
            return _eval_count(sheet, col1, row1, col2, row2, cycle_set)
        else:
            return _eval_sum_min_max(sheet, func_name, col1, row1, col2, row2, cycle_set)

    # Unary minus
    if node_type == NEG:
        operand = _evaluate_node(node[1], sheet, cycle_set)
        if isinstance(operand, str):
            return operand  # Propagate error
        return -operand

    # Binary operators
    if node_type in {ADD, SUB, MUL, DIV, EQ, NEQ, LT, LTE, GT, GTE}:
        left = _evaluate_node(node[1], sheet, cycle_set)
        # Short-circuit on error
        if isinstance(left, str):
            return left
        right = _evaluate_node(node[2], sheet, cycle_set)
        # Short-circuit on error
        if isinstance(right, str):
            return right

        if node_type == ADD:
            return left + right
        elif node_type == SUB:
            return left - right
        elif node_type == MUL:
            return left * right
        elif node_type == DIV:
            if right == 0:
                return DIV_ERROR
            # Truncate toward zero
            return int(left / right)
        elif node_type == EQ:
            return 1 if left == right else 0
        elif node_type == NEQ:
            return 1 if left != right else 0
        elif node_type == LT:
            return 1 if left < right else 0
        elif node_type == LTE:
            return 1 if left <= right else 0
        elif node_type == GT:
            return 1 if left > right else 0
        elif node_type == GTE:
            return 1 if left >= right else 0

    return PARSE_ERROR


def _eval_sum_min_max(sheet: Sheet, func_name: str, col1: int, row1: int, col2: int, row2: int, cycle_set: set) -> object:
    """Evaluate SUM/MIN/MAX over a range."""
    has_numeric = False
    first_numeric = None

    # Iterate row-major: row by row, column by column
    for r in range(row1, row2 + 1):
        for c in range(col1, col2 + 1):
            ref = _coords_to_ref(c, r)

            # Check for cycles
            if cycle_set is not None and ref in cycle_set:
                return CYCLE_ERROR

            raw = sheet.get(ref, cycle_set)
            if raw is None:
                # Empty cell: skip for SUM/MIN/MAX
                continue

            if isinstance(raw, str):
                # String cell: #TYPE! for SUM/MIN/MAX
                return TYPE_ERROR

            if isinstance(raw, int):
                # Numeric cell
                if not has_numeric:
                    has_numeric = True
                    first_numeric = raw
                else:
                    if func_name == SUM_T:
                        first_numeric += raw
                    elif func_name == MIN_T:
                        if raw < first_numeric:
                            first_numeric = raw
                    elif func_name == MAX_T:
                        if raw > first_numeric:
                            first_numeric = raw

    if not has_numeric:
        # All empty range
        if func_name == SUM_T:
            return 0
        else:  # MIN_T or MAX_T
            return TYPE_ERROR

    return first_numeric


def _eval_count(sheet: Sheet, col1: int, row1: int, col2: int, row2: int, cycle_set: set) -> int:
    """Evaluate COUNT over a range. Counts non-empty cells without evaluating them."""
    count = 0

    # Iterate row-major
    for r in range(row1, row2 + 1):
        for c in range(col1, col2 + 1):
            ref = _coords_to_ref(c, r)

            # COUNT does not participate in cycle detection and does not evaluate
            # Formula cells. Per R8: "COUNT is purely structural: it returns the
            # number of non-empty cells (number, string, and formula cells all
            # count) without evaluating anything"
            # Check _data directly to avoid triggering formula evaluation
            raw = sheet._data.get(ref)
            if raw is not None:
                # Non-empty cell (number, string, or formula)
                count += 1

    return count


def evaluate_formula(formula_text: str, sheet: Sheet, cycle_set: set = None) -> object:
    """Evaluate a formula string (with leading =) on a sheet.

    Returns the computed value (int) or an error string.
    """
    if not formula_text.startswith("="):
        return PARSE_ERROR

    # Parse the formula (without the leading =)
    parsed = parse(formula_text[1:])
    if parsed == PARSE_ERROR:
        return PARSE_ERROR

    # Evaluate the AST
    return _evaluate_node(parsed, sheet, cycle_set)
