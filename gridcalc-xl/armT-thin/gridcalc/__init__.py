import json
import sys

__all__ = ["Workbook"]

# R12: within-bounds evaluations must complete without raising — a 256-cell
# reference chain and a ~500-deep unary-minus tower (512 source chars) are
# explicitly within bounds. The recursive parser/evaluator would exceed
# CPython's default 1000-frame limit on those, so raise it once at import
# (the Engineer Lens sanctions this as the sole exception to R24's
# global-state hygiene, provided the chain and tower cases pass). Kept well
# below the C-stack ceiling so genuinely out-of-bounds depths raise
# RecursionError (an acceptable out-of-bounds outcome) rather than crash.
if sys.getrecursionlimit() < 8000:
    sys.setrecursionlimit(8000)

_ERRORS = {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"}
_FUNCTION_NAMES = {"SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW"}

_PARSE_FAIL = object()


def _plain_str(value):
    if not isinstance(value, str):
        raise ValueError
    return str(value)


def _validate_addr(addr):
    addr = _plain_str(addr)
    if len(addr) < 2 or len(addr) > 3:
        raise ValueError
    col = addr[0]
    row_text = addr[1:]
    if not ("A" <= col <= "Z"):
        raise ValueError
    if not row_text or not row_text.isascii() or not row_text.isdigit():
        raise ValueError
    if row_text.startswith("0"):
        raise ValueError
    row = int(row_text)
    if row < 1 or row > 99:
        raise ValueError
    return addr


def _normalize_raw(raw):
    if isinstance(raw, bool):
        raise ValueError
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, str):
        return str(raw)
    raise ValueError


def _validate_sheet_name(name):
    name = _plain_str(name)
    if not _sheet_name_shape(name):
        raise ValueError
    return name


def _sheet_name_shape(name):
    if len(name) < 1 or len(name) > 32:
        return False
    first = name[0]
    if not ("A" <= first <= "Z" or "a" <= first <= "z"):
        return False
    for ch in name:
        if not ("A" <= ch <= "Z" or "a" <= ch <= "z" or "0" <= ch <= "9" or ch == "_"):
            return False
    return True


def _ref_to_addr(token):
    token = token.replace("$", "")
    if len(token) < 2:
        return None
    col = token[0]
    row_text = token[1:]
    if not ("A" <= col <= "Z") or not row_text.isascii() or not row_text.isdigit():
        return None
    if row_text.startswith("0"):
        return None
    row = int(row_text)
    if row < 1 or row > 99:
        return None
    return token


def _addr_parts(addr):
    return ord(addr[0]) - ord("A"), int(addr[1:])


def _addr_from_parts(col, row):
    return chr(ord("A") + col) + str(row)


def _is_name_token(token):
    if len(token) < 2 or len(token) > 32 or token in _FUNCTION_NAMES:
        return False
    first = token[0]
    if not ("A" <= first <= "Z" or first == "_"):
        return False
    for ch in token:
        if not ("A" <= ch <= "Z" or "0" <= ch <= "9" or ch == "_"):
            return False
    if len(token) >= 2 and "A" <= token[0] <= "Z" and token[1:].isdigit():
        return False
    return True


def _valid_range_addrs(range_arg):
    """Return the row-major member addresses of a `("range", ...)` arg, or
    None if the range is invalid (bad endpoints or mis-ordered)."""
    if range_arg[0] != "range":
        return None
    start = _ref_to_addr(range_arg[1][-1])
    end = _ref_to_addr(range_arg[2][-1])
    if start is None or end is None:
        return None
    start_col, start_row = _addr_parts(start)
    end_col, end_row = _addr_parts(end)
    if start_col > end_col or start_row > end_row:
        return None
    return [
        _addr_from_parts(col, row)
        for row in range(start_row, end_row + 1)
        for col in range(start_col, end_col + 1)
    ]


def _ref_node_parts(node, host_sheet):
    if len(node) == 2:
        return host_sheet, node[1]
    return node[1], node[2]


def _parse_ref_token(text, pos):
    start = pos
    abs_col = False
    abs_row = False
    if pos < len(text) and text[pos] == "$":
        abs_col = True
        pos += 1
    if pos >= len(text) or not ("A" <= text[pos] <= "Z"):
        return None
    col = text[pos]
    pos += 1
    if pos < len(text) and text[pos] == "$":
        abs_row = True
        pos += 1
    digit_start = pos
    while pos < len(text) and text[pos].isascii() and text[pos].isdigit():
        pos += 1
    if pos == digit_start:
        return None
    return {
        "start": start,
        "end": pos,
        "text": text[start:pos],
        "col": col,
        "row_text": text[digit_start:pos],
        "abs_col": abs_col,
        "abs_row": abs_row,
    }


def _ref_info_addr(info):
    return _ref_to_addr(info["col"] + info["row_text"])


def _shift_ref_text(info, dcol, drow):
    addr = _ref_info_addr(info)
    if addr is None:
        return info["text"]
    col, row = _addr_parts(addr)
    if not info["abs_col"]:
        col += dcol
    if not info["abs_row"]:
        row += drow
    if col < 0 or col > 25 or row < 1 or row > 99:
        return "#REF!"
    prefix_col = "$" if info["abs_col"] else ""
    prefix_row = "$" if info["abs_row"] else ""
    return prefix_col + chr(ord("A") + col) + prefix_row + str(row)


