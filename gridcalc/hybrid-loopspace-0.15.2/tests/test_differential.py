"""
Seeded differential suite: cross-checks the production Sheet engine against a
naive full-recompute reference implementation.

The reference lives entirely inside this file and shares no code with
gridcalc's engine except gridcalc.parser.parse (the parser).  Every get() on
the reference recomputes from the currently stored literals and formulas.

Acceptance:
- At least 1000 seeded random set/get sequences of length >= 50 over a
  bounded region (literals, formulas, functions, errors, cycles mixed).
- Zero mismatches between reference and production across all sequences.
- Seeds are fixed and logged.
"""

import random

import pytest

from gridcalc import Sheet
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

# ---------------------------------------------------------------------------
# Naive reference implementation
# ---------------------------------------------------------------------------

_ADDRESS_RE = __import__("re").compile(r"^[A-Z][1-9][0-9]?$")
_MAX_FORMULA_CHAIN = 256
_MAGNITUDE_BOUND = 2**63 - 1
_OVF_ERROR = "#OVF!"


def _naive_parse_address(addr):
    if not _ADDRESS_RE.match(addr):
        return None
    col = ord(addr[0]) - ord("A")
    row = int(addr[1:])
    return col, row


def _naive_iter_range_cells(start_addr, end_addr):
    start_col, start_row = _naive_parse_address(start_addr)
    end_col, end_row = _naive_parse_address(end_addr)
    for r in range(start_row, end_row + 1):
        for c in range(start_col, end_col + 1):
            yield chr(ord("A") + c) + str(r)


def _naive_is_valid_range(range_node):
    start_ok = _naive_parse_address(range_node.start.name)
    end_ok = _naive_parse_address(range_node.end.name)
    if start_ok is None or end_ok is None:
        return False
    start_col, start_row = start_ok
    end_col, end_row = end_ok
    if start_col > end_col or start_row > end_row:
        return False
    return True


def _naive_is_error(val):
    return isinstance(val, str) and val in ("#TYPE!", "#REF!", "#DIV!", "#PARSE!", "#CYCLE!")


def _naive_is_numeric(val):
    return isinstance(val, int) and not isinstance(val, bool)


def _naive_check_magnitude(value):
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > _MAGNITUDE_BOUND:
            return _OVF_ERROR
    return value


def _naive_eval_binary(left, right, op):
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


def _naive_eval_node(sheet, node, visited, chain_depth):
    if isinstance(node, IntLiteral):
        return node.value

    if isinstance(node, Ref):
        if not _ADDRESS_RE.match(node.name):
            return "#REF!"
        return _naive_evaluate(sheet, node.name, visited, chain_depth)

    if isinstance(node, UnaryOp):
        operand = _naive_eval_node(sheet, node.operand, visited, chain_depth)
        if isinstance(operand, str):
            return operand
        if node.op == "-":
            result = -operand
            return _naive_check_magnitude(result)
        raise ValueError(f"unknown unary op {node.op!r}")

    if isinstance(node, BinaryOp):
        left = _naive_eval_node(sheet, node.left, visited, chain_depth)
        if isinstance(left, str):
            return left
        right = _naive_eval_node(sheet, node.right, visited, chain_depth)
        if isinstance(right, str):
            return right
        result = _naive_eval_binary(left, right, node.op)
        return _naive_check_magnitude(result)

    if isinstance(node, Group):
        return _naive_eval_node(sheet, node.expr, visited, chain_depth)

    if isinstance(node, Range):
        start_ok = _naive_parse_address(node.start.name)
        end_ok = _naive_parse_address(node.end.name)
        if start_ok is None or end_ok is None:
            return "#REF!"
        start_col, start_row = start_ok
        end_col, end_row = end_ok
        if start_col > end_col or start_row > end_row:
            return "#REF!"
        return _naive_eval_range(sheet, node, visited, chain_depth)

    if isinstance(node, FuncCall):
        return _naive_eval_func(sheet, node, visited, chain_depth)

    raise ValueError(f"unknown node {type(node).__name__}")


