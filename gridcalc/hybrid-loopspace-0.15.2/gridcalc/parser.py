from dataclasses import dataclass


PARSE_ERROR = "#PARSE!"

# R3: Only these function names are recognized.
_KNOWN_FUNCS = frozenset({"SUM", "MIN", "MAX", "COUNT"})

# R12: Size, depth, and magnitude bounds.
# Parser enforces source text length and parenthesis nesting depth.
_MAX_SOURCE_LEN = 512
_MAX_PAREN_DEPTH = 32


@dataclass(frozen=True)
class IntLiteral:
    text: str
    value: int


@dataclass(frozen=True)
class Ref:
    name: str


@dataclass(frozen=True)
class Range:
    start: Ref
    end: Ref


@dataclass(frozen=True)
class FuncCall:
    name: str
    arg: Range


@dataclass(frozen=True)
class UnaryOp:
    op: str
    operand: object


@dataclass(frozen=True)
class BinaryOp:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Group:
    expr: object


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str


class _ParseFailure(Exception):
    pass


def parse(source):
    try:
        text = str(source)
        if text.startswith("="):
            text = text[1:]
        if len(text) > _MAX_SOURCE_LEN:
            return PARSE_ERROR
        tokens = _tokenize(text)
        parser = _Parser(tokens)
        result = parser.expr(depth=0)
        parser.expect("EOF")
        return result
    except Exception:
        return PARSE_ERROR


def _tokenize(source):
    tokens = []
    pos = 0
    two_char_ops = {"<=", ">=", "<>"}
    single_char = {"+", "-", "*", "/", ":", "(", ")", "=", "<", ">"}

    while pos < len(source):
        char = source[pos]
        if char in " \t":
            pos += 1
        elif char.isascii() and char.isdigit():
            start = pos
            while pos < len(source) and source[pos].isascii() and source[pos].isdigit():
                pos += 1
            text = source[start:pos]
            tokens.append(_Token("INT", text))
        elif "A" <= char <= "Z":
            start = pos
            pos += 1
            if pos < len(source) and source[pos].isascii() and source[pos].isdigit():
                while pos < len(source) and source[pos].isascii() and source[pos].isdigit():
                    pos += 1
                tokens.append(_Token("REF", source[start:pos]))
            else:
                while pos < len(source) and "A" <= source[pos] <= "Z":
                    pos += 1
                tokens.append(_Token("IDENT", source[start:pos]))
        elif source[pos : pos + 2] in two_char_ops:
            tokens.append(_Token("OP", source[pos : pos + 2]))
            pos += 2
        elif char in single_char:
            tokens.append(_Token("OP", char))
            pos += 1
        else:
            raise _ParseFailure

    tokens.append(_Token("EOF", ""))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def expr(self, depth=0):
        node = self.additive(depth)
        while self.peek().text in {"=", "<>", "<", "<=", ">", ">="}:
            op = self.advance().text
            node = BinaryOp(op=op, left=node, right=self.additive(depth))
        return node

    def additive(self, depth=0):
        node = self.term(depth)
        while self.peek().text in {"+", "-"}:
            op = self.advance().text
            node = BinaryOp(op=op, left=node, right=self.term(depth))
        return node

    def term(self, depth=0):
        node = self.factor(depth)
        while self.peek().text in {"*", "/"}:
            op = self.advance().text
            node = BinaryOp(op=op, left=node, right=self.factor(depth))
        return node

    def factor(self, depth=0):
        if self.peek().text == "-":
            op = self.advance().text
            return UnaryOp(op=op, operand=self.factor(depth))
        return self.primary(depth)

    def primary(self, depth=0):
        token = self.peek()
        if token.kind == "INT":
            self.advance()
            return IntLiteral(text=token.text, value=int(token.text))
        if token.kind == "IDENT" and token.text in _KNOWN_FUNCS:
            return self._parse_func_call()
        if token.kind == "REF":
            self.advance()
            return Ref(name=token.text)
        if token.text == "(":
            if depth + 1 > _MAX_PAREN_DEPTH:
                raise _ParseFailure
            self.advance()
            node = self.expr(depth + 1)
            self.expect_text(")")
            return Group(expr=node)
        raise _ParseFailure

    def _parse_func_call(self):
        func_token = self.advance()
        self.expect_text("(")
        start = self._parse_ref()
        self.expect_text(":")
        end = self._parse_ref()
        self.expect_text(")")
        return FuncCall(name=func_token.text, arg=Range(start=start, end=end))

    def _parse_ref(self):
        token = self.peek()
        if token.kind == "REF":
            self.advance()
            return Ref(name=token.text)
        raise _ParseFailure

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        token = self.peek()
        self.pos += 1
        return token

    def expect(self, kind):
        token = self.advance()
        if token.kind != kind:
            raise _ParseFailure
        return token

    def expect_text(self, text):
        token = self.advance()
        if token.text != text:
            raise _ParseFailure
        return token
