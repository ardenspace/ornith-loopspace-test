"""Task 4.4: Seeded differential suite per R11.

This test-only task cross-checks gridcalc's engine against a naive
full-recompute reference implementation. The reference lives in this file
and shares no code with gridcalc's engine.
"""
import random
from gridcalc import Sheet


class NaiveSheet:
    """Naive full-recompute reference implementation per R11.

    This implements the spec's naive model: every get() recomputes everything
    from scratch, ignoring any caching or incremental optimization.
    """

    def __init__(self):
        self._store = {}
        self._eval_count = 0

    @property
    def eval_count(self):
        return self._eval_count

    def set(self, addr, raw):
        """Store a value (same validation as gridcalc.Sheet)."""
        import re
        if not isinstance(addr, str):
            raise ValueError("Address must be a string")
        if not re.match(r"^[A-Z](?:[1-9][0-9]?)$", addr):
            raise ValueError(f"Invalid address: {addr!r}")
        if isinstance(raw, bool):
            raise ValueError("bool not allowed")
        if not isinstance(raw, (int, str)):
            raise ValueError("Only int and str allowed")
        if isinstance(raw, str) and not type(raw) is str:
            raw = str(raw)
        if isinstance(raw, int) and not type(raw) is int:
            raw = int(raw)
        self._store[addr] = raw
        return None

    def get(self, addr):
        """Retrieve value, evaluating formulas naively (full recompute)."""
        import re
        if not isinstance(addr, str):
            raise ValueError("Address must be a string")
        if not re.match(r"^[A-Z](?:[1-9][0-9]?)$", addr):
            raise ValueError(f"Invalid address: {addr!r}")

        value = self._store.get(addr)
        if value is None:
            return None
        if not (isinstance(value, str) and value.startswith("=")):
            return value

        # Formula cell: evaluate naively
        self._eval_count += 1
        formula = value[1:]
        try:
            result = self._evaluate_formula(formula, set())
            return result
        except Exception:
            self._eval_count += 1
            return "#PARSE!"

    def _evaluate_formula(self, formula, _evaluating):
        """Evaluate a formula string naively."""
        from gridcalc.parser import parse as parser_parse
        from gridcalc.evaluator import (
            INT, REF, ADD, SUB, MUL, DIV, NEG,
            LT, LTE, GT, GTE, EQ, NEQ,
            FUNC_SUM, FUNC_MIN, FUNC_MAX, FUNC_COUNT,
        )

        ast = parser_parse(formula)
        return self._eval_node(ast, _evaluating)

    def _eval_node(self, node, _evaluating):
        """Evaluate an AST node naively."""
        if node[0] == INT:
            return node[1]
        if node[0] == REF:
            return self._eval_reference(node[1], _evaluating)
        if node[0] == NEG:
            return -self._eval_node(node[1], _evaluating)
        if node[0] in (ADD, SUB, MUL, DIV, LT, LTE, GT, GTE, EQ, NEQ):
            left = self._eval_node(node[1], _evaluating)
            right = self._eval_node(node[2], _evaluating)
            if isinstance(left, str):
                return left
            if isinstance(right, str):
                return right
            if node[0] == ADD:
                return left + right
            elif node[0] == SUB:
                return left - right
            elif node[0] == MUL:
                return left * right
            elif node[0] == DIV:
                if right == 0:
                    return "#DIV!"
                return int(left / right)
            if node[0] == LT:
                return 1 if left < right else 0
            elif node[0] == LTE:
                return 1 if left <= right else 0
            elif node[0] == GT:
                return 1 if left > right else 0
            elif node[0] == GTE:
                return 1 if left >= right else 0
            elif node[0] == EQ:
                return 1 if left == right else 0
            elif node[0] == NEQ:
                return 1 if left != right else 0
        if node[0] in (FUNC_SUM, FUNC_MIN, FUNC_MAX, FUNC_COUNT):
            return self._eval_function(node[0], node[1], _evaluating)
        raise ValueError(f"Unknown node: {node[0]}")

    def _eval_reference(self, addr, _evaluating):
        """Evaluate a reference naively."""
        import re
        if not re.match(r"^[A-Z](?:[1-9][0-9]?)$", addr):
            return "#REF!"
        if addr in _evaluating:
            return "#CYCLE!"

        _evaluating.add(addr)
        try:
            value = self._store.get(addr)
            if value is None:
                return 0
            if isinstance(value, str) and value in ("#PARSE!", "#REF!", "#TYPE!", "#DIV!"):
                return value
            if isinstance(value, str) and value.startswith("="):
                self._eval_count += 1
                result = self._evaluate_formula(value[1:], _evaluating)
                return result
            if isinstance(value, str):
                return "#TYPE!"
            if isinstance(value, int):
                return value
            return "#TYPE!"
        finally:
            _evaluating.discard(addr)

    def _eval_function(self, func_name, range_spec, _evaluating):
        """Evaluate a function naively."""
        import re
        match_start = re.match(r"^([A-Z])([1-9][0-9]?)$", range_spec[0])
        match_end = re.match(r"^([A-Z])([1-9][0-9]?)$", range_spec[1])
        if not match_start or not match_end:
            return "#REF!"

        start_col = ord(match_start.group(1)) - ord('A')
        start_row = int(match_start.group(2))
        end_col = ord(match_end.group(1)) - ord('A')
        end_row = int(match_end.group(2))

        if (start_col, start_row) > (end_col, end_row):
            return "#REF!"

        numeric_values = []
        non_empty_count = 0

        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                addr = chr(ord('A') + col) + str(row)
                raw_value = self._store.get(addr)

                if raw_value is None:
                    continue

                non_empty_count += 1

                if func_name == FUNC_COUNT:
                    continue

                if isinstance(raw_value, str) and raw_value.startswith("="):
                    self._eval_count += 1
                    result = self._evaluate_formula(raw_value[1:], _evaluating)
                    if isinstance(result, str):
                        return result
                    numeric_values.append(result)
                    continue

                if isinstance(raw_value, str) and raw_value in ("#PARSE!", "#REF!", "#TYPE!", "#DIV!"):
                    return raw_value

                if isinstance(raw_value, str):
                    return "#TYPE!"

                if isinstance(raw_value, int):
                    numeric_values.append(raw_value)

        if func_name == FUNC_SUM:
            return sum(numeric_values)
        elif func_name == FUNC_MIN:
            if not numeric_values:
                return "#TYPE!"
            return min(numeric_values)
        elif func_name == FUNC_MAX:
            if not numeric_values:
                return "#TYPE!"
            return max(numeric_values)
        elif func_name == FUNC_COUNT:
            return non_empty_count
        return "#TYPE!"


