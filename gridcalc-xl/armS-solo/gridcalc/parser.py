"""Recursive-descent parser for the gridcalc formula grammar.

Grammar (R3 + XL extensions):

    expr       := additive ( CMP additive )*
    additive   := term ( (+|-) term )*
    term       := factor ( (*|/) factor )*
    factor     := - factor | primary
    primary    := INT | STRING | REF | NAME | #REF! | ( expr ) | FUNC-CALL
    FUNC-CALL  := SUM | MIN | MAX | COUNT | CONCAT | LEN | IF | NOW '(' [args] ')'
    RANGE-ARG  := RANGE | NAME | #REF!
    RANGE      := REF : REF
    REF        := [$] [A-Z] [$] [0-9]+   (with optional sheet qualifier SHEET! )
    NAME       := [A-Z0-9_][A-Z0-9_]*  (2-32 chars, not func name, not REF shape)
    SHEET      := [A-Za-z][A-Za-z0-9_]*  (1-32 chars, valid sheet-name shape)

Returns an AST (Node) on success, or *None* on parse failure.
"""

from __future__ import annotations

import sys

# R28: Raise recursion limit to handle ~500-deep unary minus towers.
# This is the sole exception to R24's global-state hygiene — set once at
# import, cited here, and the R28 tower case must pass.
sys.setrecursionlimit(10000)

import string

