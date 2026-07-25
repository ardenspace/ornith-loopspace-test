"""Formula parser and evaluator for Phase 2 scalar expressions.

Grammar (R3 Phase 2 slice, formula source after leading '='):

    expr       := additive ( CMP additive )*
    CMP        := = | <> | < | <= | > | >=
    additive   := term ((+|-) term)*
    term       := factor ((*|/) factor)*
    factor     := - factor | primary
    primary    := INT | STR | REF | ( expr )

INT  : one or more ASCII digits (leading zeros allowed, evaluated by numeric value)
STR  : double-quoted string literal (e.g. "hello", ""); R13 uses double-quotes only
REF  : one uppercase A-Z followed by one or more ASCII digits

Spaces and tabs are permitted around tokens. Two-character operators
(<=, >=, <>) must not contain whitespace between their characters.

Returns PARSE_ERROR ("#PARSE!") for any malformed formula text.

Runtime error sentinels:
  - PARSE_ERROR  : "#PARSE!"  (malformed formula text)
  - DIV_ERROR    : "#DIV!"    (division by zero)
  - TYPE_ERROR   : "#TYPE!"   (operand type mismatch, e.g. string in arithmetic)
  - REF_ERROR    : "#REF!"    (invalid cell address in a reference)

The evaluator accepts an optional ``resolve_ref(addr)`` callback that
maps a reference address to a typed cell value.  The callback returns
a ``(kind, value)`` tuple where ``kind`` is one of ``"int"``, ``"str"``,
``"empty"``, or ``"invalid"``.  An optional ``eval_count`` list is
mutated in place to record how many REF nodes were actually evaluated
(left-to-right short-circuit means later operands may be skipped when
an earlier operand produced an error).
"""

PARSE_ERROR = "#PARSE!"
DIV_ERROR = "#DIV!"
TYPE_ERROR = "#TYPE!"
REF_ERROR = "#REF!"
NAME_ERROR = "#NAME!"
OV_ERROR = "#OV!"

# R12 bounds.
_MAX_FORMULA_TEXT_LEN = 512
_MAX_PAREN_DEPTH = 32
_MAX_REACHED_FORMULA_CELLS = 256
_MAX_INT_ABS = 2**63 - 1
_MAX_STR_LEN = 4096


def _is_valid_sheet_name_token(name):
    """Check if a name is a valid sheet name token for qualified references.
    
    Rules:
      - must be non-empty
      - first character: ASCII letter (A-Z, a-z)
      - remaining characters: ASCII letters, digits, underscore
    """
    if not name:
        return False
    first = name[0]
    if not first.isascii() or not first.isalpha():
        return False
    for ch in name[1:]:
        if not ch.isascii():
            return False
        if not (ch.isalpha() or ch.isdigit() or ch == "_"):
            return False
    return True


def _check_formula_bounds(text):
    """Check R12 bounds on formula text length and parenthesis nesting depth.

    Returns True if the formula is within bounds, False otherwise.
    """
    # Check formula text length.
    if len(text) > _MAX_FORMULA_TEXT_LEN:
        return False

    # Check maximum parenthesis nesting depth.
    max_depth = 0
    current_depth = 0
    for ch in text:
        if ch == '(':
            current_depth += 1
            if current_depth > max_depth:
                max_depth = current_depth
            if current_depth > _MAX_PAREN_DEPTH:
                return False
        elif ch == ')':
            current_depth -= 1
            if current_depth < 0:
                return False

    return True


