import re
from typing import Any, Union, List, Tuple

# Token types
INT_T = "INT"
REF_T = "REF"
ADD = "ADD"
SUB = "SUB"
MUL = "MUL"
DIV = "DIV"
NEG = "NEG"
EQ = "EQ"
NEQ = "NEQ"
LT = "LT"
LTE = "LTE"
GT = "GT"
GTE = "GTE"
LPAREN = "LPAREN"
RPAREN = "RPAREN"
COLON = "COLON"
EOF = "EOF"

# Function types
SUM_T = "SUM"
MIN_T = "MIN"
MAX_T = "MAX"
COUNT_T = "COUNT"
FUNC_T = "FUNC"

# Range token (created during parsing, not tokenized)
RANGE_T = "RANGE"

# Valid function names
VALID_FUNCS = {SUM_T, MIN_T, MAX_T, COUNT_T}

# Operator precedence and associativity
# Higher number = higher precedence
OP_PREC = {
    ADD: 1, SUB: 1,
    MUL: 2, DIV: 2,
    EQ: 3, NEQ: 3, LT: 3, LTE: 3, GT: 3, GTE: 3,
}
OP_ASSOC = {ADD: "L", SUB: "L", MUL: "L", DIV: "L",
            EQ: "L", NEQ: "L", LT: "L", LTE: "L", GT: "L", GTE: "L"}

# Binary operators (excluding unary minus)
BINARY_OPS = {ADD, SUB, MUL, DIV, EQ, NEQ, LT, LTE, GT, GTE}


def tokenize(formula: str) -> Union[List[Tuple[str, Any]], str]:
    """Tokenize a formula string into a list of (type, value) tuples.
    Returns "#PARSE!" on tokenization errors."""
    tokens = []
    i = 0
    n = len(formula)

    while i < n:
        c = formula[i]

        # Skip whitespace
        if c in " \t":
            i += 1
            continue

        # Numbers
        if c.isdigit():
            j = i
            while j < n and formula[j].isdigit():
                j += 1
            tokens.append((INT_T, int(formula[i:j])))
            i = j
            continue

        # References and function names (A-Z followed by digits, or function names)
        if c.isalpha() and c.isupper():
            j = i
            while j < n and (formula[j].isalpha() or formula[j].isdigit()):
                j += 1
            token_text = formula[i:j]
            # Check if it's a valid function name
            if token_text in VALID_FUNCS:
                tokens.append((FUNC_T, token_text))
            elif re.match(r"^[A-Z]\d+$", token_text):
                tokens.append((REF_T, token_text))
            else:
                return "#PARSE!"  # Invalid identifier (e.g., AA1, AVG)
            i = j
            continue

        # Two-character operators (must check before single-char)
        if i + 1 < n:
            two_char = formula[i:i+2]
            if two_char == "<=":
                tokens.append((LTE, "<="))
                i += 2
                continue
            elif two_char == ">=":
                tokens.append((GTE, ">="))
                i += 2
                continue
            elif two_char == "<>":
                tokens.append((NEQ, "<>"))
                i += 2
                continue

        # Single-character operators and punctuation
        if c == "+":
            tokens.append((ADD, "+"))
        elif c == "-":
            tokens.append((SUB, "-"))
        elif c == "*":
            tokens.append((MUL, "*"))
        elif c == "/":
            tokens.append((DIV, "/"))
        elif c == "<":
            tokens.append((LT, "<"))
        elif c == ">":
            tokens.append((GT, ">"))
        elif c == "=":
            tokens.append((EQ, "="))
        elif c == "(":
            tokens.append((LPAREN, "("))
        elif c == ")":
            tokens.append((RPAREN, ")"))
        elif c == ":":
            tokens.append((COLON, ":"))
        else:
            return "#PARSE!"  # Unknown character

        i += 1

    tokens.append((EOF, None))
    return tokens


