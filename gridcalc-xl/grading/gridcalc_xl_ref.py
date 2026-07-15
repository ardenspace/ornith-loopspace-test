"""Independent naive reference for the gridcalc-xl spec (Experiment W').

Authored from gridcalc-xl/SPEC.md alone, before any arm ran. No
dependency tracking: every get re-evaluates recursively from the stored
state (R11's naive model). eval_count is NOT modeled (R10/R27 counter
patterns are asserted directly against the arm); the self-test therefore
excludes counter-marked tests.

Covers the full XL surface: typed evaluation and strings (R13-R15),
$-marks and copy text rewriting (R16-R17), per-sheet named ranges (R18),
the undo/redo journal (R19-R20), multi-sheet workbooks and qualifiers
(R21-R23), string persistence (R24-R25), and the clock (R26-R27).
"""
import json
import re
import sys

sys.setrecursionlimit(30000)  # naive recursion over 256-cell chains (R12)

_FUNCS = ("SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW")
_AGGS = ("SUM", "MIN", "MAX", "COUNT")

_ADDR_RE = re.compile(r"^[A-Z]([1-9][0-9]?)$")
_SHEETNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]{1,31}$")
_REFSHAPE_RE = re.compile(r"^[A-Z][0-9]+$")
# copy/define_name qualified-argument shapes: no whitespace (R23)
_QADDR_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]{0,31})!([A-Z][1-9][0-9]?)$")
_QTARGET_RE = re.compile(
    r"^(?:([A-Za-z][A-Za-z0-9_]{0,31})!)?"
    r"([A-Z][1-9][0-9]?)(?::([A-Z][1-9][0-9]?))?$")

_TOKEN_RES = (
    ("referr", re.compile(r"#REF!")),
    ("string", re.compile(r'"[^"]*"')),
    ("dref", re.compile(r"\$[A-Z]\$?[0-9]+|[A-Z]\$[0-9]+")),
    ("int", re.compile(r"[0-9]+")),
    ("ident", re.compile(r"[A-Za-z_][A-Za-z0-9_]*")),
    ("op", re.compile(r"<=|>=|<>|[=<>+\-*/(),:!]")),
)


class _Err(Exception):
    def __init__(self, s):
        self.s = s


def _tokenize(src):
    toks, i, n = [], 0, len(src)
    while i < n:
        if src[i] in " \t":
            i += 1
            continue
        for kind, rx in _TOKEN_RES:
            m = rx.match(src, i)
            if m:
                toks.append((kind, m.group(0), i, m.end()))
                i = m.end()
                break
        else:
            raise _Err("#PARSE!")
    return toks


def _endpoint(tok):
    """Token -> endpoint record for eval + rewrite."""
    kind, text, start, end = tok
    if kind == "ident":
        if not _REFSHAPE_RE.match(text):
            raise _Err("#PARSE!")
        return {"letter": text[0], "digits": text[1:], "colabs": False,
                "rowabs": False, "lpos": start, "dstart": start + 1,
                "dend": end, "span": (start, end)}
    if kind == "dref":
        i = 0
        colabs = text[0] == "$"
        if colabs:
            i = 1
        letter, lpos = text[i], start + i
        i += 1
        rowabs = text[i] == "$"
        if rowabs:
            i += 1
        return {"letter": letter, "digits": text[i:], "colabs": colabs,
                "rowabs": rowabs, "lpos": lpos, "dstart": start + i,
                "dend": end, "span": (start, end)}
    raise _Err("#PARSE!")