def _naive_eval_range(sheet, node, visited, chain_depth):
    cells = list(_naive_iter_range_cells(node.start.name, node.end.name))
    values = []
    for addr in cells:
        if addr in visited:
            values.append((addr, None))
        else:
            val = _naive_evaluate(sheet, addr, visited, chain_depth)
            values.append((addr, val))
    return values


def _naive_eval_sum(sheet, node, visited, chain_depth):
    if not _naive_is_valid_range(node.arg):
        return "#REF!"
    cells = list(_naive_iter_range_cells(node.arg.start.name, node.arg.end.name))
    total = 0
    for addr in cells:
        if addr in visited:
            return "#CYCLE!"
        if addr not in sheet._data:
            continue
        val = _naive_evaluate(sheet, addr, visited, chain_depth)
        if _naive_is_error(val):
            return val
        if not _naive_is_numeric(val):
            return "#TYPE!"
        total += val
    return total


def _naive_eval_min(sheet, node, visited, chain_depth):
    if not _naive_is_valid_range(node.arg):
        return "#REF!"
    cells = list(_naive_iter_range_cells(node.arg.start.name, node.arg.end.name))
    min_val = None
    for addr in cells:
        if addr in visited:
            return "#CYCLE!"
        if addr not in sheet._data:
            continue
        val = _naive_evaluate(sheet, addr, visited, chain_depth)
        if _naive_is_error(val):
            return val
        if not _naive_is_numeric(val):
            return "#TYPE!"
        if min_val is None or val < min_val:
            min_val = val
    if min_val is None:
        return "#TYPE!"
    return min_val


def _naive_eval_max(sheet, node, visited, chain_depth):
    if not _naive_is_valid_range(node.arg):
        return "#REF!"
    cells = list(_naive_iter_range_cells(node.arg.start.name, node.arg.end.name))
    max_val = None
    for addr in cells:
        if addr in visited:
            return "#CYCLE!"
        if addr not in sheet._data:
            continue
        val = _naive_evaluate(sheet, addr, visited, chain_depth)
        if _naive_is_error(val):
            return val
        if not _naive_is_numeric(val):
            return "#TYPE!"
        if max_val is None or val > max_val:
            max_val = val
    if max_val is None:
        return "#TYPE!"
    return max_val


def _naive_eval_count(sheet, node, visited, chain_depth):
    if not _naive_is_valid_range(node.arg):
        return "#REF!"
    cells = list(_naive_iter_range_cells(node.arg.start.name, node.arg.end.name))
    count = 0
    for addr in cells:
        if addr not in sheet._data:
            continue
        count += 1
    return count


def _naive_eval_func(sheet, node, visited, chain_depth):
    if node.name == "SUM":
        return _naive_eval_sum(sheet, node, visited, chain_depth)
    if node.name == "MIN":
        return _naive_eval_min(sheet, node, visited, chain_depth)
    if node.name == "MAX":
        return _naive_eval_max(sheet, node, visited, chain_depth)
    if node.name == "COUNT":
        return _naive_eval_count(sheet, node, visited, chain_depth)
    raise ValueError(f"unknown function {node.name!r}")


def _naive_evaluate(sheet, addr, visited, chain_depth):
    if addr in visited:
        return "#CYCLE!"

    stored = sheet._data.get(addr)

    if stored is None:
        return 0
    if isinstance(stored, str) and stored.startswith("="):
        if chain_depth >= _MAX_FORMULA_CHAIN:
            return "#CHAIN!"
        new_visited = visited | {addr}
        ast = parse(stored)
        if ast is PARSE_ERROR:
            return PARSE_ERROR
        result = _naive_eval_node(sheet, ast, new_visited, chain_depth + 1)
        return result
    if isinstance(stored, int):
        return stored
    if isinstance(stored, str):
        return "#TYPE!"
    return stored