def _lex_ref_run(text, pos):
    if pos >= len(text) or not ("A" <= text[pos] <= "Z" or text[pos] == "$" or text[pos] == "_"):
        return None, None
    end = pos
    while end < len(text) and ("A" <= text[end] <= "Z" or "0" <= text[end] <= "9" or text[end] in "$_"):
        end += 1
    run = text[pos:end]
    info = _parse_ref_token(text, pos)
    if info is None or info["end"] != end:
        return {"start": pos, "end": end, "text": run}, None
    return {"start": pos, "end": end, "text": run}, info


def _rewrite_formula_for_copy(raw, src, dst):
    dcol = _addr_parts(dst)[0] - _addr_parts(src)[0]
    drow = _addr_parts(dst)[1] - _addr_parts(src)[1]
    text = raw[1:]
    out = []
    pos = 0
    while pos < len(text):
        ch = text[pos]
        if ch == '"':
            end = pos + 1
            while end < len(text) and text[end] != '"':
                end += 1
            if end < len(text):
                end += 1
            out.append(text[pos:end])
            pos = end
            continue
        run, info = _lex_ref_run(text, pos)
        if run is None:
            out.append(ch)
            pos += 1
            continue
        qual_scan = run["end"]
        while qual_scan < len(text) and text[qual_scan] in " \t":
            qual_scan += 1
        if qual_scan < len(text) and text[qual_scan] == "!" and _sheet_name_shape(run["text"]):
            ref_start = qual_scan + 1
            while ref_start < len(text) and text[ref_start] in " \t":
                ref_start += 1
            ref_run, ref_info = _lex_ref_run(text, ref_start)
            if ref_info is None:
                out.append(run["text"])
                pos = run["end"]
                continue
            scan = ref_info["end"]
            while scan < len(text) and text[scan] in " \t":
                scan += 1
            if scan < len(text) and text[scan] == ":":
                after_colon = scan + 1
                while after_colon < len(text) and text[after_colon] in " \t":
                    after_colon += 1
                end_run, end_info = _lex_ref_run(text, after_colon)
                if end_info is not None:
                    shifted_start = _shift_ref_text(ref_info, dcol, drow)
                    shifted_end = _shift_ref_text(end_info, dcol, drow)
                    out.append("#REF!" if shifted_start == "#REF!" or shifted_end == "#REF!" else text[pos:ref_start] + shifted_start + text[ref_info["end"]:after_colon] + shifted_end)
                    pos = end_info["end"]
                    continue
            shifted = _shift_ref_text(ref_info, dcol, drow)
            out.append("#REF!" if shifted == "#REF!" else text[pos:ref_start] + shifted)
            pos = ref_info["end"]
            continue
        if info is None:
            out.append(run["text"])
            pos = run["end"]
            continue
        scan = info["end"]
        while scan < len(text) and text[scan] in " \t":
            scan += 1
        if scan < len(text) and text[scan] == ":":
            after_colon = scan + 1
            while after_colon < len(text) and text[after_colon] in " \t":
                after_colon += 1
            end_run, end_info = _lex_ref_run(text, after_colon)
            if end_info is not None:
                shifted_start = _shift_ref_text(info, dcol, drow)
                shifted_end = _shift_ref_text(end_info, dcol, drow)
                if shifted_start == "#REF!" or shifted_end == "#REF!":
                    out.append("#REF!")
                else:
                    out.append(shifted_start + text[info["end"]:after_colon] + shifted_end)
                pos = end_info["end"]
                continue
        out.append(_shift_ref_text(info, dcol, drow))
        pos = info["end"]
    return "=" + "".join(out)


def _within_formula_source_bounds(raw):
    text = raw[1:] if raw.startswith("=") else raw
    if len(text) > 512:
        return False
    depth = 0
    max_depth = 0
    in_string = False
    for ch in text:
        if ch == '"':
            in_string = not in_string
        elif not in_string and ch == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif not in_string and ch == ")":
            depth = max(0, depth - 1)
    return max_depth <= 32


def _parse_qualified_addr_arg(value, default_sheet, workbook):
    value = _plain_str(value)
    if "!" in value:
        parts = value.split("!")
        if len(parts) != 2:
            raise ValueError
        sheetname = _validate_sheet_name(parts[0])
        if sheetname not in workbook._sheets:
            raise ValueError
        return sheetname, _validate_addr(parts[1])
    return default_sheet, _validate_addr(value)


def _parse_qualified_target_arg(value, default_sheet, workbook):
    value = _plain_str(value)
    sheetname = default_sheet
    body = value
    if "!" in value:
        parts = value.split("!")
        if len(parts) != 2:
            raise ValueError
        sheetname = _validate_sheet_name(parts[0])
        if sheetname not in workbook._sheets:
            raise ValueError
        body = parts[1]
    if ":" in body:
        parts = body.split(":")
        if len(parts) != 2:
            raise ValueError
        start = _validate_addr(parts[0])
        end = _validate_addr(parts[1])
        if _valid_range_addrs(("range", ("ref", start), ("ref", end))) is None:
            raise ValueError
        return ("range", sheetname, start, end)
    return ("addr", sheetname, _validate_addr(body))


class _ParseError(Exception):
    pass


