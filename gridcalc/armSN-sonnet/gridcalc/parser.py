"""Hand-written tokenizer + recursive-descent parser for gridcalc formulas.

Grammar (see SPEC.md R3):
    expr     := additive ( CMP additive )*
    additive := term ( (+|-) term )*
    term     := factor ( (*|/) factor )*
    factor   := - factor | primary
    primary  := INT | REF | FUNC ( RANGE ) | ( expr )

AST node shapes (plain tuples, no classes):
    ('perr',)                          -- unparseable input -> #PARSE!
    ('int', n)
    ('ref', addr_text)                 -- addr_text is raw letters+digits,
                                           may not denote a real grid cell
    ('neg', count, node)               -- unary minus applied `count` times
    ('bin', op, left, right)           -- op in + - * / = <> < <= > >=
    ('func', name, tl_addr, br_addr)   -- name in SUM MIN MAX COUNT
"""

FUNC_NAMES = ("SUM", "MIN", "MAX", "COUNT")
_CMP_OPS = ("=", "<>", "<", "<=", ">", ">=")
_ADD_OPS = ("+", "-")
_MUL_OPS = ("*", "/")


class _ParseError(Exception):
    pass


def _tokenize(text):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == " " or c == "\t":
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
                    raise _ParseError()
                tokens.append(("REF", letters + digits))
            else:
                tokens.append(("IDENT", letters))
            continue
        if c == "(":
            tokens.append(("(", c)); i += 1; continue
        if c == ")":
            tokens.append((")", c)); i += 1; continue
        if c == ":":
            tokens.append((":", c)); i += 1; continue
        if c == "+":
            tokens.append(("+", c)); i += 1; continue
        if c == "-":
            tokens.append(("-", c)); i += 1; continue
        if c == "*":
            tokens.append(("*", c)); i += 1; continue
        if c == "/":
            tokens.append(("/", c)); i += 1; continue
        if c == "=":
            tokens.append(("=", c)); i += 1; continue
        if c == "<":
            if i + 1 < n and text[i + 1] == "=":
                tokens.append(("<=", "<=")); i += 2; continue
            if i + 1 < n and text[i + 1] == ">":
                tokens.append(("<>", "<>")); i += 2; continue
            tokens.append(("<", c)); i += 1; continue
        if c == ">":
            if i + 1 < n and text[i + 1] == "=":
                tokens.append((">=", ">=")); i += 2; continue
            tokens.append((">", c)); i += 1; continue
        raise _ParseError()
    tokens.append(("EOF", ""))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self._tokens = tokens
        self._pos = 0

    def _peek(self):
        return self._tokens[self._pos]

    def _advance(self):
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, kind):
        tok = self._peek()
        if tok[0] != kind:
            raise _ParseError()
        return self._advance()

    def parse_expr(self):
        node = self.parse_additive()
        while self._peek()[0] in _CMP_OPS:
            op = self._advance()[0]
            rhs = self.parse_additive()
            node = ("bin", op, node, rhs)
        return node

    def parse_additive(self):
        node = self.parse_term()
        while self._peek()[0] in _ADD_OPS:
            op = self._advance()[0]
            rhs = self.parse_term()
            node = ("bin", op, node, rhs)
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self._peek()[0] in _MUL_OPS:
            op = self._advance()[0]
            rhs = self.parse_factor()
            node = ("bin", op, node, rhs)
        return node

    def parse_factor(self):
        count = 0
        while self._peek()[0] == "-":
            self._advance()
            count += 1
        node = self.parse_primary()
        if count:
            return ("neg", count, node)
        return node

    def parse_primary(self):
        tok = self._peek()
        if tok[0] == "INT":
            self._advance()
            return ("int", int(tok[1]))
        if tok[0] == "REF":
            self._advance()
            return ("ref", tok[1])
        if tok[0] == "IDENT":
            name = tok[1]
            if name not in FUNC_NAMES:
                raise _ParseError()
            self._advance()
            self._expect("(")
            tl = self._expect("REF")[1]
            self._expect(":")
            br = self._expect("REF")[1]
            self._expect(")")
            return ("func", name, tl, br)
        if tok[0] == "(":
            self._advance()
            node = self.parse_expr()
            self._expect(")")
            return node
        raise _ParseError()


def parse(text):
    """Parse formula text (without the leading '=') into an AST.

    Never raises: any malformed input yields the ('perr',) sentinel node.
    """
    try:
        tokens = _tokenize(text)
        parser = _Parser(tokens)
        node = parser.parse_expr()
        if parser._peek()[0] != "EOF":
            raise _ParseError()
        return node
    except _ParseError:
        return ("perr",)
