"""Independent naive reference model for differential tests.

This module implements a completely independent formula parser and evaluator
that does NOT delegate to gridcalc.formula.parse_formula. It has its own
tokenizer, parser, and evaluator to catch shared parser/evaluator bugs.
"""

import re

# Valid address pattern: exactly one uppercase A-Z followed by row 1-99
# with no leading zeros.
_ADDRESS_PATTERN = r"[A-Z]([1-9]|[1-9][0-9])"
_REF_PATTERN = r"\$?[A-Z]\$?([1-9]|[1-9][0-9])"
_RESERVED_NAMES = frozenset({"SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW"})


def _is_valid_address(addr):
    """Return True iff *addr* is a valid cell address per R1."""
    return isinstance(addr, str) and bool(re.fullmatch(_REF_PATTERN, addr))


def _strip_abs_ref(addr):
    return addr.replace('$', '')


def _is_valid_unqualified_address(addr):
    return isinstance(addr, str) and bool(re.fullmatch(_ADDRESS_PATTERN, addr))


def _is_valid_name(name):
    if not isinstance(name, str) or len(name) < 2 or len(name) > 32:
        return False
    first = name[0]
    if not (('A' <= first <= 'Z') or first == '_'):
        return False
    for ch in name[1:]:
        if not (('A' <= ch <= 'Z') or ch.isdigit() or ch == '_'):
            return False
    if re.fullmatch(r"[A-Z][0-9]+", name):
        return False
    return name.upper() not in _RESERVED_NAMES


def _is_valid_sheet_name(name):
    if not isinstance(name, str) or not name or len(name) > 32:
        return False
    first = name[0]
    if not first.isascii() or not first.isalpha():
        return False
    for ch in name[1:]:
        if not ch.isascii() or not (ch.isalpha() or ch.isdigit() or ch == '_'):
            return False
    return True


def _is_valid_target(target):
    if not isinstance(target, str):
        return False
    if ':' not in target:
        return _is_valid_unqualified_address(target)
    parts = target.split(':')
    if len(parts) != 2:
        return False
    start, end = parts
    if not _is_valid_unqualified_address(start) or not _is_valid_unqualified_address(end):
        return False
    start_col, start_row = _ref_parse_address(start)
    end_col, end_row = _ref_parse_address(end)
    return start_col <= end_col and start_row <= end_row


def _is_valid_target_for_sheets(target, sheets):
    if not isinstance(target, str):
        return False
    if '!' not in target:
        return _is_valid_target(target)
    if target.count('!') != 1:
        return False
    sheet, rest = target.split('!')
    return _is_valid_sheet_name(sheet) and sheet in sheets and _is_valid_target(rest)


def _split_name_target(target):
    sheet_name = None
    rest = target
    if '!' in target:
        sheet_name, rest = target.split('!', 1)
    if ':' in rest:
        ref1, ref2 = rest.split(':', 1)
        return sheet_name, ref1, ref2
    return sheet_name, rest, None


def _parse_qualified_cell_arg(text, default_sheet, sheets):
    if not isinstance(text, str):
        raise ValueError("Cell argument must be str")
    text = str(text)
    if '!' not in text:
        if not _is_valid_address(text):
            raise ValueError(f"Invalid cell argument: {text!r}")
        return default_sheet, text
    if text.count('!') != 1:
        raise ValueError(f"Invalid qualified cell argument: {text!r}")
    sheet, addr = text.split('!')
    if not _is_valid_sheet_name(sheet) or not _is_valid_address(addr):
        raise ValueError(f"Invalid qualified cell argument: {text!r}")
    if sheet not in sheets:
        raise ValueError(f"Unknown sheet: {sheet!r}")
    return sheet, addr


def _public(value):
    """Convert internal error sentinel to plain string for public API."""
    if hasattr(value, 'code'):
        return value.code
    return value


# ---------------------------------------------------------------------------
# Independent formula parser and evaluator
# ---------------------------------------------------------------------------

# Error sentinels (matching gridcalc.formula)
PARSE_ERROR = "#PARSE!"
DIV_ERROR = "#DIV!"
TYPE_ERROR = "#TYPE!"
REF_ERROR = "#REF!"
NAME_ERROR = "#NAME!"
OV_ERROR = "#OV!"


class _RefErrorValue:
    """Internal error sentinel for the reference model's evaluator."""
    __slots__ = ("code",)

    def __init__(self, code):
        self.code = code

    def __eq__(self, other):
        if isinstance(other, _RefErrorValue):
            return self.code == other.code
        if isinstance(other, str):
            return self.code == other
        return NotImplemented

    def __hash__(self):
        return hash(self.code)

    def __str__(self):
        return self.code


_REF_PARSE_ERR = _RefErrorValue(PARSE_ERROR)
_REF_DIV_ERR = _RefErrorValue(DIV_ERROR)
_REF_TYPE_ERR = _RefErrorValue(TYPE_ERROR)
_REF_REF_ERR = _RefErrorValue(REF_ERROR)
_REF_NAME_ERR = _RefErrorValue(NAME_ERROR)


def _ref_is_error(value):
    return isinstance(value, _RefErrorValue)


def _ref_is_string(value):
    return isinstance(value, str)


# R12 bounds (matching gridcalc.formula)
_MAX_FORMULA_TEXT_LEN = 512
_MAX_PAREN_DEPTH = 32
_MAX_INT_ABS = 2**63 - 1
_MAX_STR_LEN = 4096


def _ref_check_formula_bounds(text):
    """Check R12 bounds on formula text length and parenthesis nesting depth."""
    if len(text) > _MAX_FORMULA_TEXT_LEN:
        return False

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


