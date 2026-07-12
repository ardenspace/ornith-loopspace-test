"""Formula tokenizer and recursive-descent parser for gridcalc."""

from __future__ import annotations

import re

# ── token types ──────────────────────────────────────────────────────
T_INT = "INT"
T_REF = "REF"
T_FUNC = "FUNC"
T_LPAREN = "LPAREN"
T_RPAREN = "RPAREN"
T_COLON = "COLON"
T_PLUS = "PLUS"
T_MINUS = "MINUS"
T_STAR = "STAR"
T_SLASH = "SLASH"
T_EQ = "EQ"        # =
T_NE = "NE"        # <>
T_LT = "LT"        # <
T_LE = "LE"        # <=
T_GT = "GT"        # >
T_GE = "GE"        # >=
T_EOF = "EOF"
T_ERROR = "ERROR"

_CMP_TOKENS = {T_EQ, T_NE, T_LT, T_LE, T_GT, T_GE}
_FUNC_NAMES = {"SUM", "MIN", "MAX", "COUNT"}


class ParseError:
    """Sentinel returned by parse() on malformed input."""
    __slots__ = ()

    def __repr__(self):
        return "#PARSE!"


PARSE_ERROR = ParseError()


# ── tokenizer ────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[tuple[str, str]]:
    """Yield (type, value) pairs from formula text (without leading '=')."""
    tokens: list[tuple[str, str]] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        # skip whitespace
        if c in " \t":
            i += 1
            continue
        # two-char operators (must check before single-char)
        if i + 1 < n:
            two = text[i : i + 2]
            if two == "<=":
                tokens.append((T_LE, "<="))
                i += 2
                continue
            if two == ">=":
                tokens.append((T_GE, ">="))
                i += 2
                continue
            if two == "<>":
                tokens.append((T_NE, "<>"))
                i += 2
                continue
        # single-char operators / punctuation
        if c == "+":
            tokens.append((T_PLUS, "+")); i += 1; continue
        if c == "-":
            tokens.append((T_MINUS, "-")); i += 1; continue
        if c == "*":
            tokens.append((T_STAR, "*")); i += 1; continue
        if c == "/":
            tokens.append((T_SLASH, "/")); i += 1; continue
        if c == "(":
            tokens.append((T_LPAREN, "(")); i += 1; continue
        if c == ")":
            tokens.append((T_RPAREN, ")")); i += 1; continue
        if c == ":":
            tokens.append((T_COLON, ":")); i += 1; continue
        if c == "=":
            tokens.append((T_EQ, "=")); i += 1; continue
        if c == "<":
            tokens.append((T_LT, "<")); i += 1; continue
        if c == ">":
            tokens.append((T_GT, ">")); i += 1; continue
        # digits → INT
        if c.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            tokens.append((T_INT, text[i:j]))
            i = j
            continue
        # letter → could be FUNC, REF, or unknown identifier
        if c.isalpha():
            j = i
            while j < n and text[j].isalpha():
                j += 1
            word = text[i:j]
            if word in _FUNC_NAMES:
                tokens.append((T_FUNC, word))
                i = j
            elif len(word) == 1 and word.isupper():
                # single uppercase letter — check for digits after
                k = j
                while k < n and text[k].isdigit():
                    k += 1
                if k > j:
                    tokens.append((T_REF, text[i:k]))
                    i = k
                else:
                    # single letter with no digits → malformed
                    tokens.append((T_ERROR, word))
                    i = j
            else:
                # multi-letter non-func or lowercase → error
                tokens.append((T_ERROR, word))
                i = j
            continue
        # anything else → unparseable
        return [(T_EOF, "")]
    tokens.append((T_EOF, ""))
    return tokens


# ── AST node types ───────────────────────────────────────────────────

class IntLit:
    __slots__ = ("value",)
    def __init__(self, value: int):
        self.value = value

class Ref:
    __slots__ = ("addr",)
    def __init__(self, addr: str):
        self.addr = addr

class FuncCall:
    __slots__ = ("name", "range_ref_tl", "range_ref_br")
    def __init__(self, name: str, tl: str, br: str):
        self.name = name
        self.range_ref_tl = tl
        self.range_ref_br = br

class BinOp:
    __slots__ = ("op", "left", "right")
    def __init__(self, op: str, left, right):
        self.op = op
        self.left = left
        self.right = right

class UnaryMinus:
    __slots__ = ("operand",)
    def __init__(self, operand):
        self.operand = operand


# ── parser ───────────────────────────────────────────────────────────

