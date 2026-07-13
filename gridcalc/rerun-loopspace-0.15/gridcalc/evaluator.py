"""Formula evaluator — evaluates parsed AST with reference resolution."""
import sys

from gridcalc.parser import (
    parse, ParseError, INT, REF, ADD, SUB, MUL, DIV, NEG,
    LT, LTE, GT, GTE, EQ, NEQ,
    FUNC_SUM, FUNC_MIN, FUNC_MAX, FUNC_COUNT,
)

# R12: 256-cell reference chain requires deep recursion.
# Set recursion limit to handle worst case (256 cells * ~4 frames/cell = 1024)
# plus parser recursion overhead.
sys.setrecursionlimit(2000)


# Error markers per R5
ERROR_PARSE = "#PARSE!"
ERROR_REF = "#REF!"
ERROR_TYPE = "#TYPE!"
ERROR_DIV = "#DIV!"
ERROR_CYCLE = "#CYCLE!"


def evaluate(ast, sheet, _evaluating=None):
    """Evaluate a parsed formula AST against a Sheet.

    Args:
        ast: Parsed AST tuple from parser.parse()
        sheet: Sheet instance to resolve references
        _evaluating: Set of addresses currently being evaluated (for cycle detection)

    Returns:
        int or error string (#PARSE!, #REF!, #TYPE!, #DIV!, #CYCLE!)
    """
    try:
        if _evaluating is None:
            _evaluating = set()
        return _eval_node(ast, sheet, _evaluating)
    except ParseError:
        return ERROR_PARSE
    except ZeroDivisionError:
        return ERROR_DIV


class CycleError(Exception):
    """Raised when a circular reference is detected."""
    pass


def _eval_node(node, sheet, _evaluating):
    """Recursively evaluate an AST node."""
    if node is None:
        raise ValueError("None node")

    node_type = node[0]

    # Integer literal
    if node_type == INT:
        return node[1]

    # Reference
    if node_type == REF:
        return _eval_reference(node[1], sheet, _evaluating)

    # Unary negation
    if node_type == NEG:
        return -_eval_node(node[1], sheet, _evaluating)

    # Binary operations
    if node_type in (ADD, SUB, MUL, DIV, LT, LTE, GT, GTE, EQ, NEQ):
        left = _eval_node(node[1], sheet, _evaluating)
        right = _eval_node(node[2], sheet, _evaluating)

        # Error propagation: if either operand is an error, return it
        if isinstance(left, str):
            return left
        if isinstance(right, str):
            return right

        # Arithmetic operations
        if node_type == ADD:
            return left + right
        elif node_type == SUB:
            return left - right
        elif node_type == MUL:
            return left * right
        elif node_type == DIV:
            if right == 0:
                raise ZeroDivisionError
            # Truncate toward zero (Python's // floors, so use int division)
            return int(left / right)

        # Comparison operations — yield 1/0 ints
        if node_type == LT:
            return 1 if left < right else 0
        elif node_type == LTE:
            return 1 if left <= right else 0
        elif node_type == GT:
            return 1 if left > right else 0
        elif node_type == GTE:
            return 1 if left >= right else 0
        elif node_type == EQ:
            return 1 if left == right else 0
        elif node_type == NEQ:
            return 1 if left != right else 0

    # Function calls
    if node_type in (FUNC_SUM, FUNC_MIN, FUNC_MAX, FUNC_COUNT):
        return _eval_function(node_type, node[1], sheet, _evaluating)

    raise ValueError(f"Unknown node type: {node_type}")


def _eval_reference(addr, sheet, _evaluating):
    """Evaluate a reference token against the sheet.

    Args:
        addr: Address string (e.g. "A1")
        sheet: Sheet instance
        _evaluating: Set of addresses currently being evaluated (for cycle detection)

    Returns:
        Value from sheet (int, str, or error string)
    """
    # Validate address format (per R6: leading zeros or out-of-range rows denote no grid cell)
    if not _is_valid_grid_address(addr):
        return ERROR_REF

    # Check for cycle
    if addr in _evaluating:
        return ERROR_CYCLE

    # Add to evaluating set
    _evaluating.add(addr)
    try:
        # Use sheet._evaluate_cell for all cells to properly handle dirty propagation
        # This will cache literals and remove them from dirty set
        value = sheet._store.get(addr)

        # Empty cell contributes 0
        if value is None:
            sheet._dirty.discard(addr)
            return 0

        # Error strings propagate as-is (per R5)
        if isinstance(value, str) and value in (ERROR_PARSE, ERROR_REF, ERROR_TYPE, ERROR_DIV):
            sheet._dirty.discard(addr)
            return value

        # Formula cell: evaluate it through sheet._evaluate_cell
        if isinstance(value, str) and value.startswith("="):
            result = sheet._evaluate_cell(addr)
            return result

        # String cell yields #TYPE! in numeric context
        if isinstance(value, str):
            sheet._dirty.discard(addr)
            return ERROR_TYPE

        # Number cell: return as-is, but clean up dirty set
        if isinstance(value, int):
            sheet._dirty.discard(addr)
            return value

        # Fallback (should not reach here given R2 type restrictions)
        sheet._dirty.discard(addr)
        return ERROR_TYPE
    finally:
        _evaluating.discard(addr)