class _Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def parse(self):
        if self.text == "":
            raise _ParseError
        expr = self._expr()
        self._skip_ws()
        if self.pos != len(self.text):
            raise _ParseError
        return expr

    def _skip_ws(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t":
            self.pos += 1

    def _match(self, token):
        self._skip_ws()
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def _expr(self):
        left = self._additive()
        while True:
            self._skip_ws()
            op = None
            for candidate in ("<=", ">=", "<>", "=", "<", ">"):
                if self.text.startswith(candidate, self.pos):
                    op = candidate
                    self.pos += len(candidate)
                    break
            if op is None:
                return left
            right = self._additive()
            left = ("cmp", op, left, right)

    def _additive(self):
        left = self._term()
        while True:
            self._skip_ws()
            if self._match("+"):
                left = ("bin", "+", left, self._term())
            elif self._match("-"):
                left = ("bin", "-", left, self._term())
            else:
                return left

    def _term(self):
        left = self._factor()
        while True:
            self._skip_ws()
            if self._match("*"):
                left = ("bin", "*", left, self._factor())
            elif self._match("/"):
                left = ("bin", "/", left, self._factor())
            else:
                return left

    def _factor(self):
        self._skip_ws()
        if self._match("-"):
            return ("neg", self._factor())
        return self._primary()

    def _primary(self):
        self._skip_ws()
        if self.pos >= len(self.text):
            raise _ParseError
        if self.text.startswith("#REF!", self.pos):
            self.pos += 5
            return ("error", "#REF!")
        ch = self.text[self.pos]
        if ch == '"':
            self.pos += 1
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos] != '"':
                self.pos += 1
            if self.pos >= len(self.text):
                raise _ParseError
            value = self.text[start:self.pos]
            self.pos += 1
            return ("str", value)
        if ch.isascii() and ch.isdigit():
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isascii() and self.text[self.pos].isdigit():
                self.pos += 1
            return ("int", int(self.text[start:self.pos]))
        if ch == "(":
            self.pos += 1
            expr = self._expr()
            if not self._match(")"):
                raise _ParseError
            return expr
        if "A" <= ch <= "Z":
            saved = self.pos
            token = self._sheet_qualifier_token()
            if token is not None:
                info = _parse_ref_token(self.text, self.pos)
                if info is None:
                    raise _ParseError
                self.pos = info["end"]
                return ("ref", token, info["text"])
            self.pos = saved
        if "a" <= ch <= "z":
            start = self.pos
            self.pos += 1
            while self.pos < len(self.text):
                next_ch = self.text[self.pos]
                if not ("A" <= next_ch <= "Z" or "a" <= next_ch <= "z" or "0" <= next_ch <= "9" or next_ch == "_"):
                    break
                self.pos += 1
            token = self.text[start:self.pos]
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == "!" and _sheet_name_shape(token):
                self.pos += 1
                self._skip_ws()
                info = _parse_ref_token(self.text, self.pos)
                if info is None:
                    raise _ParseError
                self.pos = info["end"]
                return ("ref", token, info["text"])
            raise _ParseError
        if ch == "$" or "A" <= ch <= "Z":
            info = _parse_ref_token(self.text, self.pos)
            if info is not None:
                scan = info["end"]
                while scan < len(self.text) and self.text[scan] in " \t":
                    scan += 1
                if scan < len(self.text) and self.text[scan] == "!" and _sheet_name_shape(info["text"]):
                    self.pos = scan + 1
                    self._skip_ws()
                    ref_info = _parse_ref_token(self.text, self.pos)
                    if ref_info is None:
                        raise _ParseError
                    self.pos = ref_info["end"]
                    return ("ref", info["text"], ref_info["text"])
                self.pos = info["end"]
                return ("ref", info["text"])
        if "A" <= ch <= "Z" or ch == "_":
            start = self.pos
            self.pos += 1
            while self.pos < len(self.text):
                next_ch = self.text[self.pos]
                if not ("A" <= next_ch <= "Z" or "0" <= next_ch <= "9" or next_ch == "_"):
                    break
                self.pos += 1
            token = self.text[start:self.pos]
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == "!":
                if not _sheet_name_shape(token):
                    raise _ParseError
                self.pos += 1
                self._skip_ws()
                info = _parse_ref_token(self.text, self.pos)
                if info is None:
                    raise _ParseError
                self.pos = info["end"]
                return ("ref", token, info["text"])
            if self.pos < len(self.text) and self.text[self.pos] == "(":
                return self._function_call(token)
            if len(token) >= 2 and "A" <= token[0] <= "Z" and token[1:].isdigit():
                return ("ref", token)
            if _is_name_token(token):
                return ("name", token)
            raise _ParseError
        raise _ParseError

    def _function_call(self, name):
        if name not in _FUNCTION_NAMES:
            raise _ParseError
        self.pos += 1
        if name in {"SUM", "MIN", "MAX", "COUNT"}:
            arg = self._range_arg()
            if not self._match(")"):
                raise _ParseError
            return ("func", name, arg)
        if name == "CONCAT":
            args = [self._expr()]
            while self._match(","):
                args.append(self._expr())
            if not self._match(")"):
                raise _ParseError
            return ("concat", args)
        if name == "LEN":
            arg = self._expr()
            if self._match(",") or not self._match(")"):
                raise _ParseError
            return ("len", arg)
        if name == "IF":
            cond = self._expr()
            if not self._match(","):
                raise _ParseError
            then_node = self._expr()
            if not self._match(","):
                raise _ParseError
            else_node = self._expr()
            if self._match(",") or not self._match(")"):
                raise _ParseError
            return ("if", cond, then_node, else_node)
        if name == "NOW":
            if not self._match(")"):
                raise _ParseError
            return ("now",)
        raise _ParseError

    def _range_arg(self):
        self._skip_ws()
        if self.text.startswith("#REF!", self.pos):
            self.pos += 5
            return ("range_error", "#REF!")
        first = self._range_token()
        self._skip_ws()
        if self._match(":"):
            second = self._range_token()
            if len(first) == 3 and len(second) == 3:
                raise _ParseError
            if len(first) == 2 and len(second) == 3:
                raise _ParseError
            return ("range", first, second)
        if first[0] == "name":
            return ("range_name", first[1])
        raise _ParseError

    def _range_token(self):
        self._skip_ws()
        if self.pos >= len(self.text):
            raise _ParseError
        ch = self.text[self.pos]
        if "A" <= ch <= "Z":
            saved = self.pos
            token = self._sheet_qualifier_token()
            if token is not None:
                info = _parse_ref_token(self.text, self.pos)
                if info is None:
                    raise _ParseError
                self.pos = info["end"]
                return ("ref", token, info["text"])
            self.pos = saved
        if "a" <= ch <= "z":
            start = self.pos
            self.pos += 1
            while self.pos < len(self.text):
                next_ch = self.text[self.pos]
                if not ("A" <= next_ch <= "Z" or "a" <= next_ch <= "z" or "0" <= next_ch <= "9" or next_ch == "_"):
                    break
                self.pos += 1
            token = self.text[start:self.pos]
            self._skip_ws()
            if self.pos < len(self.text) and self.text[self.pos] == "!" and _sheet_name_shape(token):
                self.pos += 1
                self._skip_ws()
                info = _parse_ref_token(self.text, self.pos)
                if info is None:
                    raise _ParseError
                self.pos = info["end"]
                return ("ref", token, info["text"])
            raise _ParseError
        if ch == "$" or "A" <= ch <= "Z":
            info = _parse_ref_token(self.text, self.pos)
            if info is not None:
                scan = info["end"]
                while scan < len(self.text) and self.text[scan] in " \t":
                    scan += 1
                if scan < len(self.text) and self.text[scan] == "!" and _sheet_name_shape(info["text"]):
                    self.pos = scan + 1
                    self._skip_ws()
                    ref_info = _parse_ref_token(self.text, self.pos)
                    if ref_info is None:
                        raise _ParseError
                    self.pos = ref_info["end"]
                    return ("ref", info["text"], ref_info["text"])
                self.pos = info["end"]
                return ("ref", info["text"])
        if not ("A" <= ch <= "Z" or ch == "_"):
            raise _ParseError
        start = self.pos
        self.pos += 1
        while self.pos < len(self.text):
            next_ch = self.text[self.pos]
            if not ("A" <= next_ch <= "Z" or "0" <= next_ch <= "9" or next_ch == "_"):
                break
            self.pos += 1
        token = self.text[start:self.pos]
        self._skip_ws()
        if self.pos < len(self.text) and self.text[self.pos] == "!":
            if not _sheet_name_shape(token):
                raise _ParseError
            self.pos += 1
            self._skip_ws()
            info = _parse_ref_token(self.text, self.pos)
            if info is None:
                raise _ParseError
            self.pos = info["end"]
            return ("ref", token, info["text"])
        if len(token) >= 2 and "A" <= token[0] <= "Z" and token[1:].isdigit():
            return ("ref", token)
        if _is_name_token(token):
            return ("name", token)
        raise _ParseError

    def _sheet_qualifier_token(self):
        start = self.pos
        if self.pos >= len(self.text) or not ("A" <= self.text[self.pos] <= "Z" or "a" <= self.text[self.pos] <= "z"):
            return None
        self.pos += 1
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if not ("A" <= ch <= "Z" or "a" <= ch <= "z" or "0" <= ch <= "9" or ch == "_"):
                break
            self.pos += 1
        token = self.text[start:self.pos]
        self._skip_ws()
        if self.pos < len(self.text) and self.text[self.pos] == "!" and _sheet_name_shape(token):
            self.pos += 1
            self._skip_ws()
            return token
        return None


