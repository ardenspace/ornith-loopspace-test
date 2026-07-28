"""Address helpers and pure AST evaluation for gridcalc (SPEC.md R4-R9).

`evaluate` and `direct_deps` are pure functions of an AST plus a `ctx`
object; all sheet-state concerns (storage, caching, eval_count, cycle
detection) live in Sheet and are reached only through `ctx._ref_value` /
`ctx._range_values`, keeping this module a plain, sheet-free evaluator.
"""

import re

ADDR_RE = re.compile(r"^[A-Z]([1-9][0-9]?)$")

ERROR_VALUES = ("#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!")


def is_grid_address(addr):
    return bool(ADDR_RE.fullmatch(addr))


def addr_col_row(addr):
    return ord(addr[0]) - ord("A"), int(addr[1:])


def make_addr(col, row):
    return chr(ord("A") + col) + str(row)


def _is_error(v):
    return isinstance(v, str)


def apply_op(op, l, r):
    if op == "+":
        return l + r
    if op == "-":
        return l - r
    if op == "*":
        return l * r
    if op == "/":
        if r == 0:
            return "#DIV!"
        q = abs(l) // abs(r)
        return -q if (l < 0) != (r < 0) else q
    if op == "=":
        return 1 if l == r else 0
    if op == "<>":
        return 1 if l != r else 0
    if op == "<":
        return 1 if l < r else 0
    if op == "<=":
        return 1 if l <= r else 0
    if op == ">":
        return 1 if l > r else 0
    if op == ">=":
        return 1 if l >= r else 0
    raise AssertionError(f"unknown operator {op!r}")


def evaluate(node, ctx):
    """Evaluate an AST node to an int or an error string.

    `ctx` must provide `_ref_value(addr) -> int|str` and
    `_range_values(tl, br, name) -> int|str`.
    """
    kind = node[0]
    if kind == "perr":
        return "#PARSE!"
    if kind == "int":
        return node[1]
    if kind == "ref":
        return ctx._ref_value(node[1])
    if kind == "neg":
        _, count, inner = node
        v = evaluate(inner, ctx)
        if _is_error(v):
            return v
        return -v if count % 2 else v
    if kind == "bin":
        _, op, left, right = node
        lv = evaluate(left, ctx)
        if _is_error(lv):
            return lv
        rv = evaluate(right, ctx)
        if _is_error(rv):
            return rv
        return apply_op(op, lv, rv)
    if kind == "func":
        _, name, tl, br = node
        return ctx._range_values(tl, br, name)
    raise AssertionError(f"unknown node kind {kind!r}")


def _valid_range(tl, br):
    if not (is_grid_address(tl) and is_grid_address(br)):
        return None
    tc, tr = addr_col_row(tl)
    bc, br_ = addr_col_row(br)
    if tc > bc or tr > br_:
        return None
    return tc, tr, bc, br_


def range_addresses(tl, br):
    """Row-major list of addresses in a valid range, or None if invalid."""
    bounds = _valid_range(tl, br)
    if bounds is None:
        return None
    tc, tr, bc, br_ = bounds
    return [make_addr(c, r) for r in range(tr, br_ + 1) for c in range(tc, bc + 1)]


def direct_deps(node):
    """Static (sheet-free) set of addresses a formula AST directly depends on.

    Per R10: every single REF that denotes a grid cell, and every cell of a
    *valid* RANGE argument (SUM/MIN/MAX/COUNT alike, empty cells included).
    An invalid range or an out-of-grid REF contributes no members. A
    ('perr',) node's closure is itself only (no deps here).
    """
    deps = set()
    _collect_deps(node, deps)
    return frozenset(deps)


def _collect_deps(node, deps):
    kind = node[0]
    if kind == "int" or kind == "perr":
        return
    if kind == "ref":
        addr = node[1]
        if is_grid_address(addr):
            deps.add(addr)
        return
    if kind == "neg":
        _collect_deps(node[2], deps)
        return
    if kind == "bin":
        _collect_deps(node[2], deps)
        _collect_deps(node[3], deps)
        return
    if kind == "func":
        _, _name, tl, br = node
        addrs = range_addresses(tl, br)
        if addrs:
            deps.update(addrs)
        return
    raise AssertionError(f"unknown node kind {kind!r}")