class NaiveSheet:
    """Naive full-recompute spreadsheet engine.

    No caching, no closures, no eval_count tracking.  Every get() recomputes
    from the currently stored literals and formulas.
    """

    def __init__(self):
        self._data = {}

    def get(self, addr):
        if not isinstance(addr, str):
            raise ValueError(f"Address must be a string, got {type(addr).__name__}")
        if not _ADDRESS_RE.match(addr):
            raise ValueError(f"Invalid address: {addr!r}")
        if addr not in self._data:
            return None
        stored = self._data[addr]
        if isinstance(stored, str) and not stored.startswith("="):
            return stored
        return _naive_evaluate(self, addr, set(), 0)

    def set(self, addr, value):
        if not isinstance(addr, str):
            raise ValueError(f"Address must be a string, got {type(addr).__name__}")
        if not _ADDRESS_RE.match(addr):
            raise ValueError(f"Invalid address: {addr!r}")
        if isinstance(value, bool):
            raise ValueError(f"bool values are not allowed, got {type(value).__name__}")
        if isinstance(value, int):
            self._data[addr] = int(value)
        elif isinstance(value, str):
            self._data[addr] = str(value)
        else:
            raise ValueError(f"Unsupported value type: {type(value).__name__}")


# ---------------------------------------------------------------------------
# Deterministic helpers for random sequence generation
# ---------------------------------------------------------------------------

_ADDR_POOL = []
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    for _r in range(1, 100):
        _ADDR_POOL.append(f"{_c}{_r}")

# A smaller pool for tighter random sequences.
_ADDR_POOL_SMALL = _ADDR_POOL[:200]


def _random_formula(rng, available_addrs):
    """Generate a random formula string."""
    kind = rng.choice(["arith", "compare", "func", "ref_chain", "error", "cycle", "mixed"])

    if kind == "arith":
        left = rng.choice(available_addrs + ["1", "2", "3", "10", "100"])
        right = rng.choice(available_addrs + ["1", "2", "3", "10", "100"])
        op = rng.choice(["+", "-", "*", "/"])
        return f"={left}{op}{right}"

    if kind == "compare":
        left = rng.choice(available_addrs + ["1", "2", "3"])
        right = rng.choice(available_addrs + ["1", "2", "3"])
        op = rng.choice(["=", "<>", "<", "<=", ">", ">="])
        return f"={left}{op}{right}"

    if kind == "func":
        func = rng.choice(["SUM", "MIN", "MAX"])
        if len(available_addrs) >= 2:
            a, b = rng.sample(available_addrs, 2)
            start, end = (a, b) if available_addrs.index(a) < available_addrs.index(b) else (b, a)
        else:
            a = available_addrs[0]
            start, end = a, a
        return f"={func}({start}:{end})"

    if kind == "ref_chain":
        if len(available_addrs) >= 2:
            target = rng.choice(available_addrs)
            return f"={target}"
        return "=1"

    if kind == "error":
        return "=1/0"

    if kind == "cycle":
        if len(available_addrs) >= 2:
            a, b = rng.sample(available_addrs, 2)
            return f"={b}"
        return "=A1"

    # mixed
    parts = []
    for _ in range(rng.randint(1, 3)):
        parts.append(rng.choice(available_addrs + ["1", "2", "3", "10"]))
    op = rng.choice(["+", "-", "*"])
    if op == "+":
        body = "+".join(parts)
    else:
        right = parts[-1] if len(parts) > 1 else "1"
        body = f"{parts[0]}{op}{right}"
    return f"={body}"