class _Evaluator:
    def __init__(self, workbook, sheetname, visiting):
        self.wb = workbook
        self.sheetname = sheetname
        self.visiting = visiting

    def evaluate(self, node):
        kind = node[0]
        if kind == "int":
            return node[1]
        if kind == "str":
            return node[1]
        if kind == "error":
            return node[1]
        if kind == "ref":
            return self._ref(node)
        if kind == "name":
            return self._name_value(node[1])
        if kind == "func":
            return self._func(node[1], node[2])
        if kind == "concat":
            return self._concat(node[1])
        if kind == "len":
            return self._len(node[1])
        if kind == "if":
            return self._if(node[1], node[2], node[3])
        if kind == "now":
            return self.wb._clock
        if kind == "neg":
            value = self.evaluate(node[1])
            if value in _ERRORS:
                return value
            if not isinstance(value, int):
                return "#TYPE!"
            return -value
        if kind == "bin":
            return self._binary(node[1], node[2], node[3])
        if kind == "cmp":
            return self._compare(node[1], node[2], node[3])
        return "#PARSE!"

    def _ref(self, node):
        sheetname, token = _ref_node_parts(node, self.sheetname)
        if sheetname not in self.wb._sheets:
            return "#REF!"
        addr = _ref_to_addr(token)
        if addr is None:
            return "#REF!"
        value = self.wb._compute((sheetname, addr), self.visiting)
        if value is None:
            return 0
        return value

    def _binary(self, op, left_node, right_node):
        left = self.evaluate(left_node)
        if left in _ERRORS:
            return left
        if not isinstance(left, int):
            return "#TYPE!"
        right = self.evaluate(right_node)
        if right in _ERRORS:
            return right
        if not isinstance(right, int):
            return "#TYPE!"
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if right == 0:
            return "#DIV!"
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            quotient = -quotient
        return quotient

    def _compare(self, op, left_node, right_node):
        left = self.evaluate(left_node)
        if left in _ERRORS:
            return left
        if not isinstance(left, (int, str)):
            return "#TYPE!"
        right = self.evaluate(right_node)
        if right in _ERRORS:
            return right
        if not isinstance(right, (int, str)):
            return "#TYPE!"
        if op in {"=", "<>"}:
            if type(left) is not type(right):
                return "#TYPE!"
            return int(left == right) if op == "=" else int(left != right)
        if not isinstance(left, int) or not isinstance(right, int):
            return "#TYPE!"
        if op == "<":
            return int(left < right)
        if op == "<=":
            return int(left <= right)
        if op == ">":
            return int(left > right)
        if op == ">=":
            return int(left >= right)
        return "#PARSE!"

    def _render(self, value):
        if value in _ERRORS:
            return value
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            return value
        return "#TYPE!"

    def _concat(self, args):
        parts = []
        for arg in args:
            rendered = self._render(self.evaluate(arg))
            if rendered in _ERRORS:
                return rendered
            parts.append(rendered)
        return "".join(parts)

    def _len(self, node):
        rendered = self._render(self.evaluate(node))
        if rendered in _ERRORS:
            return rendered
        return len(rendered)

    def _if(self, cond_node, then_node, else_node):
        cond = self.evaluate(cond_node)
        if cond in _ERRORS:
            return cond
        if not isinstance(cond, int):
            return "#TYPE!"
        return self.evaluate(then_node if cond != 0 else else_node)

    def _func(self, name, range_arg):
        cells_or_error = self._range_cells(range_arg)
        if isinstance(cells_or_error, str):
            return cells_or_error
        target_sheet, cells = cells_or_error
        data = self.wb._sheets[target_sheet]
        if name == "COUNT":
            # R8: purely structural — count non-empty members without
            # evaluating anything (no counter, no cycle participation).
            count = 0
            for addr in cells:
                if addr in data:
                    count += 1
            return count

        values = []
        for addr in cells:
            if addr not in data:
                continue
            value = self.wb._compute((target_sheet, addr), self.visiting)
            if value in _ERRORS:
                return value
            if not isinstance(value, int):
                return "#TYPE!"
            values.append(value)
        if name == "SUM":
            return sum(values)
        if not values:
            return "#TYPE!"
        if name == "MIN":
            return min(values)
        if name == "MAX":
            return max(values)
        return "#PARSE!"

    def _range_cells(self, range_arg):
        kind = range_arg[0]
        if kind == "range_error":
            return range_arg[1]
        if kind == "range_name":
            return self._name_cells(range_arg[1])
        if kind != "range":
            return "#PARSE!"
        sheetname = self.sheetname
        if len(range_arg[1]) == 3:
            sheetname = range_arg[1][1]
        if sheetname not in self.wb._sheets:
            return "#REF!"
        addrs = _valid_range_addrs(range_arg)
        if addrs is None:
            return "#REF!"
        return (sheetname, addrs)

    def _name_binding(self, name):
        return self.wb._names.get(self.sheetname, {}).get(name)

    def _name_value(self, name):
        binding = self._name_binding(name)
        if binding is None:
            return "#NAME!"
        kind = binding[0]
        if kind == "addr":
            value = self.wb._compute((binding[1], binding[2]), self.visiting)
            return 0 if value is None else value
        cells = _valid_range_addrs(("range", ("ref", binding[2]), ("ref", binding[3])))
        if cells is not None and len(cells) == 1:
            value = self.wb._compute((binding[1], cells[0]), self.visiting)
            return 0 if value is None else value
        return "#REF!"

    def _name_cells(self, name):
        binding = self._name_binding(name)
        if binding is None:
            return "#NAME!"
        if binding[0] == "addr":
            return (binding[1], [binding[2]])
        cells = _valid_range_addrs(("range", ("ref", binding[2]), ("ref", binding[3])))
        return "#REF!" if cells is None else (binding[1], cells)


