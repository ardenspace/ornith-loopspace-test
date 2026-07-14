import re

from gridcalc.parser import (
    BinaryOp,
    FuncCall,
    Group,
    IntLiteral,
    PARSE_ERROR,
    Range,
    Ref,
    UnaryOp,
    parse,
)

_ADDRESS_RE = re.compile(r"^[A-Z][1-9][0-9]?$")
_MAX_FORMULA_CHAIN = 256
_MAGNITUDE_BOUND = 2**63 - 1
_CHAIN_ERROR = "#CHAIN!"
_OVF_ERROR = "#OVF!"


def _parse_address(addr):
    if not _ADDRESS_RE.match(addr):
        return None
    col = ord(addr[0]) - ord("A")
    row = int(addr[1:])
    return col, row


def _iter_range_cells(start_addr, end_addr):
    start_col, start_row = _parse_address(start_addr)
    end_col, end_row = _parse_address(end_addr)
    for r in range(start_row, end_row + 1):
        for c in range(start_col, end_col + 1):
            yield chr(ord("A") + c) + str(r)


def evaluate(sheet, addr, _visited=None):
    if _visited is None:
        _visited = set()

    if addr in _visited:
        return "#CYCLE!"

    if addr in sheet._cache:
        return sheet._cache[addr]

    stored = sheet._data.get(addr)

    if stored is None:
        result = 0
    elif isinstance(stored, str) and stored.startswith("="):
        sheet._eval_count += 1
        if len(_visited) >= _MAX_FORMULA_CHAIN:
            return _CHAIN_ERROR
        _visited = _visited | {addr}
        ast = parse(stored)
        if ast is PARSE_ERROR:
            result = PARSE_ERROR
        else:
            result = _eval_node(sheet, ast, _visited)
        sheet._cache[addr] = result
        return result
    elif isinstance(stored, int):
        result = stored
    elif isinstance(stored, str):
        result = "#TYPE!"
    else:
        result = stored

    return result


def _check_magnitude(value):
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > _MAGNITUDE_BOUND:
            return _OVF_ERROR
    return value


def _eval_node(sheet, node, visited):
    if isinstance(node, IntLiteral):
        return node.value

    if isinstance(node, Ref):
        if not _ADDRESS_RE.match(node.name):
            return "#REF!"
        return evaluate(sheet, node.name, visited)

    if isinstance(node, UnaryOp):
        operand = _eval_node(sheet, node.operand, visited)
        if isinstance(operand, str):
            return operand
        if node.op == "-":
            result = -operand
            return _check_magnitude(result)
        raise ValueError(f"unknown unary op {node.op!r}")

    if isinstance(node, BinaryOp):
        left = _eval_node(sheet, node.left, visited)
        if isinstance(left, str):
            return left
        right = _eval_node(sheet, node.right, visited)
        if isinstance(right, str):
            return right
        result = _eval_binary(left, right, node.op)
        return _check_magnitude(result)

    if isinstance(node, Group):
        return _eval_node(sheet, node.expr, visited)

    if isinstance(node, Range):
        start_ok = _parse_address(node.start.name)
        end_ok = _parse_address(node.end.name)
        if start_ok is None or end_ok is None:
            return "#REF!"
        start_col, start_row = start_ok
        end_col, end_row = end_ok
        if start_col > end_col or start_row > end_row:
            return "#REF!"
        return _eval_range(sheet, node, visited)

    if isinstance(node, FuncCall):
        return _eval_func(sheet, node, visited)

    raise ValueError(f"unknown node {type(node).__name__}")


def _eval_binary(left, right, op):
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        if right == 0:
            return "#DIV!"
        sign = -1 if (left < 0) ^ (right < 0) else 1
        return sign * (abs(left) // abs(right))
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
    raise ValueError(f"unknown binary op {op!r}")


def _eval_range(sheet, node, visited):
    cells = list(_iter_range_cells(node.start.name, node.end.name))
    values = []
    for addr in cells:
        if addr in visited:
            values.append((addr, None))
        else:
            val = evaluate(sheet, addr, visited)
            values.append((addr, val))
    return values


def _eval_func(sheet, node, visited):
    if node.name == "SUM":
        return _eval_sum(sheet, node, visited)
    if node.name == "MIN":
        return _eval_min(sheet, node, visited)
    if node.name == "MAX":
        return _eval_max(sheet, node, visited)
    if node.name == "COUNT":
        return _eval_count(sheet, node, visited)
    raise ValueError(f"unknown function {node.name!r}")


def _is_error(val):
    return isinstance(val, str) and val in ("#TYPE!", "#REF!", "#DIV!", "#PARSE!", "#CYCLE!")


def _is_numeric(val):
    return isinstance(val, int) and not isinstance(val, bool)


def _is_cell_empty(sheet, addr):
    return addr not in sheet._data


def _validate_range(range_node):
    start_ok = _parse_address(range_node.start.name)
    end_ok = _parse_address(range_node.end.name)
    if start_ok is None or end_ok is None:
        return False
    start_col, start_row = start_ok
    end_col, end_row = end_ok
    if start_col > end_col or start_row > end_row:
        return False
    return True


def _eval_sum(sheet, node, visited):
    if not _validate_range(node.arg):
        return "#REF!"
    cells = list(_iter_range_cells(node.arg.start.name, node.arg.end.name))
    total = 0
    for addr in cells:
        if addr in visited:
            return "#CYCLE!"
        if _is_cell_empty(sheet, addr):
            continue
        val = evaluate(sheet, addr, visited)
        if _is_error(val):
            return val
        if not _is_numeric(val):
            return "#TYPE!"
        total += val
    return total


def _eval_min(sheet, node, visited):
    if not _validate_range(node.arg):
        return "#REF!"
    cells = list(_iter_range_cells(node.arg.start.name, node.arg.end.name))
    min_val = None
    for addr in cells:
        if addr in visited:
            return "#CYCLE!"
        if _is_cell_empty(sheet, addr):
            continue
        val = evaluate(sheet, addr, visited)
        if _is_error(val):
            return val
        if not _is_numeric(val):
            return "#TYPE!"
        if min_val is None or val < min_val:
            min_val = val
    if min_val is None:
        return "#TYPE!"
    return min_val


def _eval_max(sheet, node, visited):
    if not _validate_range(node.arg):
        return "#REF!"
    cells = list(_iter_range_cells(node.arg.start.name, node.arg.end.name))
    max_val = None
    for addr in cells:
        if addr in visited:
            return "#CYCLE!"
        if _is_cell_empty(sheet, addr):
            continue
        val = evaluate(sheet, addr, visited)
        if _is_error(val):
            return val
        if not _is_numeric(val):
            return "#TYPE!"
        if max_val is None or val > max_val:
            max_val = val
    if max_val is None:
        return "#TYPE!"
    return max_val


def _eval_count(sheet, node, visited):
    if not _validate_range(node.arg):
        return "#REF!"
    cells = list(_iter_range_cells(node.arg.start.name, node.arg.end.name))
    count = 0
    for addr in cells:
        if _is_cell_empty(sheet, addr):
            continue
        count += 1
    return count