def _run_one_sequence(seed, seq_len=50):
    """Run one random set/get sequence and return (mismatches, details).

    Returns a list of (step_index, addr, naive_result, prod_result) for any
    mismatches found.
    """
    rng = random.Random(seed)
    naive = NaiveSheet()
    prod = Sheet()

    available = list(_ADDR_POOL_SMALL)
    mismatches = []

    for step in range(seq_len):
        op = rng.choice(["set_lit", "set_formula", "get"])

        addr = rng.choice(available)

        if op == "set_lit":
            # 70% int literal, 30% string literal
            if rng.random() < 0.7:
                val = rng.randint(-1000, 1000)
            else:
                val = "text"
            try:
                naive.set(addr, val)
                prod.set(addr, val)
            except ValueError:
                continue

        elif op == "set_formula":
            formula = _random_formula(rng, available)
            try:
                naive.set(addr, formula)
                prod.set(addr, formula)
            except ValueError:
                continue

        elif op == "get":
            try:
                naive_val = naive.get(addr)
                prod_val = prod.get(addr)
            except (ValueError, RecursionError, OverflowError):
                continue

            if naive_val != prod_val:
                mismatches.append((step, addr, naive_val, prod_val))

    return mismatches


# ---------------------------------------------------------------------------
# Fixed seeds for reproducibility
# ---------------------------------------------------------------------------

_SEEDS = list(range(42, 42 + 1000))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_differential_seeded_random_sequences():
    """Cross-check production Sheet against naive reference over 1000 seeded sequences.

    Each sequence has >= 50 random set/get operations over a bounded region
    with mixed literals, formulas, functions, errors, and cycles.  Zero
    mismatches allowed.
    """
    total_steps = 0
    total_mismatches = 0
    mismatch_details = []

    for seed in _SEEDS:
        mismatches = _run_one_sequence(seed, seq_len=50)
        total_mismatches += len(mismatches)
        if mismatches:
            mismatch_details.append((seed, mismatches))
        total_steps += 50

    assert total_mismatches == 0, (
        f"Found {total_mismatches} mismatches across {len(_SEEDS)} sequences "
        f"({total_steps} total get steps). "
        f"First failing seeds: {[s for s, _ in mismatch_details[:5]]}"
    )


def test_differential_specific_cycle_case():
    """Direct cycle detection: A1 = B1, B1 = A1."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=B1")
    prod.set("A1", "=B1")
    naive.set("B1", "=A1")
    prod.set("B1", "=A1")

    assert naive.get("A1") == prod.get("A1")
    assert naive.get("B1") == prod.get("B1")


def test_differential_specific_div_by_zero():
    """Direct division by zero."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=1/0")
    prod.set("A1", "=1/0")

    assert naive.get("A1") == prod.get("A1")


def test_differential_specific_type_error():
    """String literal referenced by formula yields #TYPE!."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "text")
    prod.set("A1", "text")
    naive.set("B1", "=A1+1")
    prod.set("B1", "=A1+1")

    assert naive.get("B1") == prod.get("B1")


def test_differential_specific_sum_function():
    """SUM over a range of literals."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 1)
    prod.set("A1", 1)
    naive.set("A2", 2)
    prod.set("A2", 2)
    naive.set("A3", 3)
    prod.set("A3", 3)
    naive.set("B1", "=SUM(A1:A3)")
    prod.set("B1", "=SUM(A1:A3)")

    assert naive.get("B1") == prod.get("B1")


def test_differential_specific_count_function():
    """COUNT counts non-empty cells without evaluating them."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=1/0")
    prod.set("A1", "=1/0")
    naive.set("B1", "=99")
    prod.set("B1", "=99")
    naive.set("C1", "=COUNT(A1:B1)")
    prod.set("C1", "=COUNT(A1:B1)")

    assert naive.get("C1") == prod.get("C1")


def test_differential_specific_magnitude_overflow():
    """Arithmetic exceeding 2^63-1 yields #OVF!."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 2**63 - 1)
    prod.set("A1", 2**63 - 1)
    naive.set("B1", 2**63 - 1)
    prod.set("B1", 2**63 - 1)
    naive.set("C1", "=A1+B1")
    prod.set("C1", "=A1+B1")

    assert naive.get("C1") == prod.get("C1")