from .ast import (
    BinOp,
    FuncCall,
    HashRef,
    IntLit,
    Name,
    Range,
    Ref,
    StringLit,
    UnaryMinus,
)
from .lexer import (
    Token,
    _T_BANG,
    _T_COLON,
    _T_COMMA,
    _T_DOLLAR,
    _T_EOF,
    _T_GEQ,
    _T_GT,
    _T_HASHREF,
    _T_IDENT,
    _T_INT,
    _T_LEQ,
    _T_LPAREN,
    _T_LT,
    _T_NEQ,
    _T_PLUS,
    _T_RPAREN,
    _T_SLASH,
    _T_STAR,
    _T_STRING,
    _T_MINUS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FUNC_NAMES = frozenset({"SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW"})

_CMP_OPS = frozenset({"=", "<>", "<", "<=", ">", ">="})

_SHEET_NAME_CHARS = frozenset(string.ascii_letters + string.digits + "_")


def _is_valid_sheet_name_shape(s: str) -> bool:
    """Loose sheet-name shape check (used during parsing)."""
    if not s or len(s) > 32:
        return False
    if not s[0].isalpha():
        return False
    return all(c in _SHEET_NAME_CHARS for c in s)


def _is_ref_shape(s: str) -> bool:
    """Does *s* match the REF shape: one uppercase letter then one or more
    ASCII digits?"""
    if len(s) < 2:
        return False
    if not s[0].isupper():
        return False
    return s[1:].isdigit()


def _is_name_shape(s: str) -> bool:
    """Does *s* match the NAME shape (R18)?"""
    if len(s) < 2 or len(s) > 32:
        return False
    if not (s[0].isalpha() or s[0] == "_"):
        return False
    if not all(c in string.ascii_letters + string.digits + "_" for c in s):
        return False
    if _is_ref_shape(s):
        return False
    if s in _FUNC_NAMES:
        return False
    return True


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class _ParseError(Exception):
    pass


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._toks = tokens
        self._pos = 0

    # -- token access --------------------------------------------------------

    def _cur(self) -> Token:
        return self._toks[self._pos]

    def _peek(self, offset: int = 0) -> Token:
        idx = self._pos + offset
        if 0 <= idx < len(self._toks):
            return self._toks[idx]
        return self._toks[-1]

    def _eat(self, type_: str) -> Token | None:
        t = self._cur()
        if t.type == type_:
            self._pos += 1
            return t
        return None

    def _expect(self, type_: str) -> Token:
        t = self._eat(type_)
        if t is None:
            raise _ParseError(f"Expected {type_}, got {self._cur().type}")
        return t

    # -- grammar rules -------------------------------------------------------

    def parse(self) -> object:
        try:
            result = self._expr()
            if self._cur().type != _T_EOF:
                raise _ParseError(
                    f"Trailing token: {self._cur().type} {self._cur().value!r}"
                )
            return result
        except _ParseError:
            return None

    # expr := additive ( CMP additive )*
    def _expr(self) -> object:
        left = self._additive()
        while self._cur().type in _CMP_OPS:
            op = self._cur().value
            self._pos += 1
            right = self._additive()
            left = BinOp(op, left, right)
        return left

    # additive := term ( (+|-) term )*
    def _additive(self) -> object:
        left = self._term()
        while self._cur().type in ("+", "-"):
            op = self._cur().value
            self._pos += 1
            right = self._term()
            left = BinOp(op, left, right)
        return left

    # term := factor ( (*|/) factor )*
    def _term(self) -> object:
        left = self._factor()
        while self._cur().type in ("*", "/"):
            op = self._cur().value
            self._pos += 1
            right = self._factor()
            left = BinOp(op, left, right)
        return left

    # factor := - factor | primary
    def _factor(self) -> object:
        if self._cur().type == "-":
            self._pos += 1
            return UnaryMinus(self._factor())
        return self._primary()

    # primary := INT | STRING | REF | NAME | #REF! | ( expr ) | FUNC-CALL
    def _primary(self) -> object:
        t = self._cur()

        if t.type == _T_INT:
            self._pos += 1
            return IntLit(int(t.value))

        if t.type == _T_STRING:
            self._pos += 1
            return StringLit(t.value)

        if t.type == _T_HASHREF:
            self._pos += 1
            return HashRef()

        if t.type == _T_LPAREN:
            self._pos += 1
            inner = self._expr()
            self._expect(")")
            return inner

        if t.type == _T_DOLLAR:
            # Leading $ for a REF: $[A-Z]$[0-9]+
            self._pos += 1
            return self._parse_ref_body(abs_col=True)

        if t.type != _T_IDENT:
            raise _ParseError(f"Unexpected token: {t.type} {t.value!r}")

        # --- IDENT branch ---
        ident = t.value

        # Sheet qualifier: IDENT followed by !
        if self._peek(1).type == _T_BANG:
            if not _is_valid_sheet_name_shape(ident):
                raise _ParseError(f"Invalid sheet name: {ident!r}")
            self._pos += 2  # consume IDENT + !
            ref = self._parse_ref_body(abs_col=False)
            ref.qualifier = ident
            if self._cur().type == _T_COLON:
                self._pos += 1
                end = self._parse_ref_body(abs_col=False)
                end.qualifier = ident  # qualifier binds whole range
                return Range(ref, end)
            return ref

        # Function call: IDENT followed by (
        if ident in _FUNC_NAMES and self._peek(1).type == "(":
            return self._parse_func_call(ident)

        # REF shape: one uppercase letter then digits
        if _is_ref_shape(ident):
            # The IDENT token contains both column and row (e.g., "A1")
            col = ident[0]
            row_str = ident[1:]
            # Check for leading zero (A01, A0, etc.) - still parse as REF but will evaluate to #REF!
            has_leading_zero = len(row_str) > 1 and row_str[0] == "0"
            row = int(row_str)
            self._pos += 1  # consume IDENT
            # Check for $ after column (e.g., A$1)
            abs_row = False
            if self._cur().type == _T_DOLLAR:
                self._pos += 1
                abs_row = True
            ref = Ref(col, row, False, abs_row, None)
            ref._has_leading_zero = has_leading_zero
            # Check for range
            if self._cur().type == _T_COLON:
                self._pos += 1
                end = self._parse_ref_body()
                return Range(ref, end)
            return ref

        # NAME shape
        if _is_name_shape(ident):
            self._pos += 1
            return Name(ident)

        # Single uppercase letter or other invalid identifier → #PARSE!
        raise _ParseError(f"Unexpected identifier: {ident!r}")

    # -- REF body parsing ----------------------------------------------------
    #
    # Parses: [$] [A-Z] [$] [0-9]+
    # *abs_col* is True if a leading $ was already consumed by the caller.

    def _parse_ref_body(self, abs_col: bool = False) -> Ref:
        t = self._cur()

        # Handle IDENT token that contains both column and row (e.g., "A2")
        if t.type == _T_IDENT and _is_ref_shape(t.value):
            col = t.value[0]
            row = int(t.value[1:])
            self._pos += 1
            return Ref(col, row, abs_col, False, None)

        # Column letter (single uppercase letter)
        if t.type != _T_IDENT or len(t.value) != 1 or not t.value.isupper():
            raise _ParseError(f"Expected column letter, got {t.type} {t.value!r}")
        col = t.value
        self._pos += 1

        # Optional trailing $
        abs_row = False
        if self._cur().type == _T_DOLLAR:
            self._pos += 1
            abs_row = True

        # Row digits
        t = self._cur()
        if t.type != _T_INT:
            raise _ParseError(f"Expected row digits, got {t.type} {t.value!r}")
        row = int(t.value)
        self._pos += 1

        return Ref(col, row, abs_col, abs_row, None)

    # -- RANGE-ARG parsing ---------------------------------------------------

    def _parse_range_arg(self) -> object:
        t = self._cur()

        if t.type == _T_HASHREF:
            self._pos += 1
            return HashRef()

        if t.type == _T_IDENT:
            # Sheet-qualified range
            if self._peek(1).type == _T_BANG:
                ident = t.value
                if not _is_valid_sheet_name_shape(ident):
                    raise _ParseError(f"Invalid sheet name: {ident!r}")
                self._pos += 2
                start = self._parse_ref_body()
                start.qualifier = ident
                self._expect(":")
                end = self._parse_ref_body()
                end.qualifier = ident
                return Range(start, end)

            # REF shape → could be just REF or REF:REF
            if _is_ref_shape(t.value):
                # IDENT token contains both column and row (e.g., "A1")
                col = t.value[0]
                row = int(t.value[1:])
                self._pos += 1  # consume IDENT
                start = Ref(col, row, False, False, None)

                if self._cur().type == _T_COLON:
                    self._pos += 1
                    end_tok = self._cur()
                    if end_tok.type == _T_IDENT and _is_ref_shape(end_tok.value):
                        # End ref also contains both column and row
                        col2 = end_tok.value[0]
                        row2 = int(end_tok.value[1:])
                        self._pos += 1
                        end = Ref(col2, row2, False, False, None)
                        return Range(start, end)
                    else:
                        # End ref is parsed normally
                        end = self._parse_ref_body()
                        return Range(start, end)
                return start

            # NAME shape
            if _is_name_shape(t.value):
                self._pos += 1
                return Name(t.value)

        raise _ParseError(f"Expected RANGE-ARG, got {t.type} {t.value!r}")

    # -- Function calls ------------------------------------------------------

    def _parse_func_call(self, name: str) -> FuncCall:
        # Consume the function name token
        self._pos += 1
        self._expect("(")

        if name == "NOW":
            self._expect(")")
            return FuncCall("NOW", [])

        if name in ("SUM", "MIN", "MAX", "COUNT"):
            arg = self._parse_range_arg()
            self._expect(")")
            return FuncCall(name, [arg])

        if name == "CONCAT":
            args = [self._expr()]
            while self._cur().type == _T_COMMA:
                self._pos += 1
                args.append(self._expr())
            self._expect(")")
            return FuncCall("CONCAT", args)

        if name == "LEN":
            arg = self._expr()
            self._expect(")")
            return FuncCall("LEN", [arg])

        if name == "IF":
            cond = self._expr()
            self._expect(",")
            true_val = self._expr()
            self._expect(",")
            false_val = self._expr()
            self._expect(")")
            return FuncCall("IF", [cond, true_val, false_val])

        raise _ParseError(f"Unknown function: {name}")


def parse(text: str) -> object:
    """Parse a formula text (without the leading '=').

    Returns an AST node on success, or *None* on parse failure.
    """
    from .lexer import tokenize

    tokens = tokenize(text)
    if tokens is None:
        return None
    parser = _Parser(tokens)
    return parser.parse()
