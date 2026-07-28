"""Seeded differential testing (SPEC.md R11 / PLAN.md task 4.4).

This file implements its own naive, full-recompute reference model of the
gridcalc formula language from scratch (no shared code with gridcalc's
engine) and cross-checks it against `gridcalc.Sheet` over many random
set/get sequences. A mismatch means Sheet's incremental engine disagrees
with a straightforward from-scratch evaluation of the same spec.
"""

import random
import re

from gridcalc import Sheet

ADDR_RE = re.compile(r"^[A-Z]([1-9][0-9]?)$")
FUNC_NAMES = ("SUM", "MIN", "MAX", "COUNT")


# ---------------------------------------------------------------------
# Independent tokenizer/parser/evaluator (naive, full recompute, no cache)
# ---------------------------------------------------------------------

class _RefParseError(Exception):
    pass


def _ref_tokenize(text):
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t":
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            tokens.append(("INT", text[i:j]))
            i = j
            continue
        if "A" <= c <= "Z":
            j = i
            while j < n and "A" <= text[j] <= "Z":
                j += 1
            letters = text[i:j]
            i = j
            if i < n and text[i].isdigit():
                k = i
                while k < n and text[k].isdigit():
                    k += 1
                digits = text[i:k]
                i = k
                if len(letters) != 1:
                    raise _RefParseError()
                tokens.append(("REF", letters + digits))
            else:
                tokens.append(("IDENT", letters))
            continue
        if c in "()+-*/:":
            tokens.append((c, c))
            i += 1
            continue
        if c == "=":
            tokens.append(("=", "=")); i += 1; continue
        if c == "<":
            if text[i:i + 2] == "<=":
                tokens.append(("<=", "<=")); i += 2; continue
            if text[i:i + 2] == "<>":
                tokens.append(("<>", "<>")); i += 2; continue
            tokens.append(("<", "<")); i += 1; continue
        if c == ">":
            if text[i:i + 2] == ">=":
                tokens.append((">=", ">=")); i += 2; continue
            tokens.append((">", ">")); i += 1; continue
        raise _RefParseError()
    tokens.append(("EOF", ""))
    return tokens