class _Sheet:
    def __init__(self, workbook, name):
        self._workbook = workbook
        self._name = name

    def _data(self):
        try:
            return self._workbook._sheets[self._name]
        except KeyError:
            raise ValueError

    @property
    def eval_count(self):
        self._data()
        return self._workbook._eval_counts.get(self._name, 0)

    def set(self, addr, raw):
        data = self._data()
        addr = _validate_addr(addr)
        raw = _normalize_raw(raw)
        prev_exists = addr in data
        prev = data.get(addr)
        data[addr] = raw
        self._workbook._invalidate((self._name, addr))
        self._workbook._record(("cell", self._name, addr, prev_exists, prev, True, raw))
        return None

    def get(self, addr):
        data = self._data()
        addr = _validate_addr(addr)
        raw = data.get(addr)
        if isinstance(raw, str) and raw.startswith("="):
            return self._workbook._compute((self._name, addr), set())
        return raw

    def copy(self, src, dst):
        self._data()
        src_sheet, src = _parse_qualified_addr_arg(src, self._name, self._workbook)
        dst_sheet, dst = _parse_qualified_addr_arg(dst, self._name, self._workbook)
        data = self._workbook._sheets[src_sheet]
        if src not in data:
            raise ValueError
        raw = data[src]
        if isinstance(raw, str) and raw.startswith("=") and _within_formula_source_bounds(raw) and self._workbook._parse(raw[1:]) is not _PARSE_FAIL:
            raw = _rewrite_formula_for_copy(raw, src, dst)
        dst_data = self._workbook._sheets[dst_sheet]
        prev_exists = dst in dst_data
        prev = dst_data.get(dst)
        dst_data[dst] = raw
        self._workbook._invalidate((dst_sheet, dst))
        self._workbook._record(("cell", dst_sheet, dst, prev_exists, prev, True, raw))
        return None

    def define_name(self, name, target):
        self._data()
        name = _plain_str(name)
        if not _is_name_token(name):
            raise ValueError
        binding = _parse_qualified_target_arg(target, self._name, self._workbook)
        names = self._workbook._names.setdefault(self._name, {})
        prev_exists = name in names
        prev = names.get(name)
        names[name] = binding
        self._workbook._invalidate_name(self._name, name)
        self._workbook._record(("name", self._name, name, prev_exists, prev, True, binding))
        return None