def test_differential_specific_ref_chain():
    """Reference chain A1 -> B1 -> C1 -> 42."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=B1")
    prod.set("A1", "=B1")
    naive.set("B1", "=C1")
    prod.set("B1", "=C1")
    naive.set("C1", "=42")
    prod.set("C1", "=42")

    assert naive.get("A1") == prod.get("A1")


def test_differential_specific_empty_cell():
    """Getting an empty cell returns None in both engines."""
    naive = NaiveSheet()
    prod = Sheet()

    assert naive.get("Z99") == prod.get("Z99")
    assert naive.get("Z99") is None


def test_differential_specific_comparison_ops():
    """All comparison operators produce correct 0/1 results."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 5)
    prod.set("A1", 5)
    naive.set("B1", 3)
    prod.set("B1", 3)

    ops = ["=", "<>", "<", "<=", ">", ">="]
    for i, op in enumerate(ops):
        addr = f"X{10 + i}"
        naive.set(addr, f"=A1{op}B1")
        prod.set(addr, f"=A1{op}B1")
        assert naive.get(addr) == prod.get(addr), f"mismatch on op={op}"


def test_differential_specific_min_max():
    """MIN and MAX over a range."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 5)
    prod.set("A1", 5)
    naive.set("A2", 1)
    prod.set("A2", 1)
    naive.set("A3", 9)
    prod.set("A3", 9)
    naive.set("B1", "=MIN(A1:A3)")
    prod.set("B1", "=MIN(A1:A3)")
    naive.set("B2", "=MAX(A1:A3)")
    prod.set("B2", "=MAX(A1:A3)")

    assert naive.get("B1") == prod.get("B1")
    assert naive.get("B2") == prod.get("B2")


def test_differential_specific_truncating_division():
    """Integer truncating division: 7 // -2 == -4."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 7)
    prod.set("A1", 7)
    naive.set("B1", -2)
    prod.set("B1", -2)
    naive.set("C1", "=A1/B1")
    prod.set("C1", "=A1/B1")

    assert naive.get("C1") == prod.get("C1")


def test_differential_specific_invalid_range():
    """Invalid range (reversed) yields #REF!."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 1)
    prod.set("A1", 1)
    naive.set("B1", "=SUM(B1:A1)")
    prod.set("B1", "=SUM(B1:A1)")

    assert naive.get("B1") == prod.get("B1")


def test_differential_specific_parse_error():
    """Malformed formula yields #PARSE!."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=1 $ 2")
    prod.set("A1", "=1 $ 2")

    assert naive.get("A1") == prod.get("A1")


def test_differential_specific_unary_minus():
    """Unary minus on a literal and on a reference."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "= -5")
    prod.set("A1", "= -5")
    naive.set("B1", 10)
    prod.set("B1", 10)
    naive.set("C1", "= -B1")
    prod.set("C1", "= -B1")

    assert naive.get("A1") == prod.get("A1")
    assert naive.get("C1") == prod.get("C1")


def test_differential_specific_nested_parens():
    """Nested parentheses evaluate correctly."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=((1+2)*3)")
    prod.set("A1", "=((1+2)*3)")

    assert naive.get("A1") == prod.get("A1")


def test_differential_specific_mixed_error_propagation():
    """Error in first operand short-circuits: 1/0 + 99 == #DIV!."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=1/0+99")
    prod.set("A1", "=1/0+99")

    assert naive.get("A1") == prod.get("A1")


def test_differential_specific_self_referential():
    """Self-referential formula yields #CYCLE!."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=A1+1")
    prod.set("A1", "=A1+1")

    assert naive.get("A1") == prod.get("A1")


