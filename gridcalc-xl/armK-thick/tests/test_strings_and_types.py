"""Task 5.1: String literals and type rules (R13).

Covers:
- String literal parsing with no escapes, preserving every non-quote character
  including newlines and control characters.
- Arithmetic, unary minus, and ordering comparisons reject string operands
  with #TYPE! according to R5 textual left-to-right precedence.
- = and <> compare two ints or two strings and return 1 or 0; mixed
  int/string comparisons return #TYPE!.
- Operands after the first type offender or error are not evaluated, with
  eval_count evidence.
"""
import pytest

from gridcalc.formula import (
    PARSE_ERROR, DIV_ERROR, TYPE_ERROR, REF_ERROR,
    parse_formula,
)
from gridcalc.workbook import Workbook


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wb_with(cells):
    """Create a workbook with one sheet and set the given cells."""
    wb = Workbook()
    sh = wb.add_sheet("S1")
    for addr, value in cells.items():
        sh.set(addr, value)
    return wb, sh


# ---------------------------------------------------------------------------
# 1. String literal parsing (criterion 1)
# ---------------------------------------------------------------------------

class TestStringLiteralParsing:
    def test_empty_string(self):
        """Empty string literal evaluates to empty string."""
        assert parse_formula('""') == ""

    def test_simple_string(self):
        """Simple string literal evaluates to its content."""
        assert parse_formula('"hello"') == "hello"

    def test_string_with_spaces(self):
        """Spaces inside a string literal are preserved."""
        assert parse_formula('"hello world"') == "hello world"

    def test_string_with_special_chars(self):
        """Special characters inside a string literal are preserved."""
        assert parse_formula('"a!@#$%^&*()"') == "a!@#$%^&*()"

    def test_string_with_newline(self):
        """A newline inside a string literal is preserved verbatim."""
        # Formula text is the part after '='; \n is an actual newline char.
        assert parse_formula('"hello\nworld"') == "hello\nworld"

    def test_string_with_control_chars(self):
        """Control characters inside a string literal are preserved verbatim."""
        assert parse_formula('"\x01\x02\x03"') == "\x01\x02\x03"

    def test_string_with_tab(self):
        """A tab inside a string literal is preserved."""
        assert parse_formula('"\thello\t"') == "\thello\t"

    def test_string_with_equals_sign(self):
        """An = inside a string literal is preserved (not treated as operator)."""
        assert parse_formula('"a=b"') == "a=b"

    def test_string_with_formula_like_content(self):
        """A string that looks like a formula is preserved as a string."""
        assert parse_formula('"=1+2"') == "=1+2"

    def test_string_with_backslash(self):
        """A backslash inside a string literal is preserved (no escape processing)."""
        assert parse_formula('"a\\b"') == "a\\b"

    def test_string_with_angle_brackets(self):
        """Angle brackets inside a string literal are preserved."""
        assert parse_formula('"a<b>c"') == "a<b>c"

    def test_string_with_parens(self):
        """Parentheses inside a string literal are preserved."""
        assert parse_formula('"a(b)c"') == "a(b)c"

    def test_string_with_colon(self):
        """A colon inside a string literal is preserved."""
        assert parse_formula('"a:b"') == "a:b"

    def test_string_with_plus(self):
        """A plus sign inside a string literal is preserved."""
        assert parse_formula('"a+b"') == "a+b"

    def test_string_with_star(self):
        """A star inside a string literal is preserved."""
        assert parse_formula('"a*b"') == "a*b"

    def test_string_with_slash(self):
        """A slash inside a string literal is preserved."""
        assert parse_formula('"a/b"') == "a/b"

    def test_unterminated_string_returns_parse_error(self):
        """An unterminated string literal returns #PARSE!."""
        assert parse_formula('"hello') == PARSE_ERROR

    def test_string_with_double_quote_inside_returns_parse_error(self):
        """A double quote inside a string literal is not allowed (no escapes)."""
        # '"a"b"' parses as: STR("a") then b" which is invalid syntax.
        assert parse_formula('"a"b"') == PARSE_ERROR

    def test_string_with_single_quote(self):
        """A single quote inside a string literal is preserved."""
        assert parse_formula('"a\'b"') == "a'b"

    def test_string_with_unicode(self):
        """Unicode characters inside a string literal are preserved."""
        assert parse_formula('"héllo"') == "héllo"

    def test_string_with_null_byte(self):
        """A null byte inside a string literal is preserved."""
        assert parse_formula('"a\x00b"') == "a\x00b"

    def test_string_with_carriage_return(self):
        """A carriage return inside a string literal is preserved."""
        assert parse_formula('"a\rb"') == "a\rb"

    def test_string_used_in_comparison(self):
        """A string literal can be used as an operand in a comparison."""
        assert parse_formula('"a"="a"') == 1
        assert parse_formula('"a"="b"') == 0

    def test_string_used_in_addition_rejected(self):
        """A string literal cannot be used in addition."""
        assert parse_formula('"a"+1') == TYPE_ERROR