class _Parser:
    """Full XL grammar (R3 + R13/R16/R17/R18/R22 extensions).

    Records every REF/RANGE construct with source spans so copy (R17)
    can rewrite text in place.
    """

    def __init__(self, toks):
        self.toks, self.i = toks, 0
        self.constructs = []

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self):
        t = self.peek()
        if t is None:
            raise _Err("#PARSE!")
        self.i += 1
        return t

    def peek_op(self, op):
        t = self.peek()
        return t is not None and t[0] == "op" and t[1] == op

    def expect_op(self, op):
        t = self.next()
        if t[0] != "op" or t[1] != op:
            raise _Err("#PARSE!")

    def parse(self):
        node = self.expr()
        if self.peek() is not None:
            raise _Err("#PARSE!")
        return node

    def expr(self):
        node = self.additive()
        while self.peek() and self.peek()[0] == "op" and self.peek()[1] in (
                "=", "<>", "<", "<=", ">", ">="):
            op = self.next()[1]
            node = ("cmp", op, node, self.additive())
        return node

    def additive(self):
        node = self.term()
        while self.peek() and self.peek()[0] == "op" and \
                self.peek()[1] in ("+", "-"):
            op = self.next()[1]
            node = ("bin", op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek() and self.peek()[0] == "op" and \
                self.peek()[1] in ("*", "/"):
            op = self.next()[1]
            node = ("bin", op, node, self.factor())
        return node

    def factor(self):
        if self.peek_op("-"):
            self.next()
            return ("neg", self.factor())
        return self.primary()

    def primary(self):
        t = self.next()
        kind, text, start, end = t
        if kind == "int":
            return ("int", int(text))
        if kind == "string":
            return ("str", text[1:-1])
        if kind == "referr":
            return ("referr",)
        if kind == "ident" and self.peek_op("!"):
            # tokenization precedence (R22): ident before '!' is a SHEET
            if not _SHEETNAME_RE.match(text):
                raise _Err("#PARSE!")
            self.next()
            ep = _endpoint(self.next())
            self.constructs.append(
                {"kind": "ref", "span": (start, ep["span"][1]), "eps": [ep]})
            return ("ref", text, ep["letter"], ep["digits"])
        if kind == "ident":
            if text in _FUNCS and self.peek_op("("):
                return self.call(text)
            if _REFSHAPE_RE.match(text):
                ep = _endpoint(t)
                self.constructs.append(
                    {"kind": "ref", "span": (start, end), "eps": [ep]})
                return ("ref", None, ep["letter"], ep["digits"])
            if _NAME_RE.match(text) and text not in _FUNCS:
                return ("name", text)
            raise _Err("#PARSE!")
        if kind == "dref":
            ep = _endpoint(t)
            self.constructs.append(
                {"kind": "ref", "span": (start, end), "eps": [ep]})
            return ("ref", None, ep["letter"], ep["digits"])
        if kind == "op" and text == "(":
            node = self.expr()
            self.expect_op(")")
            return node
        raise _Err("#PARSE!")

    def call(self, name):
        self.expect_op("(")
        if name in _AGGS:
            arg = self.rangearg()
            self.expect_op(")")
            return ("agg", name, arg)
        if name == "CONCAT":
            args = [self.expr()]
            while self.peek_op(","):
                self.next()
                args.append(self.expr())
            self.expect_op(")")
            return ("concat", args)
        if name == "LEN":
            a = self.expr()
            self.expect_op(")")
            return ("len", a)
        if name == "IF":
            a = self.expr()
            self.expect_op(",")
            b = self.expr()
            self.expect_op(",")
            c = self.expr()
            self.expect_op(")")
            return ("if", a, b, c)
        # NOW ( )
        self.expect_op(")")
        return ("now",)

    def rangearg(self):
        t = self.next()
        kind, text, start, end = t
        if kind == "referr":
            return ("referr",)
        qual = None
        if kind == "ident" and self.peek_op("!"):
            if not _SHEETNAME_RE.match(text):
                raise _Err("#PARSE!")
            qual = text
            self.next()
            t = self.next()
            kind = t[0]
        elif kind == "ident" and _NAME_RE.match(text) and \
                text not in _FUNCS and not _REFSHAPE_RE.match(text):
            return ("name", text)
        if kind not in ("ident", "dref"):
            raise _Err("#PARSE!")
        ep1 = _endpoint(t)
        self.expect_op(":")
        ep2 = _endpoint(self.next())
        self.constructs.append(
            {"kind": "range", "span": (start if qual else ep1["span"][0],
                                       ep2["span"][1]),
             "eps": [ep1, ep2]})
        return ("range", qual, (ep1["letter"], ep1["digits"]),
                (ep2["letter"], ep2["digits"]))


def _parse(src):
    p = _Parser(_tokenize(src))
    node = p.parse()
    return node, p.constructs


def _cellpos(letter, digits):
    """REF letter+digits -> (col, row) or #REF! (R6 digit-shape rule)."""
    if digits[0] == "0" or not 1 <= int(digits) <= 99:
        raise _Err("#REF!")
    return letter, int(digits)


def _shift_endpoint(ep, dcol, drow):
    """Component edits for one endpoint: None keep-verbatim, "OUT", or
    [(start, end, replacement), ...] (R17)."""
    digits = ep["digits"]
    if digits[0] == "0" or not 1 <= int(digits) <= 99:
        return None  # denotes no grid cell: kept verbatim
    ncol = ep["letter"] if ep["colabs"] else chr(ord(ep["letter"]) + dcol)
    nrow = int(digits) if ep["rowabs"] else int(digits) + drow
    if not "A" <= ncol <= "Z" or not 1 <= nrow <= 99:
        return "OUT"
    edits = []
    if not ep["colabs"]:
        edits.append((ep["lpos"], ep["lpos"] + 1, ncol))
    if not ep["rowabs"]:
        edits.append((ep["dstart"], ep["dend"], str(nrow)))
    return edits


def _rewrite_formula(raw, dcol, drow):
    """R17: rewrite formula text for a copy shifted by (dcol, drow)."""
    src = raw[1:]
    try:
        _, constructs = _parse(src)
    except _Err:
        return raw  # unparseable: byte-for-byte
    edits = []
    for c in constructs:
        results = [_shift_endpoint(ep, dcol, drow) for ep in c["eps"]]
        if "OUT" in results:
            edits.append((c["span"][0], c["span"][1], "#REF!"))
        else:
            for r in results:
                if r:
                    edits.extend(r)
    for s, e, rep in sorted(edits, reverse=True):
        src = src[:s] + rep + src[e:]
    return "=" + src


def _check_addr(addr):
    if not isinstance(addr, str) or not _ADDR_RE.match(str(addr)):
        raise ValueError("invalid address")
    return str(addr)


def _decimal(v):
    return str(v)  # base-10, leading '-' for negatives (R14)


class RefWorkbook:
    """Naive reference implementation of the full XL spec."""

    def __init__(self):
        self._sheets = {}   # name -> {addr: ("num",i)|("str",s)|("formula",raw)}
        self._names = {}    # sheet -> {NAME: (tsheet, c1, r1, c2, r2)}
        self._clock = 0
        self._journal = []
        self._redo = []

    # -- public API (exactly the R21 surface) -------------------------------
    def add_sheet(self, name):
        name = self._check_sheet_name(name)
        if name in self._sheets:
            raise ValueError("duplicate sheet")
        self._apply(("sheet", name))
        self._journal.append(("sheet", name))
        self._redo.clear()
        return _RefHandle(self, name)

    def sheet(self, name):
        if not isinstance(name, str) or str(name) not in self._sheets:
            raise ValueError("unknown sheet")
        return _RefHandle(self, str(name))

    @property
    def sheet_names(self):
        return list(self._sheets)

    def undo(self):
        if not self._journal:
            return False
        entry = self._journal.pop()
        self._revert(entry)
        self._redo.append(entry)
        return True

    def redo(self):
        if not self._redo:
            return False
        entry = self._redo.pop()
        self._apply(entry)
        self._journal.append(entry)
        return True

    def advance_clock(self):
        self._apply(("clock",))
        self._journal.append(("clock",))
        self._redo.clear()
        return self._clock

    @property
    def clock(self):
        return self._clock

    def to_json(self):
        sheets = []
        for name, cells in self._sheets.items():
            names = {nm: list(b) for nm, b in self._names[name].items()}
            sheets.append({"name": name,
                           "cells": {a: list(kv) for a, kv in cells.items()},
                           "names": names})
        return json.dumps({"clock": self._clock, "sheets": sheets})

    @classmethod
    def from_json(cls, s):
        if not isinstance(s, str):
            raise ValueError("not a str")

        def _reject(_):
            raise ValueError("floats are invalid")

        data = json.loads(str(s), parse_float=_reject,
                          parse_constant=_reject)
        if not isinstance(data, dict) or set(data) != {"clock", "sheets"}:
            raise ValueError("bad shape")
        clock = data["clock"]
        if type(clock) is not int or clock < 0:
            raise ValueError("bad clock")
        if not isinstance(data["sheets"], list):
            raise ValueError("bad sheets")
        wb = cls()
        for entry in data["sheets"]:
            if not isinstance(entry, dict) or \
                    set(entry) != {"name", "cells", "names"}:
                raise ValueError("bad sheet entry")
            name = entry["name"]
            if not isinstance(name, str) or \
                    not _SHEETNAME_RE.match(name) or name in wb._sheets:
                raise ValueError("bad sheet name")
            if not isinstance(entry["cells"], dict) or \
                    not isinstance(entry["names"], dict):
                raise ValueError("bad sheet shape")
            cells = {}
            for addr, kv in entry["cells"].items():
                if not isinstance(addr, str) or not _ADDR_RE.match(addr):
                    raise ValueError("bad address")
                if not isinstance(kv, list) or len(kv) != 2:
                    raise ValueError("bad cell")
                kind, v = kv
                if kind == "num":
                    if type(v) is not int:
                        raise ValueError("bad number cell")
                elif kind == "str":
                    if not isinstance(v, str):
                        raise ValueError("bad string cell")
                elif kind == "formula":
                    if not isinstance(v, str) or not v.startswith("="):
                        raise ValueError("bad formula cell")
                else:
                    raise ValueError("bad cell kind")
                cells[addr] = (kind, v)
            wb._sheets[name] = cells
            wb._names[name] = entry["names"]  # validated below
        for name in list(wb._names):
            names = {}
            for nm, b in wb._names[name].items():
                if not isinstance(nm, str) or not _NAME_RE.match(nm) or \
                        _REFSHAPE_RE.match(nm) or nm in _FUNCS:
                    raise ValueError("bad name")
                if not isinstance(b, list) or len(b) != 5:
                    raise ValueError("bad binding")
                ts, c1, r1, c2, r2 = b
                if ts not in wb._sheets:
                    raise ValueError("bad binding sheet")
                for c in (c1, c2):
                    if not isinstance(c, str) or len(c) != 1 or \
                            not "A" <= c <= "Z":
                        raise ValueError("bad binding column")
                for r in (r1, r2):
                    if type(r) is not int or not 1 <= r <= 99:
                        raise ValueError("bad binding row")
                if c1 > c2 or r1 > r2:
                    raise ValueError("mis-ordered binding")
                names[nm] = (ts, c1, r1, c2, r2)
            wb._names[name] = names
        wb._clock = clock
        return wb

    # -- journal machinery (R19/R20) ----------------------------------------
    def _apply(self, entry):
        if entry[0] == "cell":
            _, sname, addr, _prev, new = entry
            if new is None:
                self._sheets[sname].pop(addr, None)
            else:
                self._sheets[sname][addr] = new
        elif entry[0] == "name":
            _, sname, nm, _prev, new = entry
            if new is None:
                self._names[sname].pop(nm, None)
            else:
                self._names[sname][nm] = new
        elif entry[0] == "sheet":
            self._sheets[entry[1]] = {}
            self._names[entry[1]] = {}
        else:  # clock
            self._clock += 1

    def _revert(self, entry):
        if entry[0] == "cell":
            _, sname, addr, prev, _new = entry
            if prev is None:
                self._sheets[sname].pop(addr, None)
            else:
                self._sheets[sname][addr] = prev
        elif entry[0] == "name":
            _, sname, nm, prev, _new = entry
            if prev is None:
                self._names[sname].pop(nm, None)
            else:
                self._names[sname][nm] = prev
        elif entry[0] == "sheet":
            del self._sheets[entry[1]]  # empty again by journal LIFO
            del self._names[entry[1]]
        else:  # clock
            self._clock -= 1

    def _journaled(self, entry):
        self._apply(entry)
        self._journal.append(entry)
        self._redo.clear()

    # -- shared validation ---------------------------------------------------
    @staticmethod
    def _check_sheet_name(name):
        if not isinstance(name, str) or not _SHEETNAME_RE.match(str(name)):
            raise ValueError("invalid sheet name")
        return str(name)

    def _check_qaddr(self, arg, default_sheet):
        """copy argument: unqualified R1 address or SHEET!ADDR (R23)."""
        if not isinstance(arg, str):
            raise ValueError("not a str")
        arg = str(arg)
        if _ADDR_RE.match(arg):
            return default_sheet, arg
        m = _QADDR_RE.match(arg)
        if not m or m.group(1) not in self._sheets:
            raise ValueError("invalid qualified address")
        return m.group(1), m.group(2)

    # -- evaluation (naive, typed; R3-R9, R13-R18, R22-R23, R26) -------------
    def _typed_read(self, sname, addr, ip):
        kv = self._sheets[sname].get(addr)
        if kv is None:
            return 0
        kind, v = kv
        if kind in ("num", "str"):
            return v
        return self._eval_formula(sname, addr, v, ip)

    def _eval_formula(self, sname, addr, raw, ip):
        key = (sname, addr)
        if key in ip:
            raise _Err("#CYCLE!")
        try:
            node, _ = _parse(raw[1:])
        except _Err:
            raise _Err("#PARSE!")
        return self._eval(node, sname, ip | {key})

    def _resolve_rangearg(self, arg, host, ip):
        """RANGE-ARG -> (sheet, c1, r1, c2, r2); raises _Err."""
        if arg[0] == "referr":
            raise _Err("#REF!")
        if arg[0] == "name":
            binding = self._names[host].get(arg[1])
            if binding is None:
                raise _Err("#NAME!")
            return binding
        _, qual, (l1, d1), (l2, d2) = arg
        sheet = host if qual is None else qual
        if sheet not in self._sheets:
            raise _Err("#REF!")
        c1, r1 = _cellpos(l1, d1)
        c2, r2 = _cellpos(l2, d2)
        if c1 > c2 or r1 > r2:
            raise _Err("#REF!")
        return sheet, c1, r1, c2, r2

    def _eval(self, node, host, ip):
        tag = node[0]
        if tag == "int" or tag == "str":
            return node[1]
        if tag == "referr":
            raise _Err("#REF!")
        if tag == "ref":
            _, qual, letter, digits = node
            sheet = host if qual is None else qual
            if qual is not None and qual not in self._sheets:
                raise _Err("#REF!")
            c, r = _cellpos(letter, digits)
            return self._typed_read(sheet, f"{c}{r}", ip)
        if tag == "name":
            binding = self._names[host].get(node[1])
            if binding is None:
                raise _Err("#NAME!")
            ts, c1, r1, c2, r2 = binding
            if c1 != c2 or r1 != r2:
                raise _Err("#REF!")  # larger target used as a primary
            return self._typed_read(ts, f"{c1}{r1}", ip)
        if tag == "neg":
            v = self._eval(node[1], host, ip)
            if isinstance(v, str):
                raise _Err("#TYPE!")
            return -v
        if tag == "bin":
            _, op, l, r = node
            a = self._eval(l, host, ip)
            if isinstance(a, str):
                raise _Err("#TYPE!")
            b = self._eval(r, host, ip)
            if isinstance(b, str):
                raise _Err("#TYPE!")
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
            a = self._eval(l, host, ip)
            if op in ("<", "<=", ">", ">=") and isinstance(a, str):
                raise _Err("#TYPE!")
            b = self._eval(r, host, ip)
            if op in ("<", "<=", ">", ">=") and isinstance(b, str):
                raise _Err("#TYPE!")
            if isinstance(a, str) != isinstance(b, str):
                raise _Err("#TYPE!")
            res = {"=": a == b, "<>": a != b, "<": a < b,
                   "<=": a <= b, ">": a > b, ">=": a >= b}[op]
            return 1 if res else 0
        if tag == "agg":
            _, name, arg = node
            sheet, c1, r1, c2, r2 = self._resolve_rangearg(arg, host, ip)
            members = [f"{chr(c)}{r}"
                       for r in range(r1, r2 + 1)
                       for c in range(ord(c1), ord(c2) + 1)]
            cells = self._sheets[sheet]
            if name == "COUNT":  # structural: never evaluates (R8)
                return sum(1 for m in members if m in cells)
            vals = []
            for m in members:
                kv = cells.get(m)
                if kv is None:
                    continue  # empty contributes nothing (R8)
                kind, v = kv
                if kind == "formula":
                    v = self._eval_formula(sheet, m, v, ip)
                if isinstance(v, str):
                    raise _Err("#TYPE!")
                vals.append(v)
            if name == "SUM":
                return sum(vals)
            if not vals:
                raise _Err("#TYPE!")  # MIN/MAX over all-empty
            return min(vals) if name == "MIN" else max(vals)
        if tag == "concat":
            parts = []
            for a in node[1]:
                v = self._eval(a, host, ip)
                parts.append(v if isinstance(v, str) else _decimal(v))
            return "".join(parts)
        if tag == "len":
            v = self._eval(node[1], host, ip)
            return len(v) if isinstance(v, str) else len(_decimal(v))
        if tag == "if":
            _, cond, then, other = node
            c = self._eval(cond, host, ip)
            if isinstance(c, str):
                raise _Err("#TYPE!")
            return self._eval(then if c != 0 else other, host, ip)
        # now
        return self._clock


class _RefHandle:
    """Sheet handle bound to its sheet *name* (R19/R21)."""

    def __init__(self, wb, name):
        self.__dict__["_wb"] = wb
        self.__dict__["_name"] = name

    def _sheet(self):
        if self._name not in self._wb._sheets:
            raise ValueError("sheet does not exist")
        return self._name

    def set(self, addr, raw):
        sname = self._sheet()
        addr = _check_addr(addr)
        if isinstance(raw, bool):
            raise ValueError("bool raw")
        if isinstance(raw, int):
            new = ("num", int(raw))
        elif isinstance(raw, str):
            s = str(raw)
            new = ("formula", s) if s.startswith("=") else ("str", s)
        else:
            raise ValueError("bad raw type")
        prev = self._wb._sheets[sname].get(addr)
        self._wb._journaled(("cell", sname, addr, prev, new))
        return None

    def get(self, addr):
        sname = self._sheet()
        addr = _check_addr(addr)
        kv = self._wb._sheets[sname].get(addr)
        if kv is None:
            return None
        kind, v = kv
        if kind in ("num", "str"):
            return v
        try:
            return self._wb._eval_formula(sname, addr, v, set())
        except _Err as e:
            return e.s

    def copy(self, src, dst):
        sname = self._sheet()
        ssheet, saddr = self._wb._check_qaddr(src, sname)
        dsheet, daddr = self._wb._check_qaddr(dst, sname)
        kv = self._wb._sheets[ssheet].get(saddr)
        if kv is None:
            raise ValueError("copy from empty cell")
        kind, v = kv
        if kind == "formula":
            dcol = ord(daddr[0]) - ord(saddr[0])
            drow = int(daddr[1:]) - int(saddr[1:])
            new = ("formula", _rewrite_formula(v, dcol, drow))
        else:
            new = (kind, v)
        prev = self._wb._sheets[dsheet].get(daddr)
        self._wb._journaled(("cell", dsheet, daddr, prev, new))
        return None

    def define_name(self, name, target):
        sname = self._sheet()
        if not isinstance(name, str):
            raise ValueError("name not a str")
        name = str(name)
        if not _NAME_RE.match(name) or _REFSHAPE_RE.match(name) or \
                name in _FUNCS:
            raise ValueError("invalid name")
        if not isinstance(target, str):
            raise ValueError("target not a str")
        m = _QTARGET_RE.match(str(target))
        if not m:
            raise ValueError("invalid target")
        qual, a1, a2 = m.groups()
        tsheet = sname if qual is None else qual
        if tsheet not in self._wb._sheets:
            raise ValueError("target sheet does not exist")
        c1, r1 = a1[0], int(a1[1:])
        c2, r2 = (a2[0], int(a2[1:])) if a2 else (c1, r1)
        if c1 > c2 or r1 > r2:
            raise ValueError("mis-ordered target range")
        prev = self._wb._names[sname].get(name)
        self._wb._journaled(
            ("name", sname, name, prev, (tsheet, c1, r1, c2, r2)))
        return None

    @property
    def eval_count(self):
        self._sheet()  # dead-handle access raises even here (R19)
        return 0  # counters are not modeled by the naive reference