def _ref_tokenize(text):
    """Convert formula text into a list of (type, value) tokens."""
    tokens = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Skip spaces and tabs.
        if ch in (' ', '\t'):
            i += 1
            continue

        # Reject newlines and other whitespace.
        if ch.isspace():
            return None

        if ch.isascii() and ch.isalpha():
            j = i + 1
            while j < n and text[j].isascii() and (text[j].isalpha() or text[j].isdigit() or text[j] == '_'):
                j += 1
            if j < n and text[j] == '!' and _is_valid_sheet_name(text[i:j]):
                tokens.append(('SHEET', text[i:j]))
                i = j + 1
                continue

        # REF_ERROR token: #REF!
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

        if ch == '$':
            j = i + 1
            if j >= n or not ('A' <= text[j] <= 'Z'):
                return None
            j += 1
            if j < n and text[j] == '$':
                j += 1
            digit_start = j
            while j < n and '0' <= text[j] <= '9':
                j += 1
            if j == digit_start:
                return None
            tokens.append(('REF', text[i:j]))
            i = j
            continue

        if ch == '_':
            j = i + 1
            while j < n and (('A' <= text[j] <= 'Z') or ('a' <= text[j] <= 'z') or text[j] == '_' or text[j].isdigit()):
                j += 1
            if j == i + 1:
                return None
            tokens.append(('NAME', text[i:j]))
            i = j
            continue

        # Identifier starting with uppercase letter.
        if 'A' <= ch <= 'Z':
            j = i + 1
            while j < n and (('A' <= text[j] <= 'Z') or ('a' <= text[j] <= 'z') or text[j] == '_'):
                j += 1
            has_multi_letter = j > i + 1
            if not has_multi_letter and j < n and text[j] == '$':
                j += 1
            digit_start = j
            while j < n and '0' <= text[j] <= '9':
                j += 1
            if has_multi_letter:
                tokens.append(('NAME', text[i:j]))
            elif j > digit_start:
                tokens.append(('REF', text[i:j]))
            else:
                return None
            i = j
            continue

        # Lowercase letter — invalid identifier.
        if 'a' <= ch <= 'z':
            return None

        # Single-quote is not valid in Phase 2 (R13 uses double-quotes).
        if ch == "'":
            return None

        # Double-quoted string literal (R13).
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

        # Single-character operators and parentheses.
        if ch in ('+', '-', '*', '/', '=', '(', ')', ':', ','):
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


def _ref_parse_expr(tokens, pos):
    """expr := additive ( CMP additive )*   (left-associative)."""
    left = _ref_parse_additive(tokens, pos)
    if left is None:
        return None
    while pos[0] < len(tokens) and tokens[pos[0]][0] in _CMP_OPS:
        op = tokens[pos[0]][0]
        pos[0] += 1
        right = _ref_parse_additive(tokens, pos)
        if right is None:
            return None
        left = ('CMP', op, left, right)
    return left


def _ref_parse_additive(tokens, pos):
    """additive := term ((+|-) term)*."""
    left = _ref_parse_term(tokens, pos)
    if left is None:
        return None
    while pos[0] < len(tokens) and tokens[pos[0]][0] in _ADD_OPS:
        op = tokens[pos[0]][0]
        pos[0] += 1
        right = _ref_parse_term(tokens, pos)
        if right is None:
            return None
        left = ('ADD', op, left, right)
    return left


def _ref_parse_term(tokens, pos):
    """term := factor ((*|/) factor)*."""
    left = _ref_parse_factor(tokens, pos)
    if left is None:
        return None
    while pos[0] < len(tokens) and tokens[pos[0]][0] in _MUL_OPS:
        op = tokens[pos[0]][0]
        pos[0] += 1
        right = _ref_parse_factor(tokens, pos)
        if right is None:
            return None
        left = ('MUL', op, left, right)
    return left


def _ref_parse_factor(tokens, pos):
    """factor := - factor | primary."""
    if pos[0] < len(tokens) and tokens[pos[0]][0] == '-':
        pos[0] += 1
        operand = _ref_parse_factor(tokens, pos)
        if operand is None:
            return None
        return ('NEG', operand)
    return _ref_parse_primary(tokens, pos)


def _ref_parse_primary(tokens, pos):
    """primary := INT | STR | REF | REF_ERROR | NAME | ( expr ) | FUNC ( RANGE ) | FUNC ( expr ( , expr )* )."""
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
        return ('REF', tok_val)

    if tok_type == 'SHEET':
        sheet_name = tok_val
        pos[0] += 1
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
            return None
        ref1 = tokens[pos[0]][1]
        pos[0] += 1
        if pos[0] < len(tokens) and tokens[pos[0]][0] == ':':
            pos[0] += 1
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
        # Check if this is IF followed by '(' — parse as IF(cond, then, else).
        if tok_val == 'IF' and pos[0] + 1 < len(tokens) and tokens[pos[0] + 1][0] == '(':
            return _ref_parse_if_call(tokens, pos)
        # Check if this is a range function followed by '('
        if tok_val in ('SUM', 'MIN', 'MAX', 'COUNT') and pos[0] + 1 < len(tokens) and tokens[pos[0] + 1][0] == '(':
            return _ref_parse_func_call(tokens, pos)
        # Check if this is CONCAT or LEN followed by '('
        if tok_val in ('CONCAT', 'LEN') and pos[0] + 1 < len(tokens) and tokens[pos[0] + 1][0] == '(':
            return _ref_parse_func_call_expr(tokens, pos)
        pos[0] += 1
        return ('NAME', tok_val)

    if tok_type == '(':
        pos[0] += 1
        expr = _ref_parse_expr(tokens, pos)
        if expr is None:
            return None
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
            return None
        pos[0] += 1
        return expr

    # Any other token type is not a valid primary.
    return None