def parse(formula: str) -> Union[Any, str]:
    """Parse a formula string (without leading =) into an AST.

    Returns "#PARSE!" on any syntax error.
    Uses iterative parsing for R12 compliance.
    """
    tokens = tokenize(formula)
    if tokens == "#PARSE!" or len(tokens) == 0:
        return "#PARSE!"

    # First pass: parse function calls (FUNC_T ( RANGE ) -> FUNC node)
    tokens = _parse_function_calls(tokens)
    if tokens == "#PARSE!":
        return "#PARSE!"

    # Check for unbalanced parentheses
    depth = 0
    for tok in tokens:
        tok_type = tok[0]
        if tok_type == LPAREN:
            depth += 1
        elif tok_type == RPAREN:
            depth -= 1
        if depth < 0:
            return "#PARSE!"
    if depth != 0:
        return "#PARSE!"

    # Check for invalid token sequences
    for i in range(1, len(tokens)):
        prev_type = tokens[i-1][0]
        curr_type = tokens[i][0]

        # Allow unary minus in specific contexts
        if curr_type == SUB:
            if prev_type in BINARY_OPS | {LPAREN, FUNC_T}:
                continue  # Unary minus is OK here

        # Two single-char operators that should be two-char
        if prev_type in {LT, GT, EQ} and curr_type in {EQ, LT, GT}:
            return "#PARSE!"

        # Other operator sequences are invalid
        if prev_type in BINARY_OPS and curr_type in BINARY_OPS:
            return "#PARSE!"

        # Can't have two literals in a row
        if prev_type in {INT_T, REF_T} and curr_type in {INT_T, REF_T}:
            return "#PARSE!"

        # Can't have literal after close paren
        if prev_type == RPAREN and curr_type in {INT_T, REF_T}:
            return "#PARSE!"

        # Can't have FUNC_T after anything other than operator or start
        if curr_type == FUNC_T:
            if prev_type not in BINARY_OPS | {LPAREN, FUNC_T}:
                return "#PARSE!"

    # Shunting-yard algorithm to convert to RPN, then build AST
    output = []  # AST nodes
    op_stack = []  # operator stack

    def make_node(op, left, right=None):
        if right is not None:
            return (op, left, right)
        else:
            return (op, left)

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        tok_type = tok[0]
        tok_val = tok[1] if len(tok) > 1 else None

        if tok_type in {INT_T, REF_T, FUNC_T}:
            output.append(tok)
        elif tok_type == NEG or (tok_type == SUB and (i == 0 or tokens[i-1][0] in BINARY_OPS | {LPAREN, FUNC_T})):
            # Unary minus - push as NEG operator
            op_stack.append((NEG, None))
        elif tok_type in BINARY_OPS:
            # Binary operator
            while (op_stack and op_stack[-1][0] != LPAREN and
                   op_stack[-1][0] in BINARY_OPS | {NEG} and
                   (OP_PREC.get(op_stack[-1][0], 0) > OP_PREC.get(tok_type, 0) or
                    (OP_PREC.get(op_stack[-1][0], 0) == OP_PREC.get(tok_type, 0) and OP_ASSOC.get(tok_type) == "L"))):
                out_op = op_stack.pop()
                if out_op[0] == NEG:
                    if len(output) < 1:
                        return "#PARSE!"
                    operand = output.pop()
                    output.append(make_node(NEG, operand))
                else:
                    if len(output) < 2:
                        return "#PARSE!"
                    right = output.pop()
                    left = output.pop()
                    output.append(make_node(out_op[0], left, right))
            op_stack.append((tok_type, tok_val))
        elif tok_type == LPAREN:
            op_stack.append((LPAREN, None))
        elif tok_type == RPAREN:
            while op_stack and op_stack[-1][0] != LPAREN:
                out_op = op_stack.pop()
                if out_op[0] == NEG:
                    if len(output) < 1:
                        return "#PARSE!"
                    operand = output.pop()
                    output.append(make_node(NEG, operand))
                else:
                    if len(output) < 2:
                        return "#PARSE!"
                    right = output.pop()
                    left = output.pop()
                    output.append(make_node(out_op[0], left, right))
            if not op_stack:
                return "#PARSE!"  # Unbalanced parens (shouldn't happen due to earlier check)
            op_stack.pop()  # Remove LPAREN
        elif tok_type == COLON:
            # Range syntax should have been handled in function call parsing
            return "#PARSE!"
        elif tok_type == EOF:
            break
        else:
            return "#PARSE!"

        i += 1

    # Pop remaining operators
    while op_stack:
        out_op = op_stack.pop()
        if out_op[0] == LPAREN:
            return "#PARSE!"  # Unbalanced parens
        if out_op[0] == NEG:
            if len(output) < 1:
                return "#PARSE!"
            operand = output.pop()
            output.append(make_node(NEG, operand))
        else:
            if len(output) < 2:
                return "#PARSE!"
            right = output.pop()
            left = output.pop()
            output.append(make_node(out_op[0], left, right))

    if len(output) != 1:
        return "#PARSE!"

    return output[0]


def _parse_function_calls(tokens: List[Tuple[str, Any]]) -> Union[List[Tuple[str, Any]], str]:
    """Parse function calls in the token stream.

    Replaces FUNC_T ( REF : REF ) with (FUNC_T, func_name, RANGE_T, ref1, ref2).
    Returns "#PARSE!" on syntax errors.
    """
    result = []
    i = 0
    n = len(tokens)

    while i < n:
        tok_type, tok_val = tokens[i]

        if tok_type == FUNC_T:
            # Expect: FUNC_T ( RANGE )
            # Check next token is LPAREN
            if i + 1 >= n or tokens[i+1][0] != LPAREN:
                return "#PARSE!"

            # Skip LPAREN
            j = i + 2

            # Skip whitespace tokens (already skipped by tokenizer, but be safe)
            # Parse first REF
            if j >= n or tokens[j][0] != REF_T:
                return "#PARSE!"
            ref1 = tokens[j][1]
            j += 1

            # Skip whitespace (already done by tokenizer)

            # Expect COLON
            if j >= n or tokens[j][0] != COLON:
                return "#PARSE!"
            j += 1

            # Parse second REF
            if j >= n or tokens[j][0] != REF_T:
                return "#PARSE!"
            ref2 = tokens[j][1]
            j += 1

            # Expect RPAREN
            if j >= n or tokens[j][0] != RPAREN:
                return "#PARSE!"

            # Create FUNC node: (FUNC_T, func_name, RANGE_T, ref1, ref2)
            func_node = (FUNC_T, tok_val, RANGE_T, ref1, ref2)
            result.append(func_node)
            i = j + 1  # Skip past RPAREN
        else:
            result.append(tokens[i])
            i += 1

    return result
