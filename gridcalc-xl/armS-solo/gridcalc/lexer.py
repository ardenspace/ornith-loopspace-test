"""Lexer for gridcalc formula language.

Tokenises the text that follows the leading '=' into a stream of typed
tokens.  Only spaces and tabs are legal whitespace inside a formula.
"""

from __future__ import annotations

import string


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

_T_INT = "INT"
_T_STRING = "STRING"
_T_IDENT = "IDENT"
_T_DOLLAR = "$"
_T_BANG = "!"
_T_COLON = ":"
_T_LPAREN = "("
_T_RPAREN = ")"
_T_COMMA = ","
_T_PLUS = "+"
_T_MINUS = "-"
_T_STAR = "*"
_T_SLASH = "/"
_T_EQ = "="
_T_NEQ = "<>"
_T_LT = "<"
_T_LEQ = "<="
_T_GT = ">"
_T_GEQ = ">="
_T_HASHREF = "#REF!"
_T_EOF = "EOF"


class Token:
    __slots__ = ("type", "value", "pos")

    def __init__(self, type_: str, value: str, pos: int) -> None:
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Token({self.type}, {self.value!r}, {self.pos})"


_DIGITS = set(string.digits)
_ALPHA = set(string.ascii_letters + "_")


def tokenize(text: str) -> list[Token] | None:
    """Return a list of tokens, or *None* if *text* contains an illegal
    character (anything other than the legal formula alphabet)."""

    tokens: list[Token] = []
    i = 0
    n = len(text)

    while i < n:
        c = text[i]

        # --- whitespace (spaces and tabs only) ---
        if c in (" ", "\t"):
            i += 1
            continue

        # --- string literal ---
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 1
            if j >= n:
                return None  # unterminated string
            tokens.append(Token(_T_STRING, text[i + 1 : j], i))
            i = j + 1
            continue

        # --- #REF! ---
        if text[i : i + 5] == "#REF!":
            tokens.append(Token(_T_HASHREF, "#REF!", i))
            i += 5
            continue

        # bare # is illegal
        if c == "#":
            return None

        # --- multi-char operators (must check before single-char) ---
        if i + 1 < n:
            two = text[i : i + 2]
            if two in ("<=", ">=", "<>"):
                tokens.append(Token(two, two, i))
                i += 2
                continue

        # --- single-char operators / punctuation ---
        if c in "+-*/(),:!$<>=":
            tokens.append(Token(c, c, i))
            i += 1
            continue

        # --- integer literal ---
        if c in _DIGITS:
            j = i
            while j < n and text[j] in _DIGITS:
                j += 1
            tokens.append(Token(_T_INT, text[i:j], i))
            i = j
            continue

        # --- identifier ---
        if c in _ALPHA:
            j = i
            while j < n and (text[j] in _DIGITS or text[j] in _ALPHA):
                j += 1
            tokens.append(Token(_T_IDENT, text[i:j], i))
            i = j
            continue

        # any other character is illegal
        return None

    tokens.append(Token(_T_EOF, "", n))
    return tokens