def parse_formula(text, resolve_ref=None, eval_count=None, resolve_count_ref=None, resolve_name=None, resolve_now=None):
    """Parse and evaluate a Phase 2 formula text (the part after the leading '=').

    Returns the numeric result for parseable expressions, or an error
    sentinel string (PARSE_ERROR / DIV_ERROR / TYPE_ERROR / REF_ERROR / OV_ERROR)
    for malformed input, runtime errors, or out-of-bounds formulas.

    ``resolve_ref(addr)`` is an optional callback that maps a reference
    address to a ``(kind, value)`` tuple:

      - (``"int"``, int_val)    for cells containing an int
      - (``"str"``, str_val)    for cells containing a string
      - (``"empty"``, None)     for cells that have never been set
      - (``"invalid"``, None)   for addresses that are not valid cell refs

    ``resolve_name(name)`` is an optional callback that maps a name to a
    ``(kind, value)`` tuple, where value is either a single address string
    or a range string (e.g. "A1:B2"):

      - (``"cell"``, addr)      for a single-cell name binding
      - (``"range"``, range)    for a range name binding
      - (``"invalid"``, None)   for undefined names

    ``eval_count`` is an optional mutable single-element list (e.g. ``[0]``)
    that is incremented once for every REF node actually evaluated.
    Left-to-right short-circuit means later operands are not counted when
    an earlier operand produced an error.
    """
    if eval_count is None:
        eval_count = [0]

    # R12: Check formula text bounds before parsing.
    if not _check_formula_bounds(text):
        return _ErrorValue(PARSE_ERROR)

    try:
        ast_node = _parse_formula_ast(text)
        if ast_node is None:
            return _PARSE_ERR
        return _evaluate(ast_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
    except Exception:
        return _PARSE_ERR


def _parse_formula_ast(text):
    if not _check_formula_bounds(text):
        return None
    tokens = _tokenize(text)
    if tokens is None:
        return None
    pos = [0]
    ast_node = _parse_expr(tokens, pos)
    if ast_node is None or pos[0] != len(tokens):
        return None
    return ast_node


def _ast_contains_now(node):
    if node is None:
        return False
    kind = node[0]
    if kind == 'NOW':
        return True
    if kind in ('INT', 'STR', 'REF', 'QREF', 'RANGE', 'QRANGE', 'NAME', 'ERROR'):
        return False
    if kind == 'FUNC':
        arg = node[2]
        if isinstance(arg, list):
            return any(_ast_contains_now(child) for child in arg)
        return _ast_contains_now(arg)
    if kind in ('ADD', 'MUL', 'CMP'):
        return _ast_contains_now(node[2]) or _ast_contains_now(node[3])
    if kind == 'NEG':
        return _ast_contains_now(node[1])
    if kind == 'IF':
        return (
            _ast_contains_now(node[1])
            or _ast_contains_now(node[2])
            or _ast_contains_now(node[3])
        )
    return False


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _tokenize(text):
    """Convert formula text into a list of (type, value) tokens.

    Returns None if the text contains any invalid character or an invalid
    whitespace pattern inside a two-character operator.
    """
    tokens = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Double-quoted string literal (R13) — check BEFORE whitespace rejection
        # so that newlines, tabs, and control characters inside strings are preserved.
        if ch == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 1
            if j >= n:
                # Unterminated string literal.
                return None
            tokens.append(('STR', text[i + 1:j]))
            i = j + 1
            continue

        # Skip spaces and tabs (only outside string literals).
        if ch in (' ', '\t'):
            i += 1
            continue

        # Reject newlines and other whitespace (only outside string literals).
        if ch.isspace():
            return None

        if text.startswith(REF_ERROR, i):
            tokens.append(('REF_ERROR', REF_ERROR))
            i += len(REF_ERROR)
            continue

        # Integer literal: one or more ASCII digits.
        if '0' <= ch <= '9':
            j = i
            while j < n and '0' <= text[j] <= '9':
                j += 1
            tokens.append(('INT', int(text[i:j])))
            i = j
            continue

        # REF with optional absolute markers before column and/or row.
        if ch == '$':
            j = i + 1
            if j >= n or not ('A' <= text[j] <= 'Z'):
                return None
            j += 1
            if j < n and text[j] == '$':
                j += 1
            start_digits = j
            while j < n and '0' <= text[j] <= '9':
                j += 1
            if j == start_digits:
                return None
            tokens.append(('REF', text[i:j]))
            i = j
            continue

        # Identifier starting with underscore.
        if ch == '_':
            j = i + 1
            while j < n and (('A' <= text[j] <= 'Z') or ('a' <= text[j] <= 'z') or text[j] == '_' or ('0' <= text[j] <= '9')):
                j += 1
            if j == i + 1:
                return None
            tokens.append(('NAME', text[i:j]))
            i = j
            continue

        # Identifier starting with a letter.
        #   - Single uppercase letter followed by one or more digits → REF
        #   - Multi-letter identifier (with or without trailing digits) → NAME
        #   - Single uppercase letter with no following characters → invalid
        #   - Single lowercase letter with no following characters → invalid
        if 'A' <= ch <= 'Z':
            j = i + 1
            # Consume additional letters and underscores (if any).
            while j < n and (('A' <= text[j] <= 'Z') or ('a' <= text[j] <= 'z') or text[j] == '_'):
                j += 1
            has_multi_letter = j > i + 1
            # Consume optional row absolute marker plus trailing digits.
            if not has_multi_letter and j < n and text[j] == '$':
                j += 1
            digit_start = j
            while j < n and '0' <= text[j] <= '9':
                j += 1
            if has_multi_letter:
                # Multi-letter identifier with or without digits — NAME token.
                # Check if followed by ! (with optional whitespace) → SHEET token.
                k = j
                while k < n and text[k] in (' ', '\t'):
                    k += 1
                if k < n and text[k] == '!':
                    # Validate sheet name: must start with letter, rest alphanumeric/underscore
                    if _is_valid_sheet_name_token(text[i:j]):
                        # Check for double !! → PARSE_ERROR
                        if k + 1 < n and text[k + 1] == '!':
                            return None
                        tokens.append(('SHEET', text[i:j]))
                        i = k + 1
                        continue
                    else:
                        # Invalid sheet name (e.g., starts with _) → PARSE_ERROR
                        return None
                tokens.append(('NAME', text[i:j]))
            elif j > digit_start:
                # Exactly one uppercase letter followed by one or more digits — REF.
                # Check if followed by ! (with optional whitespace) → SHEET token.
                k = j
                while k < n and text[k] in (' ', '\t'):
                    k += 1
                if k < n and text[k] == '!':
                    # Validate sheet name: must start with letter, rest alphanumeric/underscore
                    if _is_valid_sheet_name_token(text[i:j]):
                        # Check for double !! → PARSE_ERROR
                        if k + 1 < n and text[k + 1] == '!':
                            return None
                        tokens.append(('SHEET', text[i:j]))
                        i = k + 1
                        continue
                    else:
                        # Invalid sheet name (e.g., starts with _) → PARSE_ERROR
                        return None
                tokens.append(('REF', text[i:j]))
            else:
                # Single uppercase letter with no digits — check if followed by ! → SHEET token.
                k = j
                while k < n and text[k] in (' ', '\t'):
                    k += 1
                if k < n and text[k] == '!':
                    # Validate sheet name: must start with letter, rest alphanumeric/underscore
                    if _is_valid_sheet_name_token(text[i:j]):
                        # Check for double !! → PARSE_ERROR
                        if k + 1 < n and text[k + 1] == '!':
                            return None
                        tokens.append(('SHEET', text[i:j]))
                        i = k + 1
                        continue
                    else:
                        # Invalid sheet name (e.g., starts with _) → PARSE_ERROR
                        return None
                # Single uppercase letter with no digits and no ! — invalid.
                return None
            i = j
            continue

        # Lowercase letter — check if it's a sheet name token (followed by !).
        if 'a' <= ch <= 'z':
            j = i + 1
            # Consume additional letters, digits, and underscores.
            while j < n and (('A' <= text[j] <= 'Z') or ('a' <= text[j] <= 'z') or text[j] == '_' or ('0' <= text[j] <= '9')):
                j += 1
            # Check if followed by ! (with optional whitespace).
            k = j
            while k < n and text[k] in (' ', '\t'):
                k += 1
            if k < n and text[k] == '!':
                # Validate sheet name.
                if _is_valid_sheet_name_token(text[i:j]):
                    # Check for double !! → PARSE_ERROR.
                    if k + 1 < n and text[k + 1] == '!':
                        return None
                    tokens.append(('SHEET', text[i:j]))
                    i = k + 1
                    continue
                else:
                    # Invalid sheet name → PARSE_ERROR.
                    return None
            # Not a sheet name token — lowercase identifier is invalid.
            return None

        # Single-quote is legal inside string literals (handled above);
        # outside strings it is an invalid character.
        if ch == "'":
            return None

        # Single-character operators and parentheses.
        if ch in ('+', '-', '*', '/', '=', '(', ')', ':', ',', '!'):
            tokens.append((ch, ch))
            i += 1
            continue

        # Two-character operators starting with '<'.
        if ch == '<':
            if i + 1 < n:
                nxt = text[i + 1]
                if nxt == '=':
                    tokens.append(('<=', '<='))
                    i += 2
                    continue
                if nxt == '>':
                    tokens.append(('<>', '<>'))
                    i += 2
                    continue
                if nxt == ' ':
                    # Could be "< =" (invalid) or "< 20" (valid). Look past the
                    # space to disambiguate.
                    if i + 2 < n and text[i + 2] == '=':
                        return None
            tokens.append(('<', '<'))
            i += 1
            continue

        # Two-character operators starting with '>'.
        if ch == '>':
            if i + 1 < n:
                nxt = text[i + 1]
                if nxt == '=':
                    tokens.append(('>=', '>='))
                    i += 2
                    continue
                if nxt == ' ':
                    # Could be "> =" (invalid) or "> 20" (valid). Look past the
                    # space to disambiguate.
                    if i + 2 < n and text[i + 2] == '=':
                        return None
            tokens.append(('>', '>'))
            i += 1
            continue

        # Anything else is invalid.
        return None

    return tokens


# ---------------------------------------------------------------------------
# Recursive-descent parser
# ---------------------------------------------------------------------------

_CMP_OPS = {'=', '<>', '<', '<=', '>', '>='}
_ADD_OPS = {'+', '-'}
_MUL_OPS = {'*', '/'}


def _parse_expr(tokens, pos):
    """expr := additive ( CMP additive )*   (left-associative)."""
    left = _parse_additive(tokens, pos)
    if left is None:
        return None
    while pos[0] < len(tokens) and tokens[pos[0]][0] in _CMP_OPS:
        op = tokens[pos[0]][0]
        pos[0] += 1
        right = _parse_additive(tokens, pos)
        if right is None:
            return None
        left = ('CMP', op, left, right)
    return left


def _parse_additive(tokens, pos):
    """additive := term ((+|-) term)*."""
    left = _parse_term(tokens, pos)
    if left is None:
        return None
    while pos[0] < len(tokens) and tokens[pos[0]][0] in _ADD_OPS:
        op = tokens[pos[0]][0]
        pos[0] += 1
        right = _parse_term(tokens, pos)
        if right is None:
            return None
        left = ('ADD', op, left, right)
    return left


def _parse_term(tokens, pos):
    """term := factor ((*|/) factor)*."""
    left = _parse_factor(tokens, pos)
    if left is None:
        return None
    while pos[0] < len(tokens) and tokens[pos[0]][0] in _MUL_OPS:
        op = tokens[pos[0]][0]
        pos[0] += 1
        right = _parse_factor(tokens, pos)
        if right is None:
            return None
        left = ('MUL', op, left, right)
    return left


def _parse_factor(tokens, pos):
    """factor := - factor | primary."""
    if pos[0] < len(tokens) and tokens[pos[0]][0] == '-':
        pos[0] += 1
        operand = _parse_factor(tokens, pos)
        if operand is None:
            return None
        return ('NEG', operand)
    return _parse_primary(tokens, pos)


def _parse_primary(tokens, pos):
    """primary := INT | STR | REF | NAME | ( expr ) | FUNC ( RANGE ) | FUNC ( expr ( , expr )* )."""
    if pos[0] >= len(tokens):
        return None

    tok_type, tok_val = tokens[pos[0]]

    if tok_type == 'INT':
        pos[0] += 1
        return ('INT', tok_val)

    if tok_type == 'STR':
        pos[0] += 1
        return ('STR', tok_val)

    if tok_type == 'REF':
        pos[0] += 1
        # Check if followed by ! → qualified reference
        if pos[0] < len(tokens) and tokens[pos[0]][0] == '!':
            pos[0] += 1  # consume !
            # Parse the reference after !
            if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
                return None
            ref_addr = tokens[pos[0]][1]
            pos[0] += 1
            return ('QREF', ref_addr)
        return ('REF', tok_val)

    if tok_type == 'SHEET':
        # SHEET token: consume it and the following ! (if present)
        sheet_name = tokens[pos[0]][1]
        pos[0] += 1  # consume SHEET
        # The ! should already be consumed by the tokenizer, but handle it if not
        if pos[0] < len(tokens) and tokens[pos[0]][0] == '!':
            pos[0] += 1  # consume !
        # Now parse the REF
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
            return None
        ref1 = tokens[pos[0]][1]
        pos[0] += 1
        # Check if followed by : → qualified range
        if pos[0] < len(tokens) and tokens[pos[0]][0] == ':':
            pos[0] += 1  # consume :
            # Parse the second REF
            if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
                return None
            ref2 = tokens[pos[0]][1]
            pos[0] += 1
            return ('QRANGE', sheet_name, ref1, ref2)
        return ('QREF', sheet_name, ref1)

    if tok_type == 'REF_ERROR':
        pos[0] += 1
        return ('ERROR', REF_ERROR)

    if tok_type == 'NAME':
        # NOW() is the only accepted zero-argument function call.
        if tok_val == 'NOW' and pos[0] + 1 < len(tokens) and tokens[pos[0] + 1][0] == '(':
            return _parse_now_call(tokens, pos)
        # Check if this is IF followed by '(' — parse as IF(cond, then, else).
        if tok_val == 'IF' and pos[0] + 1 < len(tokens) and tokens[pos[0] + 1][0] == '(':
            return _parse_if_call(tokens, pos)
        # Check if this is a range function followed by '('
        if tok_val in ('SUM', 'MIN', 'MAX', 'COUNT') and pos[0] + 1 < len(tokens) and tokens[pos[0] + 1][0] == '(':
            return _parse_func_call(tokens, pos)
        # Check if this is CONCAT or LEN followed by '('
        if tok_val in ('CONCAT', 'LEN') and pos[0] + 1 < len(tokens) and tokens[pos[0] + 1][0] == '(':
            return _parse_func_call_expr(tokens, pos)
        pos[0] += 1
        return ('NAME', tok_val)

    if tok_type == '(':
        pos[0] += 1
        expr = _parse_expr(tokens, pos)
        if expr is None:
            return None
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
            return None
        pos[0] += 1
        return expr

    # Any other token type is not a valid primary.
    return None


def _parse_func_call(tokens, pos):
    """Parse FUNC_NAME ( RANGE ) and return ('FUNC', name, range_node).

    Also handles FUNC_NAME ( NAME ) where NAME is a single-cell or range name.
    """
    func_name = tokens[pos[0]][1]
    pos[0] += 1  # consume FUNC_NAME

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != '(':
        return None
    pos[0] += 1  # consume '('

    # Check if the argument is a NAME token (single-cell or range name).
    if pos[0] < len(tokens) and tokens[pos[0]][0] == 'NAME':
        name_node = ('NAME', tokens[pos[0]][1])
        pos[0] += 1
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
            return None
        pos[0] += 1  # consume ')'
        return ('FUNC', func_name, name_node)

    range_node = _parse_range(tokens, pos)
    if range_node is None:
        return None

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
        return None
    pos[0] += 1  # consume ')'

    return ('FUNC', func_name, range_node)


def _parse_func_call_expr(tokens, pos):
    """Parse FUNC_NAME ( expr ( , expr )* ) and return ('FUNC', name, [expr_nodes]).

    Returns ('FUNC', name, []) for empty call forms like FUNC().
    """
    func_name = tokens[pos[0]][1]
    pos[0] += 1  # consume FUNC_NAME

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != '(':
        return None
    pos[0] += 1  # consume '('

    # Check for empty call: FUNC()
    if pos[0] < len(tokens) and tokens[pos[0]][0] == ')':
        pos[0] += 1  # consume ')'
        return ('FUNC', func_name, [])

    # Parse first expression
    expr = _parse_expr(tokens, pos)
    if expr is None:
        return None

    exprs = [expr]

    # Parse additional comma-separated expressions
    while pos[0] < len(tokens) and tokens[pos[0]][0] == ',':
        pos[0] += 1  # consume ','
        expr = _parse_expr(tokens, pos)
        if expr is None:
            return None
        exprs.append(expr)

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
        return None
    pos[0] += 1  # consume ')'

    return ('FUNC', func_name, exprs)


def _parse_now_call(tokens, pos):
    """Parse exactly NOW() and return a zero-argument clock node."""
    pos[0] += 1  # consume NOW
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != '(':
        return None
    pos[0] += 1  # consume '('
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
        return None
    pos[0] += 1  # consume ')'
    return ('NOW',)


def _parse_range(tokens, pos):
    """Parse RANGE-ARG : RANGE-ARG and return ('RANGE', ref1, ref2).

    Also handles qualified ranges: SHEET ! REF : REF → ('QRANGE', sheet, ref1, ref2).
    """
    # Check if this is a qualified range: SHEET ! REF : REF
    if pos[0] < len(tokens) and tokens[pos[0]][0] == 'SHEET':
        sheet_name = tokens[pos[0]][1]
        pos[0] += 1  # consume SHEET
        # Consume ! if present (tokenizer may or may not have consumed it)
        if pos[0] < len(tokens) and tokens[pos[0]][0] == '!':
            pos[0] += 1
        # Parse first REF
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
            return None
        ref1 = tokens[pos[0]][1]
        pos[0] += 1
        # Check for :
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != ':':
            return None
        pos[0] += 1  # consume :
        # Parse second REF
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
            return None
        ref2 = tokens[pos[0]][1]
        pos[0] += 1
        return ('QRANGE', sheet_name, ref1, ref2)

    # Unqualified range: REF : REF
    if pos[0] >= len(tokens) or tokens[pos[0]][0] not in ('REF', 'REF_ERROR'):
        return None
    ref1 = tokens[pos[0]][1]
    pos[0] += 1

    if ref1 == REF_ERROR and (pos[0] >= len(tokens) or tokens[pos[0]][0] != ':'):
        return ('RANGE', ref1, ref1)

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ':':
        return None
    pos[0] += 1  # consume ':'

    if pos[0] >= len(tokens) or tokens[pos[0]][0] not in ('REF', 'REF_ERROR'):
        return None
    ref2 = tokens[pos[0]][1]
    pos[0] += 1

    return ('RANGE', ref1, ref2)


def _parse_if_call(tokens, pos):
    """Parse IF ( expr , expr , expr ) and return ('IF', cond, then, else).

    IF requires exactly three comma-separated expression arguments.
    """
    # tok_val is 'IF', already consumed by caller.
    pos[0] += 1  # consume IF

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != '(':
        return None
    pos[0] += 1  # consume '('

    # Parse first expression (condition).
    cond = _parse_expr(tokens, pos)
    if cond is None:
        return None

    # Expect comma.
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ',':
        return None
    pos[0] += 1  # consume ','

    # Parse second expression (then branch).
    then_expr = _parse_expr(tokens, pos)
    if then_expr is None:
        return None

    # Expect comma.
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ',':
        return None
    pos[0] += 1  # consume ','

    # Parse third expression (else branch).
    else_expr = _parse_expr(tokens, pos)
    if else_expr is None:
        return None

    # Expect closing paren.
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
        return None
    pos[0] += 1  # consume ')'

    return ('IF', cond, then_expr, else_expr)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------
#
# Internal value representation during evaluation:
#   - ``int``               : a numeric result
#   - ``str``               : a string result (including strings that look
#                             like error codes such as ``"#DIV!"``; these
#                             preserve string provenance)
#   - ``_ErrorValue``       : a runtime error sentinel (distinguished from
#                             ordinary strings by type, not by content)
#
# Public API (``Workbook.get``) converts ``_ErrorValue`` instances to
# plain strings before returning.


class _ErrorValue:
    """Internal sentinel for formula errors.

    Wraps a plain-string error code so the evaluator can distinguish
    errors from ordinary strings (including strings that happen to look
    like error codes).
    """

    __slots__ = ("code",)

    def __init__(self, code):
        self.code = code

    def __eq__(self, other):
        if isinstance(other, _ErrorValue):
            return self.code == other.code
        if isinstance(other, str):
            return self.code == other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash(self.code)

    def __str__(self):
        return self.code

    def __repr__(self):
        return f"_ErrorValue({self.code!r})"


# Internal error sentinel objects (used during evaluation).
_PARSE_ERR = _ErrorValue(PARSE_ERROR)
_DIV_ERR = _ErrorValue(DIV_ERROR)
_TYPE_ERR = _ErrorValue(TYPE_ERROR)
_REF_ERR = _ErrorValue(REF_ERROR)
_NAME_ERR = _ErrorValue(NAME_ERROR)

_ERROR_SET = {_PARSE_ERR, _DIV_ERR, _TYPE_ERR, _REF_ERR, _NAME_ERR}


def _is_error(value):
    """Return True iff *value* is a runtime error sentinel object."""
    return isinstance(value, _ErrorValue)


def _is_string(value):
    """Return True iff *value* is a plain string (not an error sentinel)."""
    return isinstance(value, str)


def _resolve_ref_value(resolve_ref, addr, eval_count):
    """Resolve a reference address via the callback.

    Returns the resolved value (int, string, or ``_ErrorValue``).
    Returns ``_REF_ERR`` if the callback reports an invalid address.
    The caller (workbook) is responsible for incrementing ``eval_count``
    when a formula cell computation starts.
    """
    if resolve_ref is None:
        # No resolver: treat all refs as empty -> int 0.
        return 0
    addr = _strip_abs_ref(addr)
    kind, value = resolve_ref(addr)
    if kind == "invalid":
        return _REF_ERR
    if kind == "int":
        return value
    if kind == "str":
        return value
    if kind == "error":
        # value is an error sentinel string; wrap it.
        return _ErrorValue(value)
    # "empty" or any other kind -> int 0.
    return 0


def _check_int_bounds(value):
    """Check if an integer value is within R12 bounds."""
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > _MAX_INT_ABS:
            return False
    return True


def _check_str_bounds(value):
    """Check if a string value is within R12 bounds."""
    if isinstance(value, str):
        if len(value) > _MAX_STR_LEN:
            return False
    return True


def _evaluate(node, resolve_ref, eval_count, resolve_count_ref=None, resolve_name=None, resolve_now=None):
    """Evaluate an AST node produced by the parser.

    Returns an ``int``, a ``str``, or an ``_ErrorValue``.
    Left-to-right short-circuit is observed: when an operand is an
    error, later operands are not evaluated.
    """
    kind = node[0]

    if kind == 'INT':
        value = node[1]
        # R12: Check integer bounds.
        if not _check_int_bounds(value):
            return _ErrorValue(OV_ERROR)
        return value

    if kind == 'STR':
        value = node[1]
        # R12: Check string bounds.
        if not _check_str_bounds(value):
            return _ErrorValue(OV_ERROR)
        return value

    if kind == 'REF':
        return _resolve_ref_value(resolve_ref, node[1], eval_count)

    if kind == 'NOW':
        value = resolve_now() if resolve_now is not None else 0
        if isinstance(value, bool) or not isinstance(value, int):
            return _TYPE_ERR
        if not _check_int_bounds(value):
            return _ErrorValue(OV_ERROR)
        return value

    if kind == 'QREF':
        # Qualified reference: node is ('QREF', sheet_name, ref_addr)
        sheet_name = node[1]
        ref_addr = node[2]
        # Pass sheet qualifier to resolve_ref via a wrapper
        def _resolve_with_sheet(addr):
            if resolve_ref:
                return resolve_ref(addr, sheet_name)
            return ('empty', None)
        return _resolve_ref_value(_resolve_with_sheet, ref_addr, eval_count)

    if kind == 'QRANGE':
        # Qualified range: node is ('QRANGE', sheet_name, ref1, ref2)
        # This is only valid as a function argument, not as a primary expression.
        # Return #PARSE! if used as a primary.
        return _PARSE_ERR

    if kind == 'ERROR':
        return _ErrorValue(node[1])

    if kind == 'NAME':
        # Resolve the name.
        if resolve_name is None:
            return _NAME_ERR
        name = node[1]
        result = resolve_name(name)
        if result is None or result == ("invalid", None):
            return _NAME_ERR
        name_kind, name_value = result
        if name_kind == "cell":
            # Single-cell name: resolve to the cell's value.
            if resolve_ref is None:
                return 0
            sheet_name = None
            ref_name = name_value
            if isinstance(name_value, str) and "!" in name_value:
                sheet_name, ref_name = name_value.split("!", 1)
            cell_kind, cell_value = resolve_ref(ref_name, sheet_name) if sheet_name is not None else resolve_ref(ref_name)
            if cell_kind == "invalid":
                return _REF_ERR
            if cell_kind == "int":
                return cell_value
            if cell_kind == "str":
                return cell_value
            if cell_kind == "error":
                return _ErrorValue(cell_value)
            # "empty" or any other kind -> int 0.
            return 0
        elif name_kind == "range":
            # Range name used as primary: return #REF!.
            return _REF_ERR
        else:
            return _NAME_ERR

    if kind == 'CMP':
        _, op, left_node, right_node = node
        left = _evaluate(left_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        if _is_error(left):
            return left
        # Short-circuit: if left is a string and the op is a string-ordering
        # operator (<, <=, >, >=), return #TYPE! without evaluating right.
        if _is_string(left) and op in ('<', '<=', '>', '>='):
            return _TYPE_ERR
        right = _evaluate(right_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        if _is_error(right):
            return right
        # Both sides resolved to non-error values.
        if _is_string(left) and _is_string(right):
            # Same-type string comparison: only = and <> permitted (R13).
            if op == '=':
                return 1 if left == right else 0
            if op == '<>':
                return 1 if left != right else 0
            # String orderings (<, <=, >, >=) not permitted -> #TYPE!
            return _TYPE_ERR
        if isinstance(left, int) and isinstance(right, int):
            # R12: Check integer bounds for comparison operands.
            if not _check_int_bounds(left) or not _check_int_bounds(right):
                return _ErrorValue(OV_ERROR)
            # Same-type int comparison: return 1/0.
            if op == '=':
                return 1 if left == right else 0
            if op == '<>':
                return 1 if left != right else 0
            if op == '<':
                return 1 if left < right else 0
            if op == '<=':
                return 1 if left <= right else 0
            if op == '>':
                return 1 if left > right else 0
            if op == '>=':
                return 1 if left >= right else 0
        # Mixed types (int vs string) -> #TYPE!
        return _TYPE_ERR

    if kind == 'ADD':
        _, op, left_node, right_node = node
        left = _evaluate(left_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        if _is_error(left):
            return left
        # Short-circuit: if left is a string, don't evaluate right.
        if _is_string(left):
            return _TYPE_ERR
        right = _evaluate(right_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        if _is_error(right):
            return right
        # Both sides resolved. Check for string operands.
        if _is_string(right):
            return _TYPE_ERR
        if op == '+':
            result = left + right
            # R12: Check integer bounds.
            if isinstance(result, int) and not isinstance(result, bool):
                if abs(result) > _MAX_INT_ABS:
                    return _ErrorValue(OV_ERROR)
            return result
        if op == '-':
            result = left - right
            # R12: Check integer bounds.
            if isinstance(result, int) and not isinstance(result, bool):
                if abs(result) > _MAX_INT_ABS:
                    return _ErrorValue(OV_ERROR)
            return result

    if kind == 'MUL':
        _, op, left_node, right_node = node
        left = _evaluate(left_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        if _is_error(left):
            return left
        # Short-circuit: if left is a string, don't evaluate right.
        if _is_string(left):
            return _TYPE_ERR
        right = _evaluate(right_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        if _is_error(right):
            return right
        # Both sides resolved. Check for string operands.
        if _is_string(right):
            return _TYPE_ERR
        if op == '*':
            result = left * right
            # R12: Check integer bounds.
            if isinstance(result, int) and not isinstance(result, bool):
                if abs(result) > _MAX_INT_ABS:
                    return _ErrorValue(OV_ERROR)
            return result
        if op == '/':
            if right == 0:
                return _DIV_ERR
            # R12: Check integer bounds for operands.
            if not _check_int_bounds(left) or not _check_int_bounds(right):
                return _ErrorValue(OV_ERROR)
            # Truncate toward zero.
            quotient = int(left / right)
            # R12: Check integer bounds for result.
            if abs(quotient) > _MAX_INT_ABS:
                return _ErrorValue(OV_ERROR)
            return quotient

    if kind == 'NEG':
        operand = _evaluate(node[1], resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        if _is_error(operand):
            return operand
        if _is_string(operand):
            return _TYPE_ERR
        result = -operand
        # R12: Check integer bounds.
        if isinstance(result, int) and not isinstance(result, bool):
            if abs(result) > _MAX_INT_ABS:
                return _ErrorValue(OV_ERROR)
        return result

    if kind == 'IF':
        return _evaluate_if(node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)

    if kind == 'FUNC':
        return _evaluate_func(node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)

    raise ValueError(f"Unknown AST node kind: {kind!r}")


# ---------------------------------------------------------------------------
# Range function evaluation (SUM, MIN, MAX, COUNT)
# ---------------------------------------------------------------------------

def _strip_abs_ref(addr):
    return addr.replace('$', '')


def _is_valid_address(addr):
    """Return True iff *addr* is a valid cell address per R1.

    Rules:
      - must be str or str subclass
      - exactly one uppercase letter A-Z
      - followed by ASCII digits representing integer 1-99
      - no leading zeros (so 'A01' is invalid, 'A1' is valid)
    """
    if not isinstance(addr, str):
        return False
    addr = _strip_abs_ref(addr)
    if len(addr) < 2:
        return False
    if not ('A' <= addr[0] <= 'Z'):
        return False
    digits = addr[1:]
    if not digits.isdigit():
        return False
    if len(digits) > 2:
        return False
    if digits[0] == '0':
        return False
    row = int(digits)
    if row < 1 or row > 99:
        return False
    return True


def _parse_address(addr):
    """Parse an address like 'A1' into (col_letter, row_int)."""
    addr = _strip_abs_ref(addr)
    return addr[0], int(addr[1:])


def _generate_range_cells(ref1, ref2):
    """Generate cell addresses in row-major order for range ref1:ref2.

    Returns a list of address strings.
    """
    col1, row1 = _parse_address(ref1)
    col2, row2 = _parse_address(ref2)

    cells = []
    for row in range(row1, row2 + 1):
        for col_ord in range(ord(col1), ord(col2) + 1):
            cells.append(f"{chr(col_ord)}{row}")
    return cells


def _evaluate_func(node, resolve_ref, eval_count, resolve_count_ref=None, resolve_name=None, resolve_now=None):
    """Evaluate a FUNC node with a range argument or expression arguments."""
    _, func_name, arg = node

    # Check if this is an expression-based function (CONCAT, LEN)
    if isinstance(arg, list):
        # Expression-based function
        if func_name == 'CONCAT':
            return _eval_concat(arg, resolve_ref, eval_count, resolve_name, resolve_now)
        elif func_name == 'LEN':
            return _eval_len(arg, resolve_ref, eval_count, resolve_name, resolve_now)
        # Unknown expression-based function
        return _PARSE_ERR

    # Range-based function (SUM, MIN, MAX, COUNT)
    # Check if the range argument is a NAME token that needs to be resolved.
    sheet_qualifier = None
    if isinstance(arg, tuple) and len(arg) == 2 and arg[0] == 'NAME':
        # Resolve the name to its target range.
        if resolve_name is None:
            return _NAME_ERR
        name = arg[1]
        result = resolve_name(name)
        if result is None or result == ("invalid", None):
            return _NAME_ERR
        name_kind, name_value = result
        if name_kind == "range":
            # Range name: parse the range string and evaluate.
            if "!" in name_value:
                sheet_qualifier, rest = name_value.split("!", 1)
                ref1, ref2 = rest.split(":")
            else:
                ref1, ref2 = name_value.split(":")
        elif name_kind == "cell":
            # Single-cell name: treat as a 1x1 range.
            if "!" in name_value:
                sheet_qualifier, ref1 = name_value.split("!", 1)
                ref2 = ref1
            else:
                ref1 = ref2 = name_value
        else:
            return _NAME_ERR
    elif isinstance(arg, tuple) and len(arg) == 4 and arg[0] == 'QRANGE':
        # Qualified range: ('QRANGE', sheet_name, ref1, ref2)
        sheet_qualifier = arg[1]
        ref1 = arg[2]
        ref2 = arg[3]
    else:
        # Original range-based function logic.
        _, ref1, ref2 = arg

    # Validate range endpoints
    if ref1 == REF_ERROR or ref2 == REF_ERROR:
        return _REF_ERR
    if not _is_valid_address(ref1) or not _is_valid_address(ref2):
        return _REF_ERR

    # Parse endpoints and validate ordering
    col1, row1 = _parse_address(ref1)
    col2, row2 = _parse_address(ref2)

    if col1 > col2 or row1 > row2:
        return _REF_ERR

    # Generate row-major cell addresses
    cells = _generate_range_cells(ref1, ref2)

    # Evaluate based on function name
    if func_name == 'SUM':
        return _eval_sum(cells, resolve_ref, eval_count, sheet_qualifier)
    elif func_name == 'MIN':
        return _eval_min(cells, resolve_ref, eval_count, sheet_qualifier)
    elif func_name == 'MAX':
        return _eval_max(cells, resolve_ref, eval_count, sheet_qualifier)
    elif func_name == 'COUNT':
        return _eval_count(cells, resolve_ref, resolve_count_ref, sheet_qualifier)

    # Should not reach here (parser rejects unknown callees)
    return _PARSE_ERR


def _eval_sum(cells, resolve_ref, eval_count, sheet_qualifier=None):
    """Evaluate SUM over a list of cell addresses."""
    total = 0
    for addr in cells:
        if resolve_ref is None:
            # No resolver: treat all refs as empty -> int 0.
            kind, value = 'empty', None
        else:
            kind, value = resolve_ref(addr, sheet_qualifier) if sheet_qualifier else resolve_ref(addr)
        if kind == 'empty':
            continue
        if kind == 'str':
            return _TYPE_ERR
        if kind == 'int':
            total += value
            if abs(total) > _MAX_INT_ABS:
                return _ErrorValue(OV_ERROR)
        if kind == 'error':
            return _ErrorValue(value)
    return total


def _eval_min(cells, resolve_ref, eval_count, sheet_qualifier=None):
    """Evaluate MIN over a list of cell addresses."""
    min_val = None
    for addr in cells:
        if resolve_ref is None:
            kind, value = 'empty', None
        else:
            kind, value = resolve_ref(addr, sheet_qualifier) if sheet_qualifier else resolve_ref(addr)
        if kind == 'empty':
            continue
        if kind == 'str':
            return _TYPE_ERR
        if kind == 'int':
            if abs(value) > _MAX_INT_ABS:
                return _ErrorValue(OV_ERROR)
            if min_val is None or value < min_val:
                min_val = value
        if kind == 'error':
            return _ErrorValue(value)
    if min_val is None:
        return _TYPE_ERR
    return min_val


def _eval_max(cells, resolve_ref, eval_count, sheet_qualifier=None):
    """Evaluate MAX over a list of cell addresses."""
    max_val = None
    for addr in cells:
        if resolve_ref is None:
            kind, value = 'empty', None
        else:
            kind, value = resolve_ref(addr, sheet_qualifier) if sheet_qualifier else resolve_ref(addr)
        if kind == 'empty':
            continue
        if kind == 'str':
            return _TYPE_ERR
        if kind == 'int':
            if abs(value) > _MAX_INT_ABS:
                return _ErrorValue(OV_ERROR)
            if max_val is None or value > max_val:
                max_val = value
        if kind == 'error':
            return _ErrorValue(value)
    if max_val is None:
        return _TYPE_ERR
    return max_val


def _eval_count(cells, resolve_ref, resolve_count_ref=None, sheet_qualifier=None):
    """Evaluate COUNT structurally over a list of cell addresses."""
    count = 0
    resolver = resolve_count_ref if resolve_count_ref is not None else resolve_ref
    for addr in cells:
        if resolver is None:
            kind, value = 'empty', None
        else:
            kind, value = resolver(addr, sheet_qualifier) if sheet_qualifier else resolver(addr)
        if kind == 'invalid':
            return _REF_ERR
        if kind != 'empty':
            count += 1
    return count


def _render_value(value):
    """Render a value as a string for CONCAT/LEN.

    - int: base-10 representation (no leading zeros, leading '-' for negatives)
    - str: preserved as-is
    - _ErrorValue: returned as-is (caller handles short-circuit)
    """
    if isinstance(value, _ErrorValue):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    # Fallback (should not reach here)
    return str(value)


def _eval_concat(exprs, resolve_ref, eval_count, resolve_name=None, resolve_now=None):
    """Evaluate CONCAT over a list of expression nodes.

    Evaluates arguments left-to-right, short-circuits on first error.
    Renders ints as base-10 strings, preserves strings as-is.
    Empty-cell references render as "0" (handled by _resolve_ref_value).
    """
    if not exprs:
        # CONCAT() with no arguments -> #PARSE!
        return _PARSE_ERR

    result_parts = []
    for expr_node in exprs:
        value = _evaluate(expr_node, resolve_ref, eval_count, resolve_name=resolve_name, resolve_now=resolve_now)
        if _is_error(value):
            return value
        rendered = _render_value(value)
        if _is_error(rendered):
            return rendered
        result_parts.append(rendered)

    result = ''.join(result_parts)
    if len(result) > _MAX_STR_LEN:
        return _ErrorValue(OV_ERROR)
    return result


def _eval_len(exprs, resolve_ref, eval_count, resolve_name=None, resolve_now=None):
    """Evaluate LEN over a single expression node.

    Returns the character count of the string or decimal-rendered int.
    """
    if len(exprs) != 1:
        # LEN with wrong arity -> #PARSE!
        return _PARSE_ERR

    expr_node = exprs[0]
    value = _evaluate(expr_node, resolve_ref, eval_count, resolve_name=resolve_name, resolve_now=resolve_now)
    if _is_error(value):
        return value
    rendered = _render_value(value)
    if _is_error(rendered):
        return rendered
    return len(rendered)


# ---------------------------------------------------------------------------
# IF function evaluation (R15)
# ---------------------------------------------------------------------------

def _evaluate_if(node, resolve_ref, eval_count, resolve_count_ref=None, resolve_name=None, resolve_now=None):
    """Evaluate an IF node: IF(cond, then_expr, else_expr).

    Per R15:
    - The condition is evaluated first.
    - An error condition returns that error.
    - A string condition returns #TYPE!.
    - An integer condition selects the then branch when nonzero and the
      else branch when zero.
    - Only the selected branch is evaluated; the unselected branch is
      never evaluated, even when it contains errors or formula cells.
    - The selected branch may return any type, including errors and strings.
    """
    _, cond_node, then_node, else_node = node

    # Evaluate the condition first.
    cond_value = _evaluate(cond_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)

    # Error condition: return the error.
    if _is_error(cond_value):
        return cond_value

    # String condition: return #TYPE!.
    if _is_string(cond_value):
        return _TYPE_ERR

    # Integer condition: select branch.
    if isinstance(cond_value, int) and not isinstance(cond_value, bool):
        if cond_value != 0:
            # Nonzero: select then branch.
            return _evaluate(then_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)
        else:
            # Zero: select else branch.
            return _evaluate(else_node, resolve_ref, eval_count, resolve_count_ref, resolve_name, resolve_now)

    # Any other type (should not happen given the grammar, but be safe):
    return _TYPE_ERR