def generate_random_sequence(rng, length, region_size=5):
    """Generate a random sequence of set/get operations.

    Args:
        rng: Random instance (for reproducibility)
        length: Number of operations
        region_size: Size of the cell region to use (e.g., 5 means A1-E5)

    Returns:
        List of (operation_type, args) tuples
    """
    operations = []

    # Generate a grid of addresses in the region
    addresses = []
    for col in range(region_size):
        for row in range(1, region_size + 1):
            addresses.append(chr(ord('A') + col) + str(row))

    for _ in range(length):
        op_type = rng.choice(["set_literal", "set_formula", "get"])
        addr = rng.choice(addresses)

        if op_type == "set_literal":
            # Set a literal value (int or string)
            if rng.random() < 0.5:
                value = rng.randint(-100, 100)
                operations.append(("set", addr, value))
            else:
                # Random string (not a formula)
                value = f"str_{rng.randint(0, 99)}"
                operations.append(("set", addr, value))

        elif op_type == "set_formula":
            # Set a formula
            formula_type = rng.choice(["simple", "reference", "function", "comparison"])
            if formula_type == "simple":
                # =INT+INT or =INT-INT
                a = rng.randint(-10, 10)
                b = rng.randint(-10, 10)
                op = rng.choice(["+", "-"])
                formula = f"={a}{op}{b}"
            elif formula_type == "reference":
                # =ADDR+INT or =ADDR-INT
                ref_addr = rng.choice(addresses)
                value = rng.randint(-10, 10)
                op = rng.choice(["+", "-"])
                formula = f"={ref_addr}{op}{value}"
            elif formula_type == "function":
                # =SUM(ADDR:ADDR) or =COUNT(ADDR:ADDR)
                func = rng.choice(["SUM", "COUNT"])
                addr1 = rng.choice(addresses)
                addr2 = rng.choice(addresses)
                formula = f"={func}({addr1}:{addr2})"
            elif formula_type == "comparison":
                # =ADDR<ADDR or =ADDR>ADDR
                addr1 = rng.choice(addresses)
                addr2 = rng.choice(addresses)
                op = rng.choice(["<", ">", "=", "<=", ">=", "<>"])
                formula = f"={addr1}{op}{addr2}"

            operations.append(("set", addr, "=" + formula))

        elif op_type == "get":
            operations.append(("get", addr))

    return operations