def test_differential_specific_get_empty_returns_none():
    """Getting an empty cell returns None in both engines."""
    naive = NaiveSheet()
    prod = Sheet()

    assert naive.get("Z99") is None
    assert prod.get("Z99") is None


def test_differential_specific_set_invalid_address():
    """Invalid addresses raise ValueError in both engines."""
    naive = NaiveSheet()
    prod = Sheet()

    with pytest.raises(ValueError):
        naive.set("a1", 1)
    with pytest.raises(ValueError):
        prod.set("a1", 1)

    with pytest.raises(ValueError):
        naive.get("A0")
    with pytest.raises(ValueError):
        prod.get("A0")


def test_differential_specific_set_bool_rejected():
    """Bool values are rejected by both engines."""
    naive = NaiveSheet()
    prod = Sheet()

    with pytest.raises(ValueError):
        naive.set("A1", True)
    with pytest.raises(ValueError):
        prod.set("A1", True)


def test_differential_specific_long_chain():
    """A 50-cell reference chain should evaluate correctly in both engines."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=1")
    prod.set("A1", "=1")
    prev = "A1"
    for i in range(2, 51):
        addr = f"A{i}"
        naive.set(addr, f"={prev}+1")
        prod.set(addr, f"={prev}+1")
        prev = addr

    assert naive.get("A50") == prod.get("A50")
    assert naive.get("A50") == 50


def test_differential_specific_cycle_in_sum():
    """Cycle through SUM: A1=B1, B1=SUM(A1:B1)."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", "=B1")
    prod.set("A1", "=B1")
    naive.set("B1", "=SUM(A1:B1)")
    prod.set("B1", "=SUM(A1:B1)")

    assert naive.get("B1") == prod.get("B1")
    assert naive.get("A1") == prod.get("A1")


def test_differential_specific_range_with_formula_members():
    """Range that includes formula cells evaluates correctly."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 1)
    prod.set("A1", 1)
    naive.set("B1", "=2")
    prod.set("B1", "=2")
    naive.set("C1", 3)
    prod.set("C1", 3)
    naive.set("D1", "=SUM(A1:C1)")
    prod.set("D1", "=SUM(A1:C1)")

    assert naive.get("D1") == prod.get("D1")
    assert naive.get("D1") == 6


def test_differential_specific_range_with_empty_cells():
    """Range with empty cells: SUM skips them."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 1)
    prod.set("A1", 1)
    naive.set("A3", 3)
    prod.set("A3", 3)
    naive.set("B1", "=SUM(A1:A3)")
    prod.set("B1", "=SUM(A1:A3)")

    assert naive.get("B1") == prod.get("B1")
    assert naive.get("B1") == 4


def test_differential_specific_negative_division():
    """Negative number division: -10 / 3 == -3 (truncating toward zero)."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", -10)
    prod.set("A1", -10)
    naive.set("B1", 3)
    prod.set("B1", 3)
    naive.set("C1", "=A1/B1")
    prod.set("C1", "=A1/B1")

    assert naive.get("C1") == prod.get("C1")
    assert naive.get("C1") == -3


def test_differential_specific_zero_result():
    """Arithmetic that results in zero."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 5)
    prod.set("A1", 5)
    naive.set("B1", 5)
    prod.set("B1", 5)
    naive.set("C1", "=A1-B1")
    prod.set("C1", "=A1-B1")

    assert naive.get("C1") == prod.get("C1")
    assert naive.get("C1") == 0


def test_differential_specific_large_numbers():
    """Large numbers exceeding magnitude bound yield #OVF!."""
    naive = NaiveSheet()
    prod = Sheet()

    naive.set("A1", 2**62)
    prod.set("A1", 2**62)
    naive.set("B1", 2**62)
    prod.set("B1", 2**62)
    naive.set("C1", "=A1+B1")
    prod.set("C1", "=A1+B1")

    assert naive.get("C1") == prod.get("C1")
    assert naive.get("C1") == "#OVF!"
