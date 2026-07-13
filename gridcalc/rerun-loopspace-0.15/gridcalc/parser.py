"""Formula parser — tokenizer + recursive-descent parser for core grammar."""
import re

# Token types
INT = "INT"
REF = "REF"
ADD = "ADD"
SUB = "SUB"
MUL = "MUL"
DIV = "DIV"
NEG = "NEG"
LT = "LT"
LTE = "LTE"
GT = "GT"
GTE = "GTE"
EQ = "EQ"
NEQ = "NEQ"
LPAREN = "LPAREN"
RPAREN = "RPAREN"
COLON = "COLON"

# Function names
FUNC_SUM = "SUM"
FUNC_MIN = "MIN"
FUNC_MAX = "MAX"
FUNC_COUNT = "COUNT"
VALID_FUNCTIONS = {FUNC_SUM, FUNC_MIN, FUNC_MAX, FUNC_COUNT}


class ParseError(Exception):
    """Raised when formula text cannot be parsed per the grammar."""
    pass


def tokenize(formula):
    """Tokenize formula text into a list of (type, value) tuples.

    Args:
        formula: Formula text (without leading '=')

    Returns:
        List of (type, value) tuples

    Raises:
        ParseError: If tokenization fails
    """
    tokens = []
    i = 0
    while i < len(formula):
        c = formula[i]

        # Skip whitespace (spaces and tabs)
        if c in " \t":
            i += 1
            continue

        # Numbers
        if c.isdigit():
            j = i
            while j < len(formula) and formula[j].isdigit():
                j += 1
            tokens.append((INT, int(formula[i:j])))
            i = j
            continue

        # Identifiers (A-Z followed by alphanumeric characters)
        if c.isalpha() and c.isupper():
            j = i + 1
            # Read all alphanumeric characters
            while j < len(formula) and (formula[j].isalpha() or formula[j].isdigit()):
                j += 1
            ident_text = formula[i:j]

            # Check if it's a valid function name
            if ident_text in VALID_FUNCTIONS:
                tokens.append((ident_text, None))  # Function token
            elif j > i + 1 and ident_text[1:].isdigit():
                # Single-letter reference (e.g., A1, Z99) — letter followed by digits only
                tokens.append((REF, ident_text))
            else:
                # Multi-letter identifier or letter without digits — this is #PARSE!
                raise ParseError(f"Invalid identifier: {ident_text!r}")
            i = j
            continue

        # Two-character operators
        if i + 1 < len(formula):
            two_char = formula[i:i+2]
            if two_char == "<=":
                tokens.append((LTE, None))
                i += 2
                continue
            elif two_char == ">=":
                tokens.append((GTE, None))
                i += 2
                continue
            elif two_char == "<>":
                tokens.append((NEQ, None))
                i += 2
                continue

        # Single-character operators
        if c == "+":
            tokens.append((ADD, None))
            i += 1
            continue
        elif c == "-":
            tokens.append((SUB, None))
            i += 1
            continue
        elif c == "*":
            tokens.append((MUL, None))
            i += 1
            continue
        elif c == "/":
            tokens.append((DIV, None))
            i += 1
            continue
        elif c == "<":
            tokens.append((LT, None))
            i += 1
            continue
        elif c == ">":
            tokens.append((GT, None))
            i += 1
            continue
        elif c == "=":
            tokens.append((EQ, None))
            i += 1
            continue
        elif c == ":":
            tokens.append((COLON, None))
            i += 1
            continue
        elif c == "(":
            tokens.append((LPAREN, None))
            i += 1
            continue
        elif c == ")":
            tokens.append((RPAREN, None))
            i += 1
            continue

        # Unknown character
        raise ParseError(f"Unknown character: {c!r}")

    return tokens


def parse(formula):
    """Parse formula text into an AST.

    Args:
        formula: Formula text (without leading '=')

    Returns:
        AST node (tuple)

    Raises:
        ParseError: If parsing fails
    """
    if not formula:
        raise ParseError("Empty formula")

    tokens = tokenize(formula)
    if not tokens:
        raise ParseError("Empty formula after tokenization")

    parser = _Parser(tokens)
    ast = parser.parse_expression()

    if parser.pos < len(tokens):
        raise ParseError(f"Unexpected token: {tokens[parser.pos]}")

    return ast


class _Parser:
    """Recursive-descent parser with precedence climbing."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type=None):
        token = self.peek()
        if token is None:
            raise ParseError("Unexpected end of input")
        if expected_type and token[0] != expected_type:
            raise ParseError(f"Expected {expected_type}, got {token[0]}")
        self.pos += 1
        return token

    def parse_expression(self):
        """Parse additive expression (lowest precedence)."""
        left = self.parse_comparison()

        while self.peek() and self.peek()[0] in (LT, LTE, GT, GTE, EQ, NEQ):
            op = self.consume()[0]
            right = self.parse_comparison()
            left = (op, left, right)

        return left

    def parse_comparison(self):
        """Parse additive expression (comparisons have same precedence as additive per spec)."""
        return self.parse_additive()

    def parse_additive(self):
        """Parse additive expression (+ and -)."""
        left = self.parse_multiplicative()

        while self.peek() and self.peek()[0] in (ADD, SUB):
            op = self.consume()[0]
            right = self.parse_multiplicative()
            left = (op, left, right)

        return left

    def parse_multiplicative(self):
        """Parse multiplicative expression (* and /)."""
        left = self.parse_unary()

        while self.peek() and self.peek()[0] in (MUL, DIV):
            op = self.consume()[0]
            right = self.parse_unary()
            left = (op, left, right)

        return left

    def parse_unary(self):
        """Parse unary expression (negation)."""
        if self.peek() and self.peek()[0] == SUB:
            self.consume()
            operand = self.parse_unary()
            return (NEG, operand)
        return self.parse_primary()

    def parse_primary(self):
        """Parse primary expression (INT, REF, FUNC(RANGE), or parenthesized expression)."""
        token = self.peek()

        if token is None:
            raise ParseError("Unexpected end of input")

        if token[0] == INT:
            self.consume()
            return token

        if token[0] == REF:
            self.consume()
            # Check if this is a range outside a function (should be #PARSE!)
            if self.peek() and self.peek()[0] == COLON:
                raise ParseError("Range outside function call")
            return token

        if token[0] in VALID_FUNCTIONS:
            func_name = self.consume()[0]
            self.consume(LPAREN)
            # Parse range: REF : REF
            start_ref = self.consume(REF)
            self.consume(COLON)
            end_ref = self.consume(REF)
            self.consume(RPAREN)
            return (func_name, (start_ref[1], end_ref[1]))

        if token[0] == LPAREN:
            self.consume()
            expr = self.parse_expression()
            self.consume(RPAREN)
            return expr

        # Unknown token type
        raise ParseError(f"Unexpected token: {token}")