class _Parser:
    """Recursive-descent parser for the formula grammar."""

    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> tuple[str, str]:
        return self.tokens[self.pos]

    def consume(self, expected_type: str | None = None) -> tuple[str, str]:
        tok = self.tokens[self.pos]
        if expected_type is not None and tok[0] != expected_type:
            raise SyntaxError
        self.pos += 1
        return tok

    def at_end(self) -> bool:
        return self.tokens[self.pos][0] in (T_EOF, T_ERROR)

    # expr := additive ( CMP additive )*
    def parse_expr(self):
        left = self.parse_additive()
        while self.peek()[0] in _CMP_TOKENS:
            op = self.consume()[1]  # store actual character
            right = self.parse_additive()
            left = BinOp(op, left, right)
        return left

    # additive := term ( (+|-) term )*
    def parse_additive(self):
        left = self.parse_term()
        while self.peek()[0] in (T_PLUS, T_MINUS):
            op = self.consume()[1]  # store actual character
            right = self.parse_term()
            left = BinOp(op, left, right)
        return left

    # term := factor ( (*|/) factor )*
    def parse_term(self):
        left = self.parse_factor()
        while self.peek()[0] in (T_STAR, T_SLASH):
            op = self.consume()[1]  # store actual character
            right = self.parse_factor()
            left = BinOp(op, left, right)
        return left

    # factor := - factor | primary
    def parse_factor(self):
        if self.peek()[0] == T_MINUS:
            self.consume()
            operand = self.parse_factor()
            return UnaryMinus(operand)
        return self.parse_primary()

    # primary := INT | REF | FUNC ( RANGE ) | ( expr )
    def parse_primary(self):
        tok = self.peek()
        if tok[0] == T_ERROR:
            raise SyntaxError
        if tok[0] == T_INT:
            self.consume()
            return IntLit(int(tok[1]))
        if tok[0] == T_REF:
            self.consume()
            return Ref(tok[1])
        if tok[0] == T_FUNC:
            return self.parse_func_call()
        if tok[0] == T_LPAREN:
            self.consume()
            expr = self.parse_expr()
            try:
                self.consume(T_RPAREN)
            except SyntaxError:
                raise SyntaxError
            return expr
        raise SyntaxError

    def parse_func_call(self):
        name_tok = self.consume()
        name = name_tok[1]
        try:
            self.consume(T_LPAREN)
        except SyntaxError:
            raise SyntaxError
        # RANGE := REF : REF
        tl_tok = self.peek()
        if tl_tok[0] != T_REF:
            raise SyntaxError
        tl = self.consume()[1]
        try:
            colon_tok = self.consume(T_COLON)
        except SyntaxError:
            raise SyntaxError
        br_tok = self.peek()
        if br_tok[0] != T_REF:
            raise SyntaxError
        br = self.consume()[1]
        try:
            self.consume(T_RPAREN)
        except SyntaxError:
            raise SyntaxError
        return FuncCall(name, tl, br)


def parse(formula_text: str):
    """Parse a formula string (with or without leading '=').

    Returns an AST node on success, or PARSE_ERROR on any parse failure.
    """
    text = formula_text
    if text.startswith("="):
        text = text[1:]
    if not text.strip():
        return PARSE_ERROR
    tokens = _tokenize(text)
    if tokens[0][0] == T_EOF:
        return PARSE_ERROR
    try:
        p = _Parser(tokens)
        ast = p.parse_expr()
        if not p.at_end():
            return PARSE_ERROR
        return ast
    except (SyntaxError, ValueError, IndexError):
        return PARSE_ERROR


def extract_deps(ast):
    """Extract the set of cell addresses referenced by an AST.

    For RANGE args, expands to all cells in the range (row-major).
    Returns a set of address strings.
    For PARSE_ERROR or invalid ranges, returns empty set.
    """
    if ast is PARSE_ERROR:
        return set()

    deps = set()
    _extract_deps_recursive(ast, deps)
    return deps


def _extract_deps_recursive(node, deps: set):
    """Recursively extract dependencies from AST."""
    if isinstance(node, IntLit):
        return
    if isinstance(node, UnaryMinus):
        _extract_deps_recursive(node.operand, deps)
        return
    if isinstance(node, BinOp):
        _extract_deps_recursive(node.left, deps)
        _extract_deps_recursive(node.right, deps)
        return
    if isinstance(node, Ref):
        # Only add valid addresses
        from gridcalc.evaluator import _valid_addr
        if _valid_addr(node.addr):
            deps.add(node.addr)
        return
    if isinstance(node, FuncCall):
        from gridcalc.evaluator import _iter_range, _valid_addr
        # Check if range is valid
        tl_parsed = None
        br_parsed = None
        if _valid_addr(node.range_ref_tl):
            tl_parsed = (node.range_ref_tl[0], int(node.range_ref_tl[1:]))
        if _valid_addr(node.range_ref_br):
            br_parsed = (node.range_ref_br[0], int(node.range_ref_br[1:]))
        if tl_parsed and br_parsed:
            tl_col_ord = ord(tl_parsed[0]) - ord("A") + 1
            br_col_ord = ord(br_parsed[0]) - ord("A") + 1
            if tl_col_ord <= br_col_ord and tl_parsed[1] <= br_parsed[1]:
                # valid range — expand to all cells
                for r in range(tl_parsed[1], br_parsed[1] + 1):
                    for c_ord in range(tl_col_ord, br_col_ord + 1):
                        c_letter = chr(ord("A") + c_ord - 1)
                        deps.add(f"{c_letter}{r}")
        # COUNT doesn't participate in cycle detection but still has deps for invalidation
        return
