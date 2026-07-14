import re

from gridcalc.evaluator import evaluate
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


def _validate_address(addr):
    if not isinstance(addr, str):
        raise ValueError(f"Address must be a string, got {type(addr).__name__}")
    if not _ADDRESS_RE.match(addr):
        raise ValueError(f"Invalid address: {addr!r}")
    return addr


def _validate_raw(raw):
    if isinstance(raw, bool):
        raise ValueError(f"bool values are not allowed, got {type(raw).__name__}")
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, str):
        return str(raw)
    raise ValueError(f"Unsupported value type: {type(raw).__name__}")


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


def _is_valid_range(range_node):
    start_ok = _parse_address(range_node.start.name)
    end_ok = _parse_address(range_node.end.name)
    if start_ok is None or end_ok is None:
        return False
    start_col, start_row = start_ok
    end_col, end_row = end_ok
    if start_col > end_col or start_row > end_row:
        return False
    return True


def _compute_closure(addr, ast, data, overrides=None, seen=None):
    if ast is PARSE_ERROR:
        return {addr}
    if seen is None:
        seen = set()
    if overrides is None:
        overrides = {}

    seen = seen | {addr}
    closure = {addr}
    for ref_addr in _extract_closure(ast):
        closure.add(ref_addr)
        raw = overrides.get(ref_addr, data.get(ref_addr))
        if ref_addr in seen or not (isinstance(raw, str) and raw.startswith("=")):
            continue
        closure.update(_compute_closure(ref_addr, parse(raw), data, overrides, seen))
    return closure


def _extract_closure(node):
    if isinstance(node, Ref):
        return {node.name}
    if isinstance(node, Range):
        if not _is_valid_range(node):
            return set()
        return set(_iter_range_cells(node.start.name, node.end.name))
    if isinstance(node, FuncCall):
        if not _is_valid_range(node.arg):
            return set()
        return set(_iter_range_cells(node.arg.start.name, node.arg.end.name))
    if isinstance(node, BinaryOp):
        return _extract_closure(node.left) | _extract_closure(node.right)
    if isinstance(node, UnaryOp):
        return _extract_closure(node.operand)
    if isinstance(node, Group):
        return _extract_closure(node.expr)
    return set()


class Sheet:
    def __init__(self):
        self._data = {}
        self._eval_count = 0
        self._cache = {}
        self._closures = {}

    def get(self, addr):
        validated = _validate_address(addr)
        if validated in self._cache:
            return self._cache[validated]
        raw = self._data.get(validated)
        if isinstance(raw, str) and raw.startswith("="):
            result = evaluate(self, validated)
            self._cache[validated] = result
            if isinstance(raw, str) and raw.startswith("="):
                ast = parse(raw)
                self._closures[validated] = _compute_closure(validated, ast, self._data)
            return result
        return raw

    def set(self, addr, value):
        validated = _validate_address(addr)
        normalized = _validate_raw(value)

        new_closure = None
        if isinstance(normalized, str) and normalized.startswith("="):
            ast = parse(normalized)
            new_closure = _compute_closure(
                validated, ast, self._data, overrides={validated: normalized}
            )

        affected = []
        for cached_addr, cached_closure in self._closures.items():
            if cached_addr == validated:
                affected.append(cached_addr)
            elif validated in cached_closure:
                affected.append(cached_addr)

        for affected_addr in affected:
            self._cache.pop(affected_addr, None)
            self._closures.pop(affected_addr, None)

        self._data[validated] = normalized
        if new_closure is not None:
            self._closures[validated] = new_closure

    @property
    def eval_count(self):
        return self._eval_count
