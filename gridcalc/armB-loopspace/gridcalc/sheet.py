import re

_ADDR_RE = re.compile(r"^[A-Z]([1-9]|[1-9]\d)$")


def _validate_address(addr) -> str:
    if not isinstance(addr, str):
        raise ValueError(f"address must be a str, got {type(addr).__name__}")
    if type(addr) is not str:
        normalized = addr.upper()
        if not _ADDR_RE.match(normalized):
            raise ValueError(f"invalid address: {addr!r}")
        return normalized
    if not _ADDR_RE.match(addr):
        raise ValueError(f"invalid address: {addr!r}")
    return addr


def _extract_refs(node):
    """Extract all references (REF tokens and RANGE endpoints) from an AST node."""
    if node is None:
        return []
    
    node_type = node[0]
    
    # REF token: (REF_T, ref_string)
    if node_type == "REF":
        return [node[1]]
    
    # FUNC node: (FUNC_T, func_name, RANGE_T, ref1, ref2)
    if node_type == "FUNC":
        # Extract refs from range endpoints
        refs = [node[3], node[4]]
        # Also check if there are nested expressions (though ranges shouldn't nest)
        return refs
    
    # Unary minus: (NEG, operand)
    if node_type == "NEG":
        return _extract_refs(node[1])
    
    # Binary operators: (OP, left, right)
    if node_type in {"ADD", "SUB", "MUL", "DIV", "EQ", "NEQ", "LT", "LTE", "GT", "GTE"}:
        return _extract_refs(node[1]) + _extract_refs(node[2])
    
    # INT literal: no refs
    if node_type == "INT":
        return []
    
    return []


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


def _compute_closure(formula_text: str, sheet: 'Sheet') -> set:
    """Compute the reference closure of a formula cell.
    
    The closure is the least set containing the cell itself and, for every
    formula cell in the set, every cell its formula references directly.
    """
    from .parser import parse
    
    # Parse the formula
    parsed = parse(formula_text[1:])  # Strip leading =
    if parsed == "#PARSE!":
        # #PARSE! formula's closure is just itself
        return set()
    
    # Extract direct references
    refs = _extract_refs(parsed)
    
    # Compute the closure
    closure = set()
    queue = list(refs)
    
    while queue:
        ref = queue.pop(0)
        if ref in closure:
            continue
        closure.add(ref)
        
        # If this ref is a formula cell, add its references to the queue
        raw = sheet._data.get(ref)
        if raw is not None and isinstance(raw, str) and raw.startswith("="):
            sub_refs = _extract_refs(parse(raw[1:]))
            queue.extend(sub_refs)
    
    return closure


class Sheet:
    def __init__(self):
        self._data = {}
        self._eval_count = 0
        self._cache = {}
        self._deps = {}  # Maps formula cell -> set of cells it depends on

    def get(self, addr, cycle_set=None):
        from .evaluator import evaluate_formula

        normalized = _validate_address(addr)

        if normalized in self._cache:
            return self._cache[normalized]

        raw = self._data.get(normalized)
        if raw is None:
            return None
        if isinstance(raw, str) and raw.startswith("="):
            self._eval_count += 1
            if cycle_set is None:
                cycle_set = {normalized}
            else:
                cycle_set = cycle_set | {normalized}
            result = evaluate_formula(raw, self, cycle_set)
            self._cache[normalized] = result
            
            # Compute and store dependencies for this formula cell
            self._deps[normalized] = _compute_closure(raw, self)
            
            return result
        return raw

    def set(self, addr, value):
        normalized = _validate_address(addr)
        if isinstance(value, bool):
            raise ValueError(f"bool values are not allowed, got {type(value).__name__}")
        if not isinstance(value, (int, str)):
            raise ValueError(f"unsupported value type: {type(value).__name__}")
        if isinstance(value, int):
            stored = int(value)
        else:
            stored = str(value)
        self._data[normalized] = stored
        
        # Invalidate cache entries for cells that depend on this address.
        # The edited cell itself is always in its own closure (per R10).
        cells_to_invalidate = [normalized]
        for cached_addr in self._cache:
            if cached_addr == normalized:
                continue  # Already added
            if cached_addr in self._deps:
                closure = self._deps[cached_addr]
                if normalized in closure:
                    cells_to_invalidate.append(cached_addr)
            else:
                # If we don't have dependency info, be conservative
                cells_to_invalidate.append(cached_addr)
        
        for addr_to_invalidate in cells_to_invalidate:
            self._cache.pop(addr_to_invalidate, None)
            # Also remove dependency info since it may be stale
            self._deps.pop(addr_to_invalidate, None)

    @property
    def eval_count(self):
        return self._eval_count