def _ref_parse_func_call(tokens, pos):
    """Parse FUNC_NAME ( RANGE ) and return ('FUNC', name, range_node)."""
    func_name = tokens[pos[0]][1]
    pos[0] += 1  # consume FUNC_NAME

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != '(':
        return None
    pos[0] += 1  # consume '('

    if pos[0] < len(tokens) and tokens[pos[0]][0] == 'NAME':
        name_node = ('NAME', tokens[pos[0]][1])
        pos[0] += 1
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
            return None
        pos[0] += 1
        return ('FUNC', func_name, name_node)

    range_node = _ref_parse_range(tokens, pos)
    if range_node is None:
        return None

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
        return None
    pos[0] += 1  # consume ')'

    return ('FUNC', func_name, range_node)


def _ref_parse_func_call_expr(tokens, pos):
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
    expr = _ref_parse_expr(tokens, pos)
    if expr is None:
        return None

    exprs = [expr]

    # Parse additional comma-separated expressions
    while pos[0] < len(tokens) and tokens[pos[0]][0] == ',':
        pos[0] += 1  # consume ','
        expr = _ref_parse_expr(tokens, pos)
        if expr is None:
            return None
        exprs.append(expr)

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
        return None
    pos[0] += 1  # consume ')'

    return ('FUNC', func_name, exprs)


def _ref_parse_range(tokens, pos):
    """Parse REF : REF or REF_ERROR : REF_ERROR and return ('RANGE', ref1, ref2)."""
    if pos[0] < len(tokens) and tokens[pos[0]][0] == 'SHEET':
        sheet_name = tokens[pos[0]][1]
        pos[0] += 1
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
            return None
        ref1 = tokens[pos[0]][1]
        pos[0] += 1
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != ':':
            return None
        pos[0] += 1
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != 'REF':
            return None
        ref2 = tokens[pos[0]][1]
        pos[0] += 1
        return ('QRANGE', sheet_name, ref1, ref2)

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


def _ref_parse_if_call(tokens, pos):
    """Parse IF ( expr , expr , expr ) and return ('IF', cond, then, else).

    IF requires exactly three comma-separated expression arguments.
    """
    # tok_val is 'IF', already consumed by caller.
    pos[0] += 1  # consume IF

    if pos[0] >= len(tokens) or tokens[pos[0]][0] != '(':
        return None
    pos[0] += 1  # consume '('

    # Parse first expression (condition).
    cond = _ref_parse_expr(tokens, pos)
    if cond is None:
        return None

    # Expect comma.
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ',':
        return None
    pos[0] += 1  # consume ','

    # Parse second expression (then branch).
    then_expr = _ref_parse_expr(tokens, pos)
    if then_expr is None:
        return None

    # Expect comma.
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ',':
        return None
    pos[0] += 1  # consume ','

    # Parse third expression (else branch).
    else_expr = _ref_parse_expr(tokens, pos)
    if else_expr is None:
        return None

    # Expect closing paren.
    if pos[0] >= len(tokens) or tokens[pos[0]][0] != ')':
        return None
    pos[0] += 1  # consume ')'

    return ('IF', cond, then_expr, else_expr)


# ---------------------------------------------------------------------------
# Independent evaluator
# ---------------------------------------------------------------------------

def _ref_parse_address(addr):
    """Parse an address like 'A1' into (col_letter, row_int)."""
    addr = _strip_abs_ref(addr)
    return addr[0], int(addr[1:])


def _ref_generate_range_cells(ref1, ref2):
    """Generate cell addresses in row-major order for range ref1:ref2."""
    col1, row1 = _ref_parse_address(ref1)
    col2, row2 = _ref_parse_address(ref2)

    cells = []
    for row in range(row1, row2 + 1):
        for col_ord in range(ord(col1), ord(col2) + 1):
            cells.append(f"{chr(col_ord)}{row}")
    return cells


def _ref_parse_copy_ref(text, i):
    if text.startswith(REF_ERROR, i):
        return {"start": i, "end": i + len(REF_ERROR), "ref_error": True, "text": REF_ERROR}
    j = i
    col_abs = False
    row_abs = False
    if j < len(text) and text[j] == '$':
        col_abs = True
        j += 1
    if j >= len(text) or not ('A' <= text[j] <= 'Z'):
        return None
    if j + 1 < len(text) and 'A' <= text[j + 1] <= 'Z':
        return None
    col = text[j]
    j += 1
    if j < len(text) and text[j] == '$':
        row_abs = True
        j += 1
    digit_start = j
    while j < len(text) and text[j].isdigit():
        j += 1
    if j == digit_start:
        return None
    if j < len(text) and (text[j].isalnum() or text[j] == '_'):
        return None
    return {
        "start": i, "end": j, "ref_error": False, "text": text[i:j],
        "col_abs": col_abs, "row_abs": row_abs, "col": col,
        "row_text": text[digit_start:j],
    }


def _ref_parse_qualified_copy_ref(text, i):
    if i > 0 and (text[i - 1].isalnum() or text[i - 1] in ('_', '$')):
        return None
    j = i
    if j >= len(text) or not text[j].isascii() or not text[j].isalpha():
        return None
    j += 1
    while j < len(text) and text[j].isascii() and (text[j].isalpha() or text[j].isdigit() or text[j] == '_'):
        j += 1
    if j >= len(text) or text[j] != '!':
        return None
    token = _ref_parse_copy_ref(text, j + 1)
    if token is None or token["ref_error"]:
        return None
    token = dict(token)
    token["start"] = i
    token["end"] = token["end"]
    token["text"] = text[i:token["end"]]
    token["bare_text"] = text[j + 1:token["end"]]
    token["prefix"] = text[i:j + 1]
    return token