# ---------------------------------------------------------------------------
# 2. Arithmetic / unary minus / ordering reject strings (criterion 2)
# ---------------------------------------------------------------------------

class TestStringRejectionInArithmetic:
    def test_string_plus_int(self):
        """String + int -> #TYPE!."""
        assert parse_formula('"x"+1') == TYPE_ERROR

    def test_int_plus_string(self):
        """int + string -> #TYPE!."""
        assert parse_formula('1+"x"') == TYPE_ERROR

    def test_string_minus_int(self):
        """String - int -> #TYPE!."""
        assert parse_formula('"x"-1') == TYPE_ERROR

    def test_string_multiply_int(self):
        """String * int -> #TYPE!."""
        assert parse_formula('"x"*2') == TYPE_ERROR

    def test_string_divide_int(self):
        """String / int -> #TYPE!."""
        assert parse_formula('"x"/2') == TYPE_ERROR

    def test_unary_minus_on_string(self):
        """Unary minus on string -> #TYPE!."""
        assert parse_formula('-"x"') == TYPE_ERROR

    def test_string_less_than_int(self):
        """String < int -> #TYPE!."""
        assert parse_formula('"x"<1') == TYPE_ERROR

    def test_string_leq_int(self):
        """String <= int -> #TYPE!."""
        assert parse_formula('"x"<=1') == TYPE_ERROR

    def test_string_gt_int(self):
        """String > int -> #TYPE!."""
        assert parse_formula('"x">1') == TYPE_ERROR

    def test_string_geq_int(self):
        """String >= int -> #TYPE!."""
        assert parse_formula('"x">=1') == TYPE_ERROR

    def test_int_less_than_string(self):
        """int < string -> #TYPE!."""
        assert parse_formula('1<"x"') == TYPE_ERROR

    def test_string_ref_in_addition(self):
        """A1 (string) + 1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=A1+1")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_ref_in_unary_minus(self):
        """-A1 where A1 is a string -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=-A1")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_ref_in_ordering(self):
        """A1 (string) < 1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=A1<1")
        assert sh.get("C1") == TYPE_ERROR


# ---------------------------------------------------------------------------
# 3. = and <> compare same types; mixed -> #TYPE! (criterion 3)
# ---------------------------------------------------------------------------

class TestEqualityAndInequality:
    def test_int_eq_int_same(self):
        """int = int (same) -> 1."""
        assert parse_formula('1=1') == 1

    def test_int_eq_int_diff(self):
        """int = int (diff) -> 0."""
        assert parse_formula('1=2') == 0

    def test_string_eq_string_same(self):
        """String = string (same) -> 1."""
        assert parse_formula('"a"="a"') == 1

    def test_string_eq_string_diff(self):
        """String = string (diff) -> 0."""
        assert parse_formula('"a"="b"') == 0

    def test_string_eq_case_sensitive(self):
        """String = string (case-diff) -> 0 (case-sensitive)."""
        assert parse_formula('"A"="a"') == 0

    def test_string_eq_exact_codepoint(self):
        """String = string (exact) -> 1."""
        assert parse_formula('"ab"="ab"') == 1

    def test_string_eq_different_lengths(self):
        """String = string (diff length) -> 0."""
        assert parse_formula('"a"="ab"') == 0

    def test_int_neq_int_same(self):
        """int <> int (same) -> 0."""
        assert parse_formula('1<>1') == 0

    def test_int_neq_int_diff(self):
        """int <> int (diff) -> 1."""
        assert parse_formula('1<>2') == 1

    def test_string_neq_string_same(self):
        """String <> string (same) -> 0."""
        assert parse_formula('"a"<> "a"') == 0

    def test_string_neq_string_diff(self):
        """String <> string (diff) -> 1."""
        assert parse_formula('"a"<> "b"') == 1

    def test_mixed_int_string_eq(self):
        """int = string -> #TYPE!."""
        assert parse_formula('1="x"') == TYPE_ERROR

    def test_mixed_string_int_eq(self):
        """string = int -> #TYPE!."""
        assert parse_formula('"x"=1') == TYPE_ERROR

    def test_mixed_int_string_neq(self):
        """int <> string -> #TYPE!."""
        assert parse_formula('1<>"x"') == TYPE_ERROR

    def test_mixed_string_int_neq(self):
        """string <> int -> #TYPE!."""
        assert parse_formula('"x"<>1') == TYPE_ERROR

    def test_string_ordering_rejected(self):
        """String < string -> #TYPE! (string orderings not permitted)."""
        assert parse_formula('"a"<"b"') == TYPE_ERROR

    def test_string_leq_rejected(self):
        """String <= string -> #TYPE!."""
        assert parse_formula('"a"<= "b"') == TYPE_ERROR

    def test_string_geq_rejected(self):
        """String >= string -> #TYPE!."""
        assert parse_formula('"a">= "b"') == TYPE_ERROR

    def test_string_gt_rejected(self):
        """String > string -> #TYPE!."""
        assert parse_formula('"a">"b"') == TYPE_ERROR


