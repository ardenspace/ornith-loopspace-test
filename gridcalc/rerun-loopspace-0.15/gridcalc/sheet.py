"""Sheet implementation with address validation, literal storage, and formula evaluation."""
import re

# Valid address: one uppercase A-Z letter followed by digits 1-99 (no leading zeros)
_ADDRESS_PATTERN = re.compile(r"^[A-Z](?:[1-9][0-9]?)$")


def _validate_address(addr):
    """Validate an address string. Raises ValueError if invalid."""
    if not isinstance(addr, str):
        raise ValueError(f"Address must be a string, got {type(addr).__name__}")
    if not _ADDRESS_PATTERN.match(addr):
        raise ValueError(f"Invalid address: {addr!r}")


class Sheet:
    """In-memory spreadsheet with validated addressing, literal storage, and dirty propagation."""

    def __init__(self):
        self._store = {}
        self._eval_count = 0
        self._evaluating = set()
        self._cache = {}
        self._dirty = set()

    @property
    def eval_count(self):
        """Cumulative evaluation count. Starts at 0, only increases during formula evaluation."""
        return self._eval_count

    def _compute_closure(self, addr):
        """Compute the reference closure of a cell.

        The closure is the least set containing addr and, for every formula cell
        in the set, every cell its formula references directly — each single REF
        and every cell covered by any RANGE argument.

        Args:
            addr: Address string to compute closure for

        Returns:
            Set of addresses in the reference closure
        """
        closure = set()
        stack = [addr]

        while stack:
            current = stack.pop()
            if current in closure:
                continue
            closure.add(current)

            # Get the raw value from store
            value = self._store.get(current)

            # Only formula cells contribute references
            if not (isinstance(value, str) and value.startswith("=")):
                continue

            # Parse the formula to find references
            formula = value[1:]  # Strip leading '='
            try:
                from gridcalc.parser import parse as parser_parse
                ast = parser_parse(formula)
                # Extract references from AST
                refs = self._extract_references(ast)
                for ref_addr in refs:
                    if ref_addr not in closure:
                        stack.append(ref_addr)
            except Exception:
                # #PARSE! formula contributes no references (closure is just itself)
                pass

        return closure

    def _extract_references(self, node):
        """Extract all cell references from an AST node.

        Args:
            node: AST tuple from parser

        Returns:
            List of address strings referenced by this node
        """
        if node is None:
            return []

        # INT node - no references
        if node[0] == "INT":
            return []

        node_type = node[0]

        # REF node
        if node_type == "REF":
            return [node[1]]

        # Function node (SUM, MIN, MAX, COUNT) - extract range members
        if node_type in ("SUM", "MIN", "MAX", "COUNT"):
            range_spec = node[1]
            start_addr = range_spec[0]
            end_addr = range_spec[1]

            # Validate range addresses
            from gridcalc.evaluator import _parse_address
            start_col, start_row = _parse_address(start_addr)
            end_col, end_row = _parse_address(end_addr)

            if start_col is None or end_col is None:
                # Invalid range contributes no members
                return []

            if (start_col, start_row) > (end_col, end_row):
                # Mis-ordered range contributes no members
                return []

            # Generate all cells in the range
            refs = []
            for row in range(start_row, end_row + 1):
                for col in range(start_col, end_col + 1):
                    from gridcalc.evaluator import _col_to_addr
                    addr = _col_to_addr(col) + str(row)
                    refs.append(addr)
            return refs

        # Binary/unary operations - extract from children
        refs = []
        if len(node) > 1:
            refs.extend(self._extract_references(node[1]))
        if len(node) > 2:
            refs.extend(self._extract_references(node[2]))
        return refs

    def set(self, addr, raw):
        """Store a value at the given address.

        Args:
            addr: Valid grid address (e.g. "A1", "Z99")
            raw: Value to store (int or str)

        Returns:
            None on success

        Raises:
            ValueError: If addr is invalid or raw is unsupported type
        """
        _validate_address(addr)

        # Normalize str-subclass to plain str
        if isinstance(raw, str) and not type(raw) is str:
            raw = str(raw)

        # bool is rejected even though it's an int subclass
        if isinstance(raw, bool):
            raise ValueError(f"bool values are not allowed, got {type(raw).__name__}")

        # Only int and str are allowed
        if not isinstance(raw, (int, str)):
            raise ValueError(
                f"Unsupported raw type: {type(raw).__name__}. "
                "Only int and str are allowed."
            )

        # Normalize int-subclass to plain int
        if isinstance(raw, int) and not type(raw) is int:
            raw = int(raw)

        self._store[addr] = raw
        self._dirty.add(addr)
        return None

    def get(self, addr):
        """Retrieve the value at the given address.

        Args:
            addr: Valid grid address (e.g. "A1", "Z99")

        Returns:
            The stored value (int or str), or None if never set.
            For formula cells, returns the evaluated result (int or error string).

        Raises:
            ValueError: If addr is invalid
        """
        _validate_address(addr)

        # Check if this cell or any cell in its closure is dirty
        needs_recompute = addr in self._dirty
        if not needs_recompute:
            # Check if any cell in the closure is dirty
            closure = self._compute_closure(addr)
            needs_recompute = bool(closure & self._dirty)

        # If not dirty and cached, return cached value
        if not needs_recompute and addr in self._cache:
            return self._cache[addr]

        # Need to re-evaluate - clear cache for entire closure and re-evaluate
        if needs_recompute:
            closure = self._compute_closure(addr)
            # Clear cache for all cells in the closure
            for cell_addr in closure:
                if cell_addr in self._cache:
                    del self._cache[cell_addr]
            # Re-evaluate the target cell (which will recursively evaluate dependencies)
            return self._evaluate_cell(addr)

        # Fallback: evaluate the cell directly
        return self._evaluate_cell(addr)

    def _evaluate_cell(self, addr):
        """Evaluate a cell and cache the result.

        This method is used internally for evaluation and by the evaluator
        to resolve references.

        Args:
            addr: Address string to evaluate

        Returns:
            The evaluated value (int, str, or None)
        """
        value = self._store.get(addr)

        # Empty cell
        if value is None:
            self._cache[addr] = None
            self._dirty.discard(addr)
            return None

        # Formula cell: evaluate it
        if isinstance(value, str) and value.startswith("="):
            from gridcalc.parser import parse as parser_parse
            from gridcalc.evaluator import evaluate as eval_formula

            formula = value[1:]  # Strip leading '='
            try:
                ast = parser_parse(formula)
                self._eval_count += 1
                result = eval_formula(ast, self, self._evaluating)
                self._cache[addr] = result
                self._dirty.discard(addr)
                return result
            except Exception:
                # If parsing fails or any other error occurs, return #PARSE!
                self._eval_count += 1
                result = "#PARSE!"
                self._cache[addr] = result
                self._dirty.discard(addr)
                return result

        # Literal cell (int or str) — cache it too for consistency
        self._cache[addr] = value
        self._dirty.discard(addr)
        return value