def _ref_copy_tokens(text):
    tokens = []
    i = 0
    while i < len(text):
        if text[i] == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 1
            i += 1
            continue
        qtoken = _ref_parse_qualified_copy_ref(text, i)
        if qtoken is not None:
            tokens.append(qtoken)
            i = qtoken["end"]
            continue
        if text[i] == '#' or text[i] == '$' or ('A' <= text[i] <= 'Z'):
            prev = text[i - 1] if i > 0 else ''
            if prev and (prev.isalnum() or prev in ('_', '$')):
                i += 1
                continue
            token = _ref_parse_copy_ref(text, i)
            if token is not None:
                tokens.append(token)
                i = token["end"]
                continue
        i += 1
    return tokens


def _ref_shift_copy_ref(token, delta_col, delta_row):
    if token["ref_error"]:
        return REF_ERROR, False
    unmarked = _strip_abs_ref(token.get("bare_text", token["text"]))
    if not _is_valid_unqualified_address(unmarked):
        return token["text"], False
    col_ord = ord(token["col"])
    row = int(token["row_text"])
    if not token["col_abs"]:
        col_ord += delta_col
    if not token["row_abs"]:
        row += delta_row
    if col_ord < ord('A') or col_ord > ord('Z') or row < 1 or row > 99:
        return REF_ERROR, True
    col_part = ("$" if token["col_abs"] else "") + chr(col_ord)
    row_part = ("$" if token["row_abs"] else "") + str(row)
    return token.get("prefix", "") + col_part + row_part, False


def _ref_rewrite_formula_for_copy(text, delta_col, delta_row):
    tokens = _ref_copy_tokens(text)
    pieces = []
    pos = 0
    i = 0
    while i < len(tokens):
        first = tokens[i]
        if i + 1 < len(tokens):
            second = tokens[i + 1]
            between = text[first["end"]:second["start"]]
            if between.strip(' \t') == ':' and len(between.strip(' \t')) == 1:
                first_text, first_left = _ref_shift_copy_ref(first, delta_col, delta_row)
                second_text, second_left = _ref_shift_copy_ref(second, delta_col, delta_row)
                pieces.append(text[pos:first["start"]])
                if first_left or second_left:
                    pieces.append(REF_ERROR)
                else:
                    pieces.append(first_text + between + second_text)
                pos = second["end"]
                i += 2
                continue
        shifted, left_grid = _ref_shift_copy_ref(first, delta_col, delta_row)
        pieces.append(text[pos:first["start"]])
        pieces.append(REF_ERROR if left_grid else shifted)
        pos = first["end"]
        i += 1
    pieces.append(text[pos:])
    return ''.join(pieces)


def _ref_check_int_bounds(value):
    """Check if an integer value is within R12 bounds."""
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > _MAX_INT_ABS:
            return False
    return True


def _ref_check_str_bounds(value):
    """Check if a string value is within R12 bounds."""
    if isinstance(value, str):
        if len(value) > _MAX_STR_LEN:
            return False
    return True


def _ref_evaluate(node, resolve_ref, eval_count, resolve_count_ref=None, resolve_name=None):
    """Evaluate an AST node produced by the parser."""
    kind = node[0]

    if kind == 'INT':
        value = node[1]
        if not _ref_check_int_bounds(value):
            return _RefErrorValue(OV_ERROR)
        return value

    if kind == 'STR':
        value = node[1]
        if not _ref_check_str_bounds(value):
            return _RefErrorValue(OV_ERROR)
        return value

    if kind == 'REF':
        if resolve_ref is None:
            return 0
        kind, value = resolve_ref(_strip_abs_ref(node[1]))
        if kind == "invalid":
            return _RefErrorValue(REF_ERROR)
        if kind == "int":
            return value
        if kind == "str":
            return value
        if kind == "error":
            return _RefErrorValue(value)
        # "empty" or any other kind -> int 0.
        return 0

    if kind == 'QREF':
        if resolve_ref is None:
            return 0
        _, sheet_name, ref_addr = node
        kind, value = resolve_ref(_strip_abs_ref(ref_addr), sheet_name)
        if kind == "invalid":
            return _RefErrorValue(REF_ERROR)
        if kind == "int":
            return value
        if kind == "str":
            return value
        if kind == "error":
            return _RefErrorValue(value)
        return 0

    if kind == 'QRANGE':
        return _RefErrorValue(PARSE_ERROR)

    if kind == 'ERROR':
        return _RefErrorValue(node[1])

    if kind == 'NAME':
        if resolve_name is None:
            return _RefErrorValue(NAME_ERROR)
        name = node[1]
        result = resolve_name(name)
        if result is None or result == ("invalid", None):
            return _RefErrorValue(NAME_ERROR)
        name_kind, name_value = result
        if name_kind == "cell":
            # Single-cell name: resolve to the cell's value.
            if resolve_ref is None:
                return 0
            sheet_name = None
            ref_name = name_value
            if isinstance(name_value, str) and '!' in name_value:
                sheet_name, ref_name = name_value.split('!', 1)
            cell_kind, cell_value = resolve_ref(ref_name, sheet_name) if sheet_name is not None else resolve_ref(ref_name)
            if cell_kind == "invalid":
                return _RefErrorValue(REF_ERROR)
            if cell_kind == "int":
                return cell_value
            if cell_kind == "str":
                return cell_value
            if cell_kind == "error":
                return _RefErrorValue(cell_value)
            # "empty" or any other kind -> int 0.
            return 0
        elif name_kind == "range":
            # Range name used as primary: return #REF!.
            return _RefErrorValue(REF_ERROR)
        else:
            return _RefErrorValue(NAME_ERROR)

    if kind == 'CMP':
        _, op, left_node, right_node = node
        left = _ref_evaluate(left_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)
        if _ref_is_error(left):
            return left
        if _ref_is_string(left) and op in ('<', '<=', '>', '>='):
            return _RefErrorValue(TYPE_ERROR)
        right = _ref_evaluate(right_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)
        if _ref_is_error(right):
            return right
        if _ref_is_string(left) and _ref_is_string(right):
            if op == '=':
                return 1 if left == right else 0
            if op == '<>':
                return 1 if left != right else 0
            return _RefErrorValue(TYPE_ERROR)
        if isinstance(left, int) and isinstance(right, int):
            if not _ref_check_int_bounds(left) or not _ref_check_int_bounds(right):
                return _RefErrorValue(OV_ERROR)
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
        return _RefErrorValue(TYPE_ERROR)

    if kind == 'ADD':
        _, op, left_node, right_node = node
        left = _ref_evaluate(left_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)
        if _ref_is_error(left):
            return left
        if _ref_is_string(left):
            return _RefErrorValue(TYPE_ERROR)
        right = _ref_evaluate(right_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)
        if _ref_is_error(right):
            return right
        if _ref_is_string(right):
            return _RefErrorValue(TYPE_ERROR)
        if op == '+':
            result = left + right
            if isinstance(result, int) and not isinstance(result, bool):
                if abs(result) > _MAX_INT_ABS:
                    return _RefErrorValue(OV_ERROR)
            return result
        if op == '-':
            result = left - right
            if isinstance(result, int) and not isinstance(result, bool):
                if abs(result) > _MAX_INT_ABS:
                    return _RefErrorValue(OV_ERROR)
            return result

    if kind == 'MUL':
        _, op, left_node, right_node = node
        left = _ref_evaluate(left_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)
        if _ref_is_error(left):
            return left
        if _ref_is_string(left):
            return _RefErrorValue(TYPE_ERROR)
        right = _ref_evaluate(right_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)
        if _ref_is_error(right):
            return right
        if _ref_is_string(right):
            return _RefErrorValue(TYPE_ERROR)
        if op == '*':
            result = left * right
            if isinstance(result, int) and not isinstance(result, bool):
                if abs(result) > _MAX_INT_ABS:
                    return _RefErrorValue(OV_ERROR)
            return result
        if op == '/':
            if right == 0:
                return _RefErrorValue(DIV_ERROR)
            if not _ref_check_int_bounds(left) or not _ref_check_int_bounds(right):
                return _RefErrorValue(OV_ERROR)
            quotient = int(left / right)
            if abs(quotient) > _MAX_INT_ABS:
                return _RefErrorValue(OV_ERROR)
            return quotient

    if kind == 'NEG':
        operand = _ref_evaluate(node[1], resolve_ref, eval_count, resolve_count_ref, resolve_name)
        if _ref_is_error(operand):
            return operand
        if _ref_is_string(operand):
            return _RefErrorValue(TYPE_ERROR)
        result = -operand
        if isinstance(result, int) and not isinstance(result, bool):
            if abs(result) > _MAX_INT_ABS:
                return _RefErrorValue(OV_ERROR)
        return result

    if kind == 'IF':
        return _ref_evaluate_if(node, resolve_ref, eval_count, resolve_count_ref, resolve_name)

    if kind == 'FUNC':
        return _ref_evaluate_func(node, resolve_ref, eval_count, resolve_count_ref, resolve_name)

    raise ValueError(f"Unknown AST node kind: {kind!r}")


