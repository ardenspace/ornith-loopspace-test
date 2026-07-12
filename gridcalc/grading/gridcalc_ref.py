"""Independent naive reference for the gridcalc spec (Experiment W oracle).

Authored from spec.md alone, before either arm ran. No dependency
tracking: every get re-evaluates recursively (R11's naive model).
eval_count is NOT modeled (R10 is asserted directly against the arm);
the self-test shim therefore skips r10 tests.
"""
import re
import sys

sys.setrecursionlimit(20000)  # naive recursion over 256-cell chains

ERRORS = ("#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!")
FUNCS = ("SUM", "MIN", "MAX", "COUNT")
_ADDR = re.compile(r"^[A-Z]([1-9][0-9]?)$")
_TOKEN = re.compile(
    r"[ \t]*(?:(?P<int>[0-9]+)|(?P<ident>[A-Z]+[0-9]*)"
    r"|(?P<op><=|>=|<>|[=<>+\-*/():]))"
)
_REFSHAPE = re.compile(r"^([A-Z])([0-9]+)$")


class _Err(Exception):
    def __init__(self, s):
        self.s = s


def _tokenize(src):
    toks, i = [], 0
    while i < len(src):
        m = _TOKEN.match(src, i)
        if not m:
            if src[i] in " \t":  # trailing whitespace
                i += 1
                continue
            raise _Err("#PARSE!")
        if m.group("int") is not None:
            toks.append(("int", m.group("int")))
        elif m.group("ident") is not None:
            toks.append(("ident", m.group("ident")))
        else:
            toks.append(("op", m.group("op")))
        i = m.end()
    return toks


class _Parser:
    def __init__(self, toks):
        self.toks, self.i = toks, 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self):
        t = self.peek()
        if t is None:
            raise _Err("#PARSE!")
        self.i += 1
        return t

    def expect_op(self, op):
        t = self.next()
        if t != ("op", op):
            raise _Err("#PARSE!")

    def parse(self):
        node = self.expr()
        if self.peek() is not None:
            raise _Err("#PARSE!")
        return node

    def expr(self):
        node = self.additive()
        while self.peek() and self.peek()[0] == "op" and self.peek()[1] in (
            "=", "<>", "<", "<=", ">", ">="
        ):
            op = self.next()[1]
            node = ("cmp", op, node, self.additive())
        return node

    def additive(self):
        node = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.next()[1]
            node = ("bin", op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.next()[1]
            node = ("bin", op, node, self.factor())
        return node

    def factor(self):
        if self.peek() == ("op", "-"):
            self.next()
            return ("neg", self.factor())
        return self.primary()

    def primary(self):
        t = self.next()
        if t[0] == "int":
            return ("int", int(t[1]))
        if t[0] == "ident":
            if _REFSHAPE.match(t[1]):
                return ("ref", t[1])
            if t[1] in FUNCS:
                self.expect_op("(")
                a = self.next()
                if a[0] != "ident" or not _REFSHAPE.match(a[1]):
                    raise _Err("#PARSE!")
                self.expect_op(":")
                b = self.next()
                if b[0] != "ident" or not _REFSHAPE.match(b[1]):
                    raise _Err("#PARSE!")
                self.expect_op(")")
                return ("func", t[1], a[1], b[1])
            raise _Err("#PARSE!")
        if t == ("op", "("):
            node = self.expr()
            self.expect_op(")")
            return node
        raise _Err("#PARSE!")


def _cell_of(reftok):
    m = _REFSHAPE.match(reftok)
    col, digits = m.group(1), m.group(2)
    if digits[0] == "0" or not 1 <= int(digits) <= 99:
        raise _Err("#REF!")
    return col, int(digits)


class RefSheet:
    def __init__(self):
        self._cells = {}  # addr -> ("num", int) | ("str", s) | ("formula", src)

    # -- API ---------------------------------------------------------------
    def set(self, addr, raw):
        addr = self._addr(addr)
        if isinstance(raw, bool):
            raise ValueError("bool raw")
        if isinstance(raw, int):
            self._cells[addr] = ("num", int(raw))
        elif isinstance(raw, str):
            s = str(raw)
            if s.startswith("="):
                self._cells[addr] = ("formula", s[1:])
            else:
                self._cells[addr] = ("str", s)
        else:
            raise ValueError("bad raw type")
        return None

    def get(self, addr):
        addr = self._addr(addr)
        kind_val = self._cells.get(addr)
        if kind_val is None:
            return None
        kind, val = kind_val
        if kind in ("num", "str"):
            return val
        try:
            return self._eval_formula(addr, val, set())
        except _Err as e:
            return e.s

    @property
    def eval_count(self):  # not modeled by the naive reference
        return 0

    # -- internals ----------------------------------------------------------
    @staticmethod
    def _addr(addr):
        if not isinstance(addr, str) or not _ADDR.match(str(addr)):
            raise ValueError("bad address")
        return str(addr)

    def _eval_formula(self, addr, src, in_progress):
        if addr in in_progress:
            raise _Err("#CYCLE!")
        node = _Parser(_tokenize(src)).parse()
        return self._eval(node, in_progress | {addr})

    def _numeric(self, addr, in_progress):
        kv = self._cells.get(addr)
        if kv is None:
            return 0
        kind, val = kv
        if kind == "num":
            return val
        if kind == "str":
            raise _Err("#TYPE!")
        if addr in in_progress:
            raise _Err("#CYCLE!")
        return self._eval_formula(addr, val, in_progress)

    def _eval(self, node, ip):
        tag = node[0]
        if tag == "int":
            return node[1]
        if tag == "ref":
            col, row = _cell_of(node[1])
            return self._numeric(f"{col}{row}", ip)
        if tag == "neg":
            return -self._eval(node[1], ip)
        if tag == "bin":
            _, op, l, r = node
            a = self._eval(l, ip)
            b = self._eval(r, ip)
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if b == 0:
                raise _Err("#DIV!")
            q = abs(a) // abs(b)
            return q if (a >= 0) == (b >= 0) else -q
        if tag == "cmp":
            _, op, l, r = node
            a = self._eval(l, ip)
            b = self._eval(r, ip)
            res = {
                "=": a == b, "<>": a != b, "<": a < b,
                "<=": a <= b, ">": a > b, ">=": a >= b,
            }[op]
            return 1 if res else 0
        if tag == "func":
            _, name, tl, br = node
            c1, r1 = _cell_of(tl)
            c2, r2 = _cell_of(br)
            if c1 > c2 or r1 > r2:
                raise _Err("#REF!")
            members = [
                f"{chr(c)}{r}"
                for r in range(r1, r2 + 1)
                for c in range(ord(c1), ord(c2) + 1)
            ]
            if name == "COUNT":
                return sum(1 for m in members if m in self._cells)
            vals = []
            for m in members:
                kv = self._cells.get(m)
                if kv is None:
                    continue
                kind, val = kv
                if kind == "str":
                    raise _Err("#TYPE!")
                if kind == "num":
                    vals.append(val)
                else:
                    if m in ip:
                        raise _Err("#CYCLE!")
                    vals.append(self._eval_formula(m, val, ip))
            if name == "SUM":
                return sum(vals)
            if not vals:
                raise _Err("#TYPE!")
            return min(vals) if name == "MIN" else max(vals)
        raise _Err("#PARSE!")