class _RefParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, kind):
        if self.peek()[0] != kind:
            raise _RefParseError()
        return self.advance()

    def expr(self):
        node = self.additive()
        while self.peek()[0] in ("=", "<>", "<", "<=", ">", ">="):
            op = self.advance()[0]
            node = ("bin", op, node, self.additive())
        return node

    def additive(self):
        node = self.term()
        while self.peek()[0] in ("+", "-"):
            op = self.advance()[0]
            node = ("bin", op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek()[0] in ("*", "/"):
            op = self.advance()[0]
            node = ("bin", op, node, self.factor())
        return node

    def factor(self):
        if self.peek()[0] == "-":
            self.advance()
            return ("neg", self.factor())
        return self.primary()

    def primary(self):
        tok = self.peek()
        if tok[0] == "INT":
            self.advance()
            return ("int", int(tok[1]))
        if tok[0] == "REF":
            self.advance()
            return ("ref", tok[1])
        if tok[0] == "IDENT":
            if tok[1] not in FUNC_NAMES:
                raise _RefParseError()
            name = tok[1]
            self.advance()
            self.expect("(")
            tl = self.expect("REF")[1]
            self.expect(":")
            br = self.expect("REF")[1]
            self.expect(")")
            return ("func", name, tl, br)
        if tok[0] == "(":
            self.advance()
            node = self.expr()
            self.expect(")")
            return node
        raise _RefParseError()


def ref_parse(text):
    try:
        p = _RefParser(_ref_tokenize(text))
        node = p.expr()
        if p.peek()[0] != "EOF":
            raise _RefParseError()
        return node
    except _RefParseError:
        return ("perr",)


def _ref_is_grid(addr):
    return bool(ADDR_RE.fullmatch(addr))


def _ref_col_row(addr):
    return ord(addr[0]) - ord("A"), int(addr[1:])


def _ref_addrs_in_range(tl, br):
    if not (_ref_is_grid(tl) and _ref_is_grid(br)):
        return None
    tc, tr = _ref_col_row(tl)
    bc, brr = _ref_col_row(br)
    if tc > bc or tr > brr:
        return None
    out = []
    for r in range(tr, brr + 1):
        for c in range(tc, bc + 1):
            out.append(chr(ord("A") + c) + str(r))
    return out


class _RefCycle(Exception):
    pass


def _ref_div(l, r):
    if r == 0:
        return "#DIV!"
    q = abs(l) // abs(r)
    return -q if (l < 0) != (r < 0) else q


def _ref_apply(op, l, r):
    return {
        "+": lambda: l + r,
        "-": lambda: l - r,
        "*": lambda: l * r,
        "/": lambda: _ref_div(l, r),
        "=": lambda: 1 if l == r else 0,
        "<>": lambda: 1 if l != r else 0,
        "<": lambda: 1 if l < r else 0,
        "<=": lambda: 1 if l <= r else 0,
        ">": lambda: 1 if l > r else 0,
        ">=": lambda: 1 if l >= r else 0,
    }[op]()


def naive_get(contents, addr, in_progress=None):
    """Full, uncached, from-scratch evaluation of `addr` against a plain
    {addr: raw_content} dict, where raw_content is ('num', int),
    ('str', str), or ('formula', text-after-equals)."""
    if in_progress is None:
        in_progress = set()
    cell = contents.get(addr)
    if cell is None:
        return None
    kind = cell[0]
    if kind == "num" or kind == "str":
        return cell[1]
    ast = ref_parse(cell[1])
    try:
        return _naive_eval(ast, contents, in_progress)
    except _RefCycle:
        return "#CYCLE!"


def _naive_ref_value(contents, addr, in_progress):
    if not _ref_is_grid(addr):
        return "#REF!"
    if addr in in_progress:
        raise _RefCycle()
    cell = contents.get(addr)
    if cell is None:
        return 0
    kind = cell[0]
    if kind == "num":
        return cell[1]
    if kind == "str":
        return "#TYPE!"
    in_progress = in_progress | {addr}
    ast = ref_parse(cell[1])
    try:
        return _naive_eval(ast, contents, in_progress)
    except _RefCycle:
        return "#CYCLE!"


def _naive_eval(node, contents, in_progress):
    kind = node[0]
    if kind == "perr":
        return "#PARSE!"
    if kind == "int":
        return node[1]
    if kind == "ref":
        return _naive_ref_value(contents, node[1], in_progress)
    if kind == "neg":
        v = _naive_eval(node[1], contents, in_progress)
        return v if isinstance(v, str) else -v
    if kind == "bin":
        _, op, left, right = node
        lv = _naive_eval(left, contents, in_progress)
        if isinstance(lv, str):
            return lv
        rv = _naive_eval(right, contents, in_progress)
        if isinstance(rv, str):
            return rv
        return _ref_apply(op, lv, rv)
    if kind == "func":
        _, name, tl, br = node
        addrs = _ref_addrs_in_range(tl, br)
        if addrs is None:
            return "#REF!"
        if name == "COUNT":
            return sum(1 for a in addrs if a in contents)
        values = []
        for a in addrs:
            cell = contents.get(a)
            if cell is None:
                continue
            if cell[0] == "num":
                v = cell[1]
            elif cell[0] == "str":
                v = "#TYPE!"
            else:
                v = _naive_ref_value(contents, a, in_progress)
            if isinstance(v, str):
                return v
            values.append(v)
        if name == "SUM":
            return sum(values)
        if name == "MIN":
            return min(values) if values else "#TYPE!"
        if name == "MAX":
            return max(values) if values else "#TYPE!"
    raise AssertionError(node)


# ---------------------------------------------------------------------
# Randomized differential harness
# ---------------------------------------------------------------------

REGION_COLS = "ABCDE"
REGION_ROWS = range(1, 6)
ADDRS = [f"{c}{r}" for c in REGION_COLS for r in REGION_ROWS]

LITERALS = [0, 1, -1, 7, -7, "hi", "#DIV!"]
FORMULA_TEMPLATES = [
    "={a}+{b}",
    "={a}-{b}",
    "={a}*{b}",
    "={a}/{b}",
    "={a}<{b}",
    "={a}<={b}",
    "={a}>{b}",
    "={a}={b}",
    "=SUM({a}:{b})",
    "=MIN({a}:{b})",
    "=MAX({a}:{b})",
    "=COUNT({a}:{b})",
    "=-{a}",
    "={a}",
]


def _random_raw(rng, addrs):
    choice = rng.random()
    if choice < 0.35:
        return rng.choice(LITERALS)
    if choice < 0.45:
        return "not-a-cell-value-but-a-string"
    a, b = rng.choice(addrs), rng.choice(addrs)
    template = rng.choice(FORMULA_TEMPLATES)
    return template.format(a=a, b=b)


def _run_one_sequence(seed, length):
    rng = random.Random(seed)
    sheet = Sheet()
    contents = {}
    for _ in range(length):
        op = rng.random()
        if op < 0.7:
            addr = rng.choice(ADDRS)
            raw = _random_raw(rng, ADDRS)
            sheet.set(addr, raw)
            if isinstance(raw, str) and raw.startswith("="):
                contents[addr] = ("formula", raw[1:])
            elif isinstance(raw, str):
                contents[addr] = ("str", raw)
            else:
                contents[addr] = ("num", raw)
        else:
            addr = rng.choice(ADDRS)
            got = sheet.get(addr)
            expected = naive_get(contents, addr)
            if got != expected:
                return (seed, addr, got, expected, dict(contents))
    return None


def test_seeded_differential_suite():
    mismatches = []
    num_seeds = 1000
    length = 50
    for seed in range(num_seeds):
        result = _run_one_sequence(seed, length)
        if result is not None:
            mismatches.append(result)
    assert not mismatches, f"differential mismatches (seed, addr, got, expected): {mismatches[:5]}"