def _ref_evaluate_func(node, resolve_ref, eval_count, resolve_count_ref=None, resolve_name=None):
    """Evaluate a FUNC node with a range argument or expression arguments."""
    _, func_name, arg = node
    sheet_qualifier = None

    # Check if this is an expression-based function (CONCAT, LEN)
    if isinstance(arg, list):
        # Expression-based function
        if func_name == 'CONCAT':
            return _ref_eval_concat(arg, resolve_ref, eval_count, resolve_name)
        elif func_name == 'LEN':
            return _ref_eval_len(arg, resolve_ref, eval_count, resolve_name)
        # Unknown expression-based function
        return _RefErrorValue(PARSE_ERROR)

    if isinstance(arg, tuple) and len(arg) == 2 and arg[0] == 'NAME':
        if resolve_name is None:
            return _RefErrorValue(NAME_ERROR)
        result = resolve_name(arg[1])
        if result is None or result == ("invalid", None):
            return _RefErrorValue(NAME_ERROR)
        name_kind, name_value = result
        if name_kind == "range":
            if '!' in name_value:
                sheet_qualifier, rest = name_value.split('!', 1)
                ref1, ref2 = rest.split(":")
            else:
                ref1, ref2 = name_value.split(":")
        elif name_kind == "cell":
            if '!' in name_value:
                sheet_qualifier, ref1 = name_value.split('!', 1)
                ref2 = ref1
            else:
                ref1 = ref2 = name_value
        else:
            return _RefErrorValue(NAME_ERROR)
    elif isinstance(arg, tuple) and len(arg) == 4 and arg[0] == 'QRANGE':
        _, sheet_qualifier, ref1, ref2 = arg
    else:
        _, ref1, ref2 = arg

    # Check for REF_ERROR in range endpoints
    if ref1 == REF_ERROR or ref2 == REF_ERROR:
        return _RefErrorValue(REF_ERROR)

    if not _is_valid_address(ref1) or not _is_valid_address(ref2):
        return _RefErrorValue(REF_ERROR)

    col1, row1 = _ref_parse_address(ref1)
    col2, row2 = _ref_parse_address(ref2)

    if col1 > col2 or row1 > row2:
        return _RefErrorValue(REF_ERROR)

    cells = _ref_generate_range_cells(ref1, ref2)

    if func_name == 'SUM':
        return _ref_eval_sum(cells, resolve_ref, eval_count, sheet_qualifier)
    elif func_name == 'MIN':
        return _ref_eval_min(cells, resolve_ref, eval_count, sheet_qualifier)
    elif func_name == 'MAX':
        return _ref_eval_max(cells, resolve_ref, eval_count, sheet_qualifier)
    elif func_name == 'COUNT':
        return _ref_eval_count(cells, resolve_ref, resolve_count_ref, sheet_qualifier)

    return _RefErrorValue(PARSE_ERROR)