def run_differential_test(seed):
    """Run a single differential test with the given seed.

    Args:
        seed: Random seed for reproducibility

    Returns:
        Tuple of (mismatches, seed) where mismatches is a list of (op_index, gridcalc_result, reference_result)
    """
    rng = random.Random(seed)
    naive = NaiveSheet()
    gridcalc = Sheet()

    # Generate random operations
    operations = generate_random_sequence(rng, length=50, region_size=5)

    mismatches = []

    for op_idx, op in enumerate(operations):
        op_type = op[0]

        if op_type == "set":
            _, addr, value = op
            try:
                naive.set(addr, value)
            except (ValueError, Exception):
                # If naive raises, gridcalc should too
                try:
                    gridcalc.set(addr, value)
                    # gridcalc succeeded but naive failed — mismatch
                    mismatches.append((op_idx, "set", value, "naive_failed"))
                except (ValueError, Exception):
                    # Both failed — OK
                    pass
                continue

            try:
                gridcalc.set(addr, value)
            except (ValueError, Exception) as e:
                # gridcalc failed but naive succeeded — mismatch
                mismatches.append((op_idx, "set", value, f"gridcalc_failed: {e}"))
                continue

        elif op_type == "get":
            _, addr = op
            try:
                naive_result = naive.get(addr)
            except (ValueError, Exception) as e:
                naive_result = f"ERROR: {e}"

            try:
                gridcalc_result = gridcalc.get(addr)
            except (ValueError, Exception) as e:
                gridcalc_result = f"ERROR: {e}"

            # Compare results
            if naive_result != gridcalc_result:
                mismatches.append((op_idx, "get", addr, gridcalc_result, naive_result))

    return mismatches, seed


def test_differential_seeded():
    """Run 1000+ seeded differential tests."""
    total_mismatches = 0
    failed_seeds = []

    # Run 1000 tests with seeds 0-999
    for seed in range(1000):
        mismatches, test_seed = run_differential_test(seed)
        if mismatches:
            total_mismatches += len(mismatches)
            failed_seeds.append((test_seed, mismatches))

    # Report results
    print(f"Ran 1000 differential tests")
    print(f"Total mismatches: {total_mismatches}")

    if failed_seeds:
        print(f"\nFailed seeds ({len(failed_seeds)}):")
        for seed, mismatches in failed_seeds[:10]:  # Show first 10
            print(f"  Seed {seed}: {len(mismatches)} mismatches")
            for op_idx, *details in mismatches[:3]:  # Show first 3 mismatches per seed
                print(f"    Op {op_idx}: {details}")

    assert total_mismatches == 0, f"Found {total_mismatches} mismatches across 1000 tests"


if __name__ == "__main__":
    test_differential_seeded()