def _is_valid_grid_address(addr):
    """Check if an address denotes a valid grid cell (per R6).

    Valid: one uppercase A-Z letter followed by digits 1-99 (no leading zeros).
    """
    import re
    pattern = re.compile(r"^[A-Z](?:[1-9][0-9]?)$")
    return bool(pattern.match(addr))


def _eval_function(func_name, range_spec, sheet, _evaluating):
    """Evaluate a function call over a range.

    Args:
        func_name: Function name (FUNC_SUM, FUNC_MIN, FUNC_MAX, FUNC_COUNT)
        range_spec: Tuple of (start_addr, end_addr)
        sheet: Sheet instance
        _evaluating: Set of addresses currently being evaluated (for cycle detection)

    Returns:
        Result of the function (int or error string)
    """
    start_col, start_row = _parse_address(range_spec[0])
    end_col, end_row = _parse_address(range_spec[1])

    # Validate range addresses
    if start_col is None or end_col is None:
        return ERROR_REF

    # Validate range order (start must be <= end)
    if (start_col, start_row) > (end_col, end_row):
        return ERROR_REF

    # Iterate range in row-major order
    numeric_values = []
    non_empty_count = 0
    has_error = None

    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            addr = _col_to_addr(col) + str(row)

            # Get raw value without evaluation (for COUNT)
            raw_value = sheet._store.get(addr)

            # Empty cell
            if raw_value is None:
                continue

            # Non-empty cell — count it for COUNT
            non_empty_count += 1

            # For COUNT, we don't need to evaluate — just count
            if func_name == FUNC_COUNT:
                continue

            # Formula cell — evaluate it through _eval_reference for cycle detection
            if isinstance(raw_value, str) and raw_value.startswith("="):
                # Route through _eval_reference so cycle detection works for range cells
                result = _eval_reference(addr, sheet, _evaluating)
                if isinstance(result, str):
                    # Short-circuit: return first error immediately
                    return result
                numeric_values.append(result)
                continue

            # Error cell
            if isinstance(raw_value, str) and raw_value in (ERROR_PARSE, ERROR_REF, ERROR_TYPE, ERROR_DIV):
                # Short-circuit: return first error immediately
                return raw_value

            # String cell (non-numeric)
            if isinstance(raw_value, str):
                # Short-circuit: return #TYPE! immediately
                return ERROR_TYPE

            # Number cell
            if isinstance(raw_value, int):
                numeric_values.append(raw_value)

    # Function-specific logic
    if func_name == FUNC_SUM:
        return sum(numeric_values)

    elif func_name == FUNC_MIN:
        if not numeric_values:
            return ERROR_TYPE  # All empty: #TYPE!
        return min(numeric_values)

    elif func_name == FUNC_MAX:
        if not numeric_values:
            return ERROR_TYPE  # All empty: #TYPE!
        return max(numeric_values)

    elif func_name == FUNC_COUNT:
        return non_empty_count

    return ERROR_TYPE


def _parse_address(addr):
    """Parse an address string into (col_index, row_index).

    Args:
        addr: Address string (e.g., "A1", "B2")

    Returns:
        Tuple of (col_index, row_index) or (None, None) if invalid
    """
    import re
    match = re.match(r"^([A-Z])([1-9][0-9]?)$", addr)
    if not match:
        return None, None
    col = ord(match.group(1)) - ord('A')
    row = int(match.group(2))
    return col, row


def _col_to_addr(col):
    """Convert a column index to a letter.

    Args:
        col: Column index (0 = A, 1 = B, etc.)

    Returns:
        Column letter
    """
    return chr(ord('A') + col)