def _ref_render_value(value):
    """Render a value as a string for CONCAT/LEN.

    - int: base-10 representation (no leading zeros, leading '-' for negatives)
    - str: preserved as-is
    - _RefErrorValue: returned as-is (caller handles short-circuit)
    """
    if isinstance(value, _RefErrorValue):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    # Fallback (should not reach here)
    return str(value)


def _ref_eval_concat(exprs, resolve_ref, eval_count, resolve_name=None):
    """Evaluate CONCAT over a list of expression nodes.

    Evaluates arguments left-to-right, short-circuits on first error.
    Renders ints as base-10 strings, preserves strings as-is.
    Empty-cell references render as "0" (handled by _ref_evaluate returning 0).
    """
    if not exprs:
        # CONCAT() with no arguments -> #PARSE!
        return _RefErrorValue(PARSE_ERROR)

    result_parts = []
    for expr_node in exprs:
        value = _ref_evaluate(expr_node, resolve_ref, eval_count, resolve_name=resolve_name)
        if isinstance(value, _RefErrorValue):
            return value
        rendered = _ref_render_value(value)
        if isinstance(rendered, _RefErrorValue):
            return rendered
        result_parts.append(rendered)

    return ''.join(result_parts)


def _ref_eval_len(exprs, resolve_ref, eval_count, resolve_name=None):
    """Evaluate LEN over a single expression node.

    Returns the character count of the string or decimal-rendered int.
    """
    if len(exprs) != 1:
        # LEN with wrong arity -> #PARSE!
        return _RefErrorValue(PARSE_ERROR)

    expr_node = exprs[0]
    value = _ref_evaluate(expr_node, resolve_ref, eval_count, resolve_name=resolve_name)
    if isinstance(value, _RefErrorValue):
        return value
    rendered = _ref_render_value(value)
    if isinstance(rendered, _RefErrorValue):
        return rendered
    return len(rendered)


# ---------------------------------------------------------------------------
# IF function evaluation (R15)
# ---------------------------------------------------------------------------

def _ref_evaluate_if(node, resolve_ref, eval_count, resolve_count_ref=None, resolve_name=None):
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
    cond_value = _ref_evaluate(cond_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)

    # Error condition: return the error.
    if isinstance(cond_value, _RefErrorValue):
        return cond_value

    # String condition: return #TYPE!.
    if isinstance(cond_value, str):
        return _RefErrorValue(TYPE_ERROR)

    # Integer condition: select branch.
    if isinstance(cond_value, int) and not isinstance(cond_value, bool):
        if cond_value != 0:
            # Nonzero: select then branch.
            return _ref_evaluate(then_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)
        else:
            # Zero: select else branch.
            return _ref_evaluate(else_node, resolve_ref, eval_count, resolve_count_ref, resolve_name)

    # Any other type (should not happen given the grammar, but be safe):
    return _RefErrorValue(TYPE_ERROR)


def _ref_eval_sum(cells, resolve_ref, eval_count, sheet_qualifier=None):
    """Evaluate SUM over a list of cell addresses."""
    total = 0
    has_values = False
    for addr in cells:
        if resolve_ref is None:
            kind, value = 'empty', None
        else:
            kind, value = resolve_ref(addr, sheet_qualifier) if sheet_qualifier else resolve_ref(addr)
        if kind == 'empty':
            continue
        if kind == 'str':
            return _RefErrorValue(TYPE_ERROR)
        if kind == 'int':
            total += value
            has_values = True
        if kind == 'error':
            return _RefErrorValue(value)
    return total


def _ref_eval_min(cells, resolve_ref, eval_count, sheet_qualifier=None):
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
            return _RefErrorValue(TYPE_ERROR)
        if kind == 'int':
            if min_val is None or value < min_val:
                min_val = value
        if kind == 'error':
            return _RefErrorValue(value)
    if min_val is None:
        return _RefErrorValue(TYPE_ERROR)
    return min_val


def _ref_eval_max(cells, resolve_ref, eval_count, sheet_qualifier=None):
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
            return _RefErrorValue(TYPE_ERROR)
        if kind == 'int':
            if max_val is None or value > max_val:
                max_val = value
        if kind == 'error':
            return _RefErrorValue(value)
    if max_val is None:
        return _RefErrorValue(TYPE_ERROR)
    return max_val


def _ref_eval_count(cells, resolve_ref, resolve_count_ref=None, sheet_qualifier=None):
    """Evaluate COUNT structurally over a list of cell addresses."""
    count = 0
    resolver = resolve_count_ref if resolve_count_ref is not None else resolve_ref
    for addr in cells:
        if resolver is None:
            kind, value = 'empty', None
        else:
            kind, value = resolver(addr, sheet_qualifier) if sheet_qualifier else resolver(addr)
        if kind == 'invalid':
            return _RefErrorValue(REF_ERROR)
        if kind != 'empty':
            count += 1
    return count


# ---------------------------------------------------------------------------
# NaiveSheet reference model
# ---------------------------------------------------------------------------