class Workbook:
    def __init__(self):
        self._sheets = {}
        self._sheet_order = []
        self._eval_counts = {}
        # R10 incremental engine: persistent result cache and dependency
        # graph. `_cache` holds computed formula-cell results (values and
        # errors alike). `_fwd[key]` is the static reference closure members
        # (direct) of a cached cell; `_rev[addr]` the cells that reference
        # addr. Edits invalidate transitively through `_rev`.
        self._cache = {}
        self._fwd = {}
        self._rev = {}
        self._parse_cache = {}
        self._names = {}
        self._journal = []
        self._redo = []
        self._replaying = False
        self._clock = 0

    def _record(self, entry):
        if self._replaying:
            return
        self._journal.append(entry)
        self._redo.clear()

    def _parse(self, text):
        cache = self._parse_cache
        if text in cache:
            return cache[text]
        try:
            ast = _Parser(text).parse()
        except _ParseError:
            ast = _PARSE_FAIL
        cache[text] = ast
        return ast

    def _static_refs(self, ast, sheetname):
        """Direct reference-closure members of one formula (R10): every
        single REF denoting a grid cell and every member of a valid range
        argument. Static — independent of evaluation short-circuiting."""
        refs = set()
        stack = [ast]
        while stack:
            node = stack.pop()
            if not isinstance(node, tuple):
                continue
            kind = node[0]
            if kind == "ref":
                target_sheet, token = _ref_node_parts(node, sheetname)
                addr = _ref_to_addr(token)
                if addr is not None:
                    refs.add((target_sheet, addr))
            elif kind == "name":
                for ref in self._name_ref_addrs(sheetname, node[1]):
                    refs.add(ref)
            elif kind == "func":
                for ref in self._range_ref_addrs(sheetname, node[2]):
                    refs.add(ref)
            elif kind in ("bin", "cmp"):
                stack.append(node[2])
                stack.append(node[3])
            elif kind == "neg":
                stack.append(node[1])
            elif kind == "concat":
                stack.extend(node[1])
            elif kind == "len":
                stack.append(node[1])
            elif kind == "if":
                stack.append(node[1])
                stack.append(node[2])
                stack.append(node[3])
            elif kind == "now":
                pass
        return refs

    def _ast_has_now(self, ast):
        stack = [ast]
        while stack:
            node = stack.pop()
            if not isinstance(node, tuple):
                continue
            kind = node[0]
            if kind == "now":
                return True
            if kind in ("bin", "cmp"):
                stack.append(node[2])
                stack.append(node[3])
            elif kind == "neg":
                stack.append(node[1])
            elif kind == "concat":
                stack.extend(node[1])
            elif kind == "len":
                stack.append(node[1])
            elif kind == "if":
                stack.append(node[1])
                stack.append(node[2])
                stack.append(node[3])
        return False

    def _invalidate_volatile(self):
        for sheetname, data in list(self._sheets.items()):
            for addr, raw in list(data.items()):
                if isinstance(raw, str) and raw.startswith("="):
                    ast = self._parse(raw[1:])
                    if ast is not _PARSE_FAIL and self._ast_has_now(ast):
                        self._invalidate((sheetname, addr))

    def _name_ref_addrs(self, sheetname, name):
        binding = self._names.get(sheetname, {}).get(name)
        if binding is None:
            return []
        if binding[0] == "addr":
            return [(binding[1], binding[2])]
        addrs = _valid_range_addrs(("range", ("ref", binding[2]), ("ref", binding[3])))
        return [] if addrs is None else [(binding[1], addr) for addr in addrs]

    def _range_ref_addrs(self, sheetname, range_arg):
        if range_arg[0] == "range_name":
            return self._name_ref_addrs(sheetname, range_arg[1])
        target_sheet = sheetname
        if range_arg[0] == "range" and len(range_arg[1]) == 3:
            target_sheet = range_arg[1][1]
        addrs = _valid_range_addrs(range_arg)
        return [] if addrs is None else [(target_sheet, addr) for addr in addrs]

    def _ast_mentions_name(self, ast, name):
        stack = [ast]
        while stack:
            node = stack.pop()
            if not isinstance(node, tuple):
                continue
            kind = node[0]
            if kind == "name" and node[1] == name:
                return True
            if kind == "func" and node[2][0] == "range_name" and node[2][1] == name:
                return True
            if kind in ("bin", "cmp"):
                stack.append(node[2])
                stack.append(node[3])
            elif kind == "neg":
                stack.append(node[1])
            elif kind == "concat":
                stack.extend(node[1])
            elif kind == "len":
                stack.append(node[1])
            elif kind == "if":
                stack.append(node[1])
                stack.append(node[2])
                stack.append(node[3])
        return False

    def _ast_mentions_qualifier(self, ast, sheetname):
        stack = [ast]
        while stack:
            node = stack.pop()
            if not isinstance(node, tuple):
                continue
            kind = node[0]
            if kind == "ref" and len(node) == 3 and node[1] == sheetname:
                return True
            if kind == "func" and node[2][0] == "range" and len(node[2][1]) == 3 and node[2][1][1] == sheetname:
                return True
            if kind in ("bin", "cmp"):
                stack.append(node[2])
                stack.append(node[3])
            elif kind == "neg":
                stack.append(node[1])
            elif kind == "concat":
                stack.extend(node[1])
            elif kind == "len":
                stack.append(node[1])
            elif kind == "if":
                stack.append(node[1])
                stack.append(node[2])
                stack.append(node[3])
        return False

    def _invalidate_qualifier(self, sheetname):
        for owner, data in list(self._sheets.items()):
            for addr, raw in list(data.items()):
                if isinstance(raw, str) and raw.startswith("="):
                    ast = self._parse(raw[1:])
                    if ast is not _PARSE_FAIL and self._ast_mentions_qualifier(ast, sheetname):
                        self._invalidate((owner, addr))

    def _invalidate_name(self, sheetname, name):
        data = self._sheets[sheetname]
        for addr, raw in list(data.items()):
            if isinstance(raw, str) and raw.startswith("="):
                ast = self._parse(raw[1:])
                if ast is not _PARSE_FAIL and self._ast_mentions_name(ast, name):
                    self._invalidate((sheetname, addr))

    def _compute(self, key, visiting):
        cache = self._cache
        if key in cache:
            return cache[key]
        if key in visiting:
            return "#CYCLE!"
        sheetname, addr = key
        raw = self._sheets[sheetname].get(addr)
        if not (isinstance(raw, str) and raw.startswith("=")):
            # literal (int/str) or empty (None) — never counted, never cached.
            return raw
        self._eval_counts[sheetname] = self._eval_counts.get(sheetname, 0) + 1
        ast = self._parse(raw[1:])
        if ast is _PARSE_FAIL:
            cache[key] = "#PARSE!"
            self._fwd[key] = frozenset()
            return "#PARSE!"
        visiting.add(key)
        try:
            value = _Evaluator(self, sheetname, visiting).evaluate(ast)
        finally:
            visiting.discard(key)
        cache[key] = value
        refs = self._static_refs(ast, sheetname)
        self._fwd[key] = refs
        for a in refs:
            self._rev.setdefault(a, set()).add(key)
        return value

    def _invalidate(self, key):
        """Drop `key`'s cached result and every result that transitively
        depends on it, cleaning dependency edges so no stale edge survives
        to spuriously invalidate an unrelated cell later (R10 irrelevant-
        edit bound)."""
        visited = set()
        worklist = [key]
        while worklist:
            k = worklist.pop()
            if k in visited:
                continue
            visited.add(k)
            dependents = self._rev.get(k)
            if dependents:
                worklist.extend(dependents)
            self._cache.pop(k, None)
            for a in self._fwd.pop(k, ()):
                bucket = self._rev.get(a)
                if bucket is not None:
                    bucket.discard(k)

    def add_sheet(self, name):
        name = _validate_sheet_name(name)
        if name in self._sheets:
            raise ValueError
        self._sheets[name] = {}
        self._names.setdefault(name, {})
        self._sheet_order.append(name)
        self._eval_counts.setdefault(name, 0)
        self._invalidate_qualifier(name)
        self._record(("add_sheet", name))
        return _Sheet(self, name)

    def sheet(self, name):
        name = _plain_str(name)
        if name not in self._sheets:
            raise ValueError
        return _Sheet(self, name)

    @property
    def sheet_names(self):
        return list(self._sheet_order)

    def undo(self):
        if not self._journal:
            return False
        entry = self._journal.pop()
        self._replaying = True
        try:
            self._apply_entry(entry, undo=True)
        finally:
            self._replaying = False
        self._redo.append(entry)
        return True

    def redo(self):
        if not self._redo:
            return False
        entry = self._redo.pop()
        self._replaying = True
        try:
            self._apply_entry(entry, undo=False)
        finally:
            self._replaying = False
        self._journal.append(entry)
        return True

    def _apply_entry(self, entry, undo):
        kind = entry[0]
        if kind == "cell":
            _, sheetname, addr, prev_exists, prev, new_exists, new = entry
            exists = prev_exists if undo else new_exists
            value = prev if undo else new
            data = self._sheets[sheetname]
            if exists:
                data[addr] = value
            else:
                data.pop(addr, None)
            self._invalidate((sheetname, addr))
            return
        if kind == "name":
            _, sheetname, name, prev_exists, prev, new_exists, new = entry
            exists = prev_exists if undo else new_exists
            value = prev if undo else new
            names = self._names.setdefault(sheetname, {})
            if exists:
                names[name] = value
            else:
                names.pop(name, None)
            self._invalidate_name(sheetname, name)
            return
        if kind == "add_sheet":
            name = entry[1]
            if undo:
                self._sheets.pop(name, None)
                if name in self._sheet_order:
                    self._sheet_order.remove(name)
                self._invalidate_qualifier(name)
                for key in list(self._cache):
                    if key[0] == name:
                        self._cache.pop(key, None)
                        self._fwd.pop(key, None)
            else:
                self._sheets[name] = {}
                self._names.setdefault(name, {})
                if name not in self._sheet_order:
                    self._sheet_order.append(name)
                self._eval_counts.setdefault(name, 0)
                self._invalidate_qualifier(name)
            return
        if kind == "clock":
            _, old, new = entry
            self._clock = old if undo else new
            self._invalidate_volatile()
            return

    def advance_clock(self):
        old = self._clock
        self._clock += 1
        self._invalidate_volatile()
        self._record(("clock", old, self._clock))
        return self._clock

    @property
    def clock(self):
        return self._clock

    def to_json(self):
        sheets = []
        for name in self._sheet_order:
            cells = {}
            for addr, raw in self._sheets[name].items():
                cells[addr] = {"type": "int" if isinstance(raw, int) else "str", "value": raw}
            names = {}
            for name_key, binding in self._names.get(name, {}).items():
                names[name_key] = list(binding)
            sheets.append({"name": name, "cells": cells, "names": names})
        return json.dumps({"version": 1, "clock": self._clock, "sheets": sheets}, separators=(",", ":"))

    @classmethod
    def from_json(cls, s):
        if not isinstance(s, str):
            raise ValueError
        try:
            data = json.loads(str(s))
        except ValueError as exc:
            raise ValueError from exc
        if not isinstance(data, dict) or set(data) != {"version", "clock", "sheets"}:
            raise ValueError
        if not isinstance(data["version"], int) or isinstance(data["version"], bool) or data["version"] != 1:
            raise ValueError
        if not isinstance(data["clock"], int) or isinstance(data["clock"], bool):
            raise ValueError
        sheets_data = data["sheets"]
        if not isinstance(sheets_data, list):
            raise ValueError
        wb = cls()
        wb._clock = data["clock"]
        seen = set()
        pending_names = []
        for sheet_obj in sheets_data:
            if not isinstance(sheet_obj, dict) or set(sheet_obj) != {"name", "cells", "names"}:
                raise ValueError
            name = _validate_sheet_name(sheet_obj["name"])
            if name in seen:
                raise ValueError
            seen.add(name)
            cells_obj = sheet_obj["cells"]
            names_obj = sheet_obj["names"]
            if not isinstance(cells_obj, dict) or not isinstance(names_obj, dict):
                raise ValueError
            wb._sheets[name] = {}
            wb._names[name] = {}
            wb._sheet_order.append(name)
            wb._eval_counts[name] = 0
            for addr_key, cell_obj in cells_obj.items():
                addr = _validate_addr(addr_key)
                if not isinstance(cell_obj, dict) or set(cell_obj) != {"type", "value"}:
                    raise ValueError
                typ = cell_obj["type"]
                value = cell_obj["value"]
                if typ == "int":
                    if not isinstance(value, int) or isinstance(value, bool):
                        raise ValueError
                    wb._sheets[name][addr] = int(value)
                elif typ == "str":
                    if not isinstance(value, str):
                        raise ValueError
                    wb._sheets[name][addr] = str(value)
                else:
                    raise ValueError
            for name_key, binding in names_obj.items():
                name_key = _plain_str(name_key)
                if not _is_name_token(name_key) or not isinstance(binding, list):
                    raise ValueError
                pending_names.append((name, name_key, binding))
        for sheetname, name_key, binding in pending_names:
            if len(binding) == 3 and binding[0] == "addr":
                target_sheet = _validate_sheet_name(binding[1])
                if target_sheet not in wb._sheets:
                    raise ValueError
                wb._names[sheetname][name_key] = ("addr", target_sheet, _validate_addr(binding[2]))
            elif len(binding) == 4 and binding[0] == "range":
                target_sheet = _validate_sheet_name(binding[1])
                if target_sheet not in wb._sheets:
                    raise ValueError
                start = _validate_addr(binding[2])
                end = _validate_addr(binding[3])
                if _valid_range_addrs(("range", ("ref", start), ("ref", end))) is None:
                    raise ValueError
                wb._names[sheetname][name_key] = ("range", target_sheet, start, end)
            else:
                raise ValueError
        return wb