# ---------------------------------------------------------------------------
# 4. Left-to-right short-circuit with eval_count (criterion 4)
# ---------------------------------------------------------------------------

class TestLeftToRightShortCircuit:
    def test_string_first_offender_in_addition(self):
        """String first offender in addition: ="x"+A1 -> #TYPE! regardless of A1."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", '="x"+A1')
        assert sh.get("C1") == TYPE_ERROR

    def test_error_first_offender_in_addition(self):
        """Error first offender in addition: =A1+"x" with A1=#DIV! -> #DIV!."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", '=A1+"x"')
        assert sh.get("C1") == DIV_ERROR

    def test_eval_count_skips_after_type_error_with_callback(self):
        """="x"+A1: A1 is not evaluated (verified via eval_count callback)."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("int", 42)

        result = parse_formula('"x"+A1', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" not in eval_log

    def test_eval_count_with_ref_first_in_type_error(self):
        """A1+"x" with A1 resolving to int: A1 is evaluated, result is #TYPE!."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("int", 0)

        result = parse_formula('A1+"x"', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" in eval_log

    def test_eval_count_with_string_ref_first(self):
        """A1+"x" with A1 being a string ref: A1 is evaluated, result is #TYPE!."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("str", "hello")
            return ("int", 0)

        result = parse_formula('A1+"x"', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" in eval_log

    def test_eval_count_with_error_ref_first(self):
        """A1+"x" with A1=#DIV!: A1 is evaluated, result is #DIV!."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            return ("int", 0)

        result = parse_formula('A1+"x"', resolve_ref=resolve_ref)
        assert result == DIV_ERROR
        assert "A1" in eval_log

    def test_eval_count_zero_for_string_only(self):
        """String literal has no refs, so eval_count should be 0."""
        # Use workbook to test eval_count (it tracks formula cell evaluations).
        wb, sh = _wb_with({})
        sh.set("C1", '="x"')
        assert sh.get("C1") == "x"
        assert sh.eval_count == 1  # Only C1 was evaluated

    def test_eval_count_with_one_ref(self):
        """Single ref: eval_count reflects the formula cell evaluation."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", "=A1")
        assert sh.get("C1") == 42
        assert sh.eval_count == 1  # Only C1 was evaluated

    def test_eval_count_short_circuit_in_multiplication(self):
        """String * A1: A1 is not evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("int", 42)

        result = parse_formula('"x"*A1', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" not in eval_log

    def test_eval_count_short_circuit_in_division(self):
        """String / A1: A1 is not evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("int", 42)

        result = parse_formula('"x"/A1', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" not in eval_log

    def test_eval_count_short_circuit_in_unary_minus(self):
        """-A1 where A1 is string: A1 is evaluated but result is #TYPE!."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("str", "hello")

        result = parse_formula('-A1', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" in eval_log

    def test_eval_count_short_circuit_in_comparison_left_string(self):
        """String < A1: A1 is not evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("int", 42)

        result = parse_formula('"x"<A1', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" not in eval_log

    def test_eval_count_short_circuit_in_comparison_right_string(self):
        """int < string: no refs evaluated, result is #TYPE!."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("int", 42)

        result = parse_formula('1<"x"', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert eval_log == []

    def test_eval_count_comparison_with_string_refs(self):
        """A1="x" with A1 being a string: A1 is evaluated, result is 0."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("str", "hello")
            return ("int", 0)

        result = parse_formula('A1="x"', resolve_ref=resolve_ref)
        assert result == 0
        assert "A1" in eval_log

    def test_chained_addition_short_circuit(self):
        """String + A1 + 1: A1 is not evaluated due to left-to-right short-circuit."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            return ("int", 42)

        result = parse_formula('"x"+A1+1', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" not in eval_log

    def test_chained_comparison_short_circuit(self):
        """A1="x"=B1 with A1=str: both evaluated, result is 0."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("str", "hello")
            if addr == "B1":
                return ("int", 42)
            return ("int", 0)

        result = parse_formula('A1="x"=B1', resolve_ref=resolve_ref)
        assert result == 0
        assert "A1" in eval_log
        assert "B1" in eval_log

    def test_chained_comparison_short_circuit_type_error(self):
        """A1+B1="x" with A1=str: B1 is not evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("str", "y")
            if addr == "B1":
                return ("int", 42)
            return ("int", 0)

        result = parse_formula('A1+B1="x"', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" in eval_log
        assert "B1" not in eval_log


# ---------------------------------------------------------------------------
# 5. Reference model differential tests
# ---------------------------------------------------------------------------

class TestDifferential:
    """Compare implementation against independent reference model."""

    def _ref_eval(self, formula_text, resolve_ref=None):
        """Evaluate using the reference model."""
        from tests.reference_model import (
            _ref_tokenize, _ref_parse_expr, _ref_evaluate,
            _RefErrorValue,
        )

        tokens = _ref_tokenize(formula_text)
        if tokens is None:
            return "#PARSE!"

        pos = [0]
        ast_node = _ref_parse_expr(tokens, pos)
        if ast_node is None or pos[0] != len(tokens):
            return "#PARSE!"

        eval_count = [0]
        result = _ref_evaluate(ast_node, resolve_ref, eval_count)

        if isinstance(result, _RefErrorValue):
            return result.code
        return result

    @pytest.mark.parametrize("formula_text", [
        '""',
        '"hello"',
        '"hello world"',
        '"a!@#$%^&*()"',
        '"a=b"',
        '"=1+2"',
        '"a\\b"',
        '"a<b>c"',
        '"a(b)c"',
        '"a:b"',
        '"a+b"',
        '"a*b"',
        '"a/b"',
        '"\x01\x02\x03"',
        '"a\x00b"',
        '"a\rb"',
        '"héllo"',
        '1=1',
        '1=2',
        '"a"="a"',
        '"a"="b"',
        '"A"="a"',
        '1<>1',
        '1<>2',
        '"a"<> "a"',
        '"a"<> "b"',
        '1="x"',
        '"x"=1',
        '1<>"x"',
        '"x"<>1',
        '"a"<"b"',
        '"x"+1',
        '1+"x"',
        '"x"-1',
        '"x"*2',
        '"x"/2',
        '-"x"',
        '"x"<1',
        '"x"<=1',
        '"x">1',
        '"x">=1',
        '1<"x"',
    ])
    def test_differential(self, formula_text):
        """Implementation and reference model agree on all these formulas."""
        impl_result = parse_formula(formula_text)
        ref_result = self._ref_eval(formula_text)
        assert impl_result == ref_result, (
            f"Mismatch for {formula_text!r}: impl={impl_result!r}, ref={ref_result!r}"
        )

    @pytest.mark.parametrize("formula_text", [
        '"x"+A1',
        'A1+"x"',
        '"x"*A1',
        '"x"/A1',
        '"x"<A1',
    ])
    def test_differential_short_circuit(self, formula_text):
        """Short-circuit behavior matches reference model."""
        eval_log_impl = []
        eval_log_ref = []

        def resolve_ref_impl(addr):
            eval_log_impl.append(addr)
            if addr == "A1":
                return ("int", 42)
            return ("int", 0)

        def resolve_ref_ref(addr):
            eval_log_ref.append(addr)
            if addr == "A1":
                return ("int", 42)
            return ("int", 0)

        impl_result = parse_formula(formula_text, resolve_ref=resolve_ref_impl)
        ref_result = self._ref_eval(formula_text, resolve_ref=resolve_ref_ref)

        assert impl_result == ref_result, (
            f"Mismatch for {formula_text!r}: impl={impl_result!r}, ref={ref_result!r}"
        )
        assert eval_log_impl == eval_log_ref, (
            f"Eval log mismatch for {formula_text!r}: "
            f"impl={eval_log_impl}, ref={eval_log_ref}"
        )