class NaiveSheet:
    """Independent naive reference sheet with its own formula parser/evaluator."""

    def __init__(self):
        self._cells = {}
        self._names = {}  # name -> target string (address or range)

    def set(self, addr, raw):
        """Store a literal value at *addr*."""
        if not _is_valid_unqualified_address(addr):
            raise ValueError(f"Invalid address: {addr!r}")
        if isinstance(raw, bool):
            raise ValueError("bool values are not accepted")
        if isinstance(raw, int):
            normalized = int(raw)
        elif isinstance(raw, str):
            normalized = str(raw)
        else:
            raise ValueError(f"Unsupported raw type: {type(raw).__name__}")
        self._cells[addr] = normalized
        return None

    def define_name(self, name, target):
        """Bind a per-sheet name to a target address or range."""
        if not _is_valid_name(name):
            raise ValueError(f"Invalid name: {name!r}")
        if not _is_valid_target(target):
            raise ValueError(f"Invalid target: {target!r}")
        self._names[name] = target
        return None

    def copy(self, src, dst):
        if not _is_valid_unqualified_address(src):
            raise ValueError(f"Invalid source address: {src!r}")
        if not _is_valid_unqualified_address(dst):
            raise ValueError(f"Invalid destination address: {dst!r}")
        if src not in self._cells:
            raise ValueError(f"Cannot copy empty source cell: {src!r}")

        value = self._cells[src]
        if isinstance(value, str) and value.startswith("="):
            src_col, src_row = _ref_parse_address(src)
            dst_col, dst_row = _ref_parse_address(dst)
            value = "=" + _ref_rewrite_formula_for_copy(
                value[1:], ord(dst_col) - ord(src_col), dst_row - src_row
            )
        self._cells[dst] = value
        return None

    def get(self, addr):
        """Retrieve the value at *addr* using independent formula evaluation."""
        if not _is_valid_unqualified_address(addr):
            raise ValueError(f"Invalid address: {addr!r}")
        return _public(self._eval_cell(addr, set()))

    def snapshot(self, addrs):
        """Return a tuple of (addr, value) pairs for the given addresses."""
        return tuple((addr, self.get(addr)) for addr in addrs)

    def _eval_cell(self, addr, in_progress):
        """Evaluate a cell using the independent parser/evaluator."""
        raw = self._cells.get(addr)
        if raw is None:
            return None
        if isinstance(raw, int):
            return raw
        if not raw.startswith("="):
            return raw
        if addr in in_progress:
            return "#CYCLE!"

        in_progress.add(addr)
        try:
            formula_text = raw[1:]

            # R12: Check formula text bounds.
            if not _ref_check_formula_bounds(formula_text):
                return _RefErrorValue(PARSE_ERROR)

            eval_count = [0]

            def _resolve_name(name):
                """Resolve a name to its binding."""
                if name not in self._names:
                    return ("invalid", None)
                target = self._names[name]
                if ":" in target:
                    ref1, ref2 = target.split(":")
                    if ref1 == ref2:
                        return ("cell", ref1)
                    return ("range", target)
                return ("cell", target)

            def _resolve_ref(ref_addr):
                """Resolve a reference address to a typed cell value."""
                ref_addr = _strip_abs_ref(ref_addr)
                if not _is_valid_address(ref_addr):
                    return ("invalid", None)

                if ref_addr in in_progress:
                    return ("error", "#CYCLE!")

                cell_value = self._cells.get(ref_addr)
                if cell_value is None:
                    return ("empty", None)
                if isinstance(cell_value, int):
                    return ("int", cell_value)
                if isinstance(cell_value, str):
                    if cell_value.startswith("="):
                        # Recursive formula evaluation.
                        sub_result = self._eval_cell(ref_addr, in_progress)
                        if sub_result is None:
                            return ("empty", None)
                        if isinstance(sub_result, _RefErrorValue):
                            return ("error", sub_result.code)
                        if isinstance(sub_result, int):
                            return ("int", sub_result)
                        return ("str", sub_result)
                    return ("str", cell_value)
                return ("empty", None)

            def _resolve_count_ref(ref_addr):
                """Resolve a reference for COUNT (structural, no recursion)."""
                if not _is_valid_address(ref_addr):
                    return ("invalid", None)
                cell_value = self._cells.get(ref_addr)
                if cell_value is None:
                    return ("empty", None)
                if isinstance(cell_value, int):
                    return ("int", cell_value)
                if isinstance(cell_value, str):
                    if cell_value.startswith("="):
                        return ("formula", None)
                    return ("str", cell_value)
                return ("empty", None)

            tokens = _ref_tokenize(formula_text)
            if tokens is None:
                return _RefErrorValue(PARSE_ERROR)

            pos = [0]
            ast_node = _ref_parse_expr(tokens, pos)
            if ast_node is None or pos[0] != len(tokens):
                return _RefErrorValue(PARSE_ERROR)

            result = _ref_evaluate(ast_node, _resolve_ref, eval_count, _resolve_count_ref, _resolve_name)
            return result
        finally:
            in_progress.discard(addr)


class NaiveWorkbook:
    """Workbook-level naive reference for multi-sheet differential tests."""

    def __init__(self):
        self._sheets = {}
        self._order = []
        self._clock = 0
        self._journal = []
        self._redo_stack = []

    @property
    def sheet_names(self):
        return list(self._order)

    @property
    def clock(self):
        return self._clock

    def _snapshot_state(self):
        return (
            tuple(self._order),
            self._clock,
            tuple(
                (name, tuple(sheet._cells.items()), tuple(sheet._names.items()))
                for name, sheet in self._sheets.items()
            ),
        )

    def _restore_state(self, state):
        order, clock, sheets = state
        self._order = list(order)
        self._clock = clock
        self._sheets = {}
        for name, cells, names in sheets:
            sheet = NaiveSheet()
            sheet._cells = dict(cells)
            sheet._names = dict(names)
            self._sheets[name] = sheet

    def _record(self, before):
        after = self._snapshot_state()
        self._journal.append((before, after))
        self._redo_stack.clear()

    def add_sheet(self, name):
        if not isinstance(name, str):
            raise ValueError("Sheet name must be str")
        name = str(name)
        if not _is_valid_sheet_name(name) or name in self._sheets:
            raise ValueError(f"Invalid or duplicate sheet: {name!r}")
        before = self._snapshot_state()
        self._sheets[name] = NaiveSheet()
        self._order.append(name)
        self._record(before)
        return self._sheets[name]

    def advance_clock(self):
        before = self._snapshot_state()
        self._clock += 1
        self._record(before)
        return self._clock

    def sheet(self, name):
        if not isinstance(name, str):
            raise ValueError("Sheet name must be str")
        name = str(name)
        if not _is_valid_sheet_name(name) or name not in self._sheets:
            raise ValueError(f"Unknown sheet: {name!r}")
        return self._sheets[name]

    def set(self, sheet_name, addr, raw):
        sheet = self.sheet(sheet_name)
        before = self._snapshot_state()
        sheet.set(addr, raw)
        self._record(before)

    def define_name(self, sheet_name, name, target):
        sheet = self.sheet(sheet_name)
        if not _is_valid_name(name):
            raise ValueError(f"Invalid name: {name!r}")
        if not _is_valid_target_for_sheets(target, self._sheets):
            raise ValueError(f"Invalid target: {target!r}")
        before = self._snapshot_state()
        sheet._names[str(name)] = str(target)
        self._record(before)

    def copy(self, default_sheet, src, dst):
        self.sheet(default_sheet)
        src_sheet, src_addr = _parse_qualified_cell_arg(src, default_sheet, self._sheets)
        dst_sheet, dst_addr = _parse_qualified_cell_arg(dst, default_sheet, self._sheets)
        if src_addr not in self._sheets[src_sheet]._cells:
            raise ValueError(f"Cannot copy empty source cell: {src!r}")
        before = self._snapshot_state()
        value = self._sheets[src_sheet]._cells[src_addr]
        if isinstance(value, str) and value.startswith("="):
            src_col, src_row = _ref_parse_address(src_addr)
            dst_col, dst_row = _ref_parse_address(dst_addr)
            value = "=" + _ref_rewrite_formula_for_copy(
                value[1:], ord(dst_col) - ord(src_col), dst_row - src_row
            )
        self._sheets[dst_sheet]._cells[dst_addr] = value
        self._record(before)

    def get(self, sheet_name, addr):
        self.sheet(sheet_name)
        if not _is_valid_unqualified_address(addr):
            raise ValueError(f"Invalid address: {addr!r}")
        return _public(self._eval_cell(sheet_name, addr, set(), [0]))

    def undo(self):
        if not self._journal:
            return False
        before, after = self._journal.pop()
        self._redo_stack.append((before, after))
        self._restore_state(before)
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        before, after = self._redo_stack.pop()
        self._journal.append((before, after))
        self._restore_state(after)
        return True

    def snapshot(self, identities):
        return (
            tuple(self._order),
            tuple((sheet, addr, self.get(sheet, addr)) for sheet, addr in identities if sheet in self._sheets),
        )

    def _eval_cell(self, sheet_name, addr, in_progress, reached_formula_cells):
        if sheet_name not in self._sheets or not _is_valid_address(addr):
            return _RefErrorValue(REF_ERROR)
        identity = (sheet_name, addr)
        sheet = self._sheets[sheet_name]
        raw = sheet._cells.get(addr)
        if raw is None:
            return None
        if isinstance(raw, int):
            return raw
        if not raw.startswith("="):
            return raw
        if identity in in_progress:
            return "#CYCLE!"
        formula_text = raw[1:]
        if not _ref_check_formula_bounds(formula_text):
            return _RefErrorValue(PARSE_ERROR)
        reached_formula_cells[0] += 1
        if reached_formula_cells[0] > 256:
            return _RefErrorValue(PARSE_ERROR)

        def _resolve_name(name):
            if name not in sheet._names:
                return ("invalid", None)
            target = sheet._names[name]
            target_sheet, ref1, ref2 = _split_name_target(target)
            if target_sheet is not None and target_sheet not in self._sheets:
                return ("invalid", None)
            prefix = f"{target_sheet}!" if target_sheet is not None else ""
            if ref2 is None or ref1 == ref2:
                return ("cell", prefix + ref1)
            return ("range", prefix + ref1 + ":" + ref2)

        def _resolve_ref(ref_addr, sheet_qualifier=None):
            target_sheet = sheet_qualifier if sheet_qualifier is not None else sheet_name
            if target_sheet not in self._sheets or not _is_valid_address(_strip_abs_ref(ref_addr)):
                return ("invalid", None)
            if (target_sheet, _strip_abs_ref(ref_addr)) in in_progress:
                return ("error", "#CYCLE!")
            value = self._eval_cell(target_sheet, _strip_abs_ref(ref_addr), in_progress, reached_formula_cells)
            if value is None:
                return ("empty", None)
            if isinstance(value, _RefErrorValue):
                return ("error", value.code)
            if isinstance(value, int):
                return ("int", value)
            if isinstance(value, str) and value.startswith("#") and value.endswith("!"):
                return ("error", value)
            return ("str", value)

        def _resolve_count_ref(ref_addr, sheet_qualifier=None):
            target_sheet = sheet_qualifier if sheet_qualifier is not None else sheet_name
            ref_addr = _strip_abs_ref(ref_addr)
            if target_sheet not in self._sheets or not _is_valid_address(ref_addr):
                return ("invalid", None)
            value = self._sheets[target_sheet]._cells.get(ref_addr)
            if value is None:
                return ("empty", None)
            if isinstance(value, int):
                return ("int", value)
            if isinstance(value, str):
                return ("formula", None) if value.startswith("=") else ("str", value)
            return ("empty", None)

        tokens = _ref_tokenize(formula_text)
        if tokens is None:
            return _RefErrorValue(PARSE_ERROR)
        pos = [0]
        ast_node = _ref_parse_expr(tokens, pos)
        if ast_node is None or pos[0] != len(tokens):
            return _RefErrorValue(PARSE_ERROR)

        in_progress.add(identity)
        try:
            return _ref_evaluate(ast_node, _resolve_ref, [0], _resolve_count_ref, _resolve_name)
        finally:
            in_progress.discard(identity)
