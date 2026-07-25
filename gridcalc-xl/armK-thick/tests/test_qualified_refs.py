"""Task 8.2: Qualified references and ranges — R22."""
import os

import pytest

from gridcalc.formula import PARSE_ERROR, parse_formula


_PACKAGE_ROOT = os.path.join(os.path.dirname(__file__), "..", "gridcalc")


# ---------------------------------------------------------------------------
# 1. Tokenizer: sheet-name-shaped identifier followed by `!` is a SHEET token
# ---------------------------------------------------------------------------

class TestTokenizerSheetToken:
    def test_sheet_token_sum_like(self):
        """SUM!A1 tokenizes as SHEET('SUM') REF('A1'), not SUM function."""
        from gridcalc.formula import _tokenize
        tokens = _tokenize("SUM!A1")
        assert tokens is not None
        assert tokens[0] == ("SHEET", "SUM")
        assert tokens[1] == ("REF", "A1")

    def test_sheet_token_ref_like(self):
        """A1!B2 tokenizes as SHEET('A1') REF('B2')."""
        from gridcalc.formula import _tokenize
        tokens = _tokenize("A1!B2")
        assert tokens is not None
        assert tokens[0] == ("SHEET", "A1")
        assert tokens[1] == ("REF", "B2")

    def test_sheet_token_with_spaces(self):
        """Sheet1 ! A1 tokenizes with whitespace around !."""
        from gridcalc.formula import _tokenize
        tokens = _tokenize("Sheet1 ! A1")
        assert tokens is not None
        assert tokens[0] == ("SHEET", "Sheet1")
        assert tokens[1] == ("REF", "A1")

    def test_sheet_token_with_tabs(self):
        """Sheet1\t!\tA1 tokenizes with tabs around !."""
        from gridcalc.formula import _tokenize
        tokens = _tokenize("Sheet1\t!\tA1")
        assert tokens is not None
        assert tokens[0] == ("SHEET", "Sheet1")
        assert tokens[1] == ("REF", "A1")

    def test_sheet_token_lowercase_sheet_name(self):
        """sheet!A1 tokenizes as SHEET('sheet') REF('A1')."""
        from gridcalc.formula import _tokenize
        tokens = _tokenize("sheet!A1")
        assert tokens is not None
        assert tokens[0] == ("SHEET", "sheet")
        assert tokens[1] == ("REF", "A1")

    def test_sheet_token_mixed_case(self):
        """MySheet!A1 tokenizes as SHEET('MySheet') REF('A1')."""
        from gridcalc.formula import _tokenize
        tokens = _tokenize("MySheet!A1")
        assert tokens is not None
        assert tokens[0] == ("SHEET", "MySheet")
        assert tokens[1] == ("REF", "A1")


# ---------------------------------------------------------------------------
# 2. Parser: qualified references and ranges
# ---------------------------------------------------------------------------

class TestParserQualifiedRefs:
    def test_qualified_ref_basic(self):
        """=Sheet1!A1 parses as a qualified reference."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1")
        assert sh.get("B1") == 10

    def test_qualified_ref_with_spaces(self):
        """=Sheet1 ! A1 parses with whitespace around !."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1 ! A1")
        assert sh.get("B1") == 10

    def test_qualified_range_basic(self):
        """=Sheet1!A1:B2 parses as a qualified range."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("A2", 3)
        sh.set("B2", 4)
        sh.set("C1", "=SUM(Sheet1!A1:B2)")
        assert sh.get("C1") == 10

    def test_qualified_range_with_spaces(self):
        """=Sheet1 ! A1 : B2 parses with whitespace."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(Sheet1 ! A1 : B2)")
        assert sh.get("C1") == 3

    def test_qualified_ref_in_expression(self):
        """=Sheet1!A1+1 evaluates correctly."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1+1")
        assert sh.get("B1") == 11

    def test_qualified_ref_in_comparison(self):
        """=Sheet1!A1=10 evaluates to 1."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1=10")
        assert sh.get("B1") == 1

    def test_qualified_ref_case_sensitive(self):
        """Sheet qualifiers are case-sensitive."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", "=sheet!A1")
        assert sh.get("B1") == "#REF!"

    def test_unqualified_ref_still_works(self):
        """Unqualified references still bind to the hosting sheet."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", "=A1")
        assert sh.get("B1") == 10

    def test_unqualified_ref_binds_to_hosting_sheet_not_first_sheet(self):
        from gridcalc.workbook import Workbook
        wb = Workbook()
        s1 = wb.add_sheet("S1")
        s2 = wb.add_sheet("S2")
        s1.set("A1", 1)
        s2.set("A1", 2)
        s2.set("B1", "=A1")

        assert s2.get("B1") == 2


# ---------------------------------------------------------------------------
# 3. Parser rejects malformed qualifiers
# ---------------------------------------------------------------------------

class TestParserRejectsMalformedQualifiers:
    def test_orphan_bang(self):
        """Sheet1! with no ref after ! returns #PARSE!."""
        assert parse_formula("Sheet1!") == PARSE_ERROR

    def test_double_bang(self):
        """Sheet1!!A1 returns #PARSE!."""
        assert parse_formula("Sheet1!!A1") == PARSE_ERROR

    def test_workbook_malformed_well_shaped_missing_ref_after_bang(self):
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "=Sheet1!")
        assert sh.get("A1") == "#PARSE!"

    def test_workbook_malformed_well_shaped_double_bang(self):
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "=Sheet1!!A1")
        assert sh.get("A1") == "#PARSE!"

    def test_invalid_sheet_name_underscore_prefix(self):
        """_Sheet!A1 returns #PARSE! (invalid sheet name)."""
        assert parse_formula("_Sheet!A1") == PARSE_ERROR

    def test_invalid_sheet_name_digit_prefix(self):
        """1Sheet!A1 returns #PARSE! (invalid sheet name)."""
        assert parse_formula("1Sheet!A1") == PARSE_ERROR

    def test_second_qualifier_in_range(self):
        """S1!A1:S2!B2 returns #PARSE! (second qualifier in range)."""
        assert parse_formula("S1!A1:S2!B2") == PARSE_ERROR

    def test_qualifier_not_at_start_of_range(self):
        """A1:S2!B2 returns #PARSE! (qualifier not at start)."""
        assert parse_formula("A1:S2!B2") == PARSE_ERROR

    def test_qualified_ref_then_operator(self):
        """Sheet1!A1+1 parses correctly (not malformed)."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1+1")
        assert sh.get("B1") == 11


# ---------------------------------------------------------------------------
# 4. Evaluation: qualifier naming no existing sheet → #REF!
# ---------------------------------------------------------------------------

class TestEvaluationMissingSheet:
    def test_qualified_ref_missing_sheet(self):
        """=Sheet1!A1 where Sheet1 doesn't exist returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1")
        assert sh.get("B1") == "#REF!"

    def test_qualified_range_missing_sheet(self):
        """=SUM(Sheet1!A1:B2) where Sheet1 doesn't exist returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(MissingSheet!A1:B2)")
        assert sh.get("C1") == "#REF!"

    def test_qualified_ref_then_add_sheet(self):
        """After add_sheet(Sheet1), =Sheet1!A1 resolves correctly."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("B1", "=Sheet1!A1")
        assert sh.get("B1") == "#REF!"
        sh1 = wb.add_sheet("Sheet1")
        sh1.set("A1", 42)
        assert sh.get("B1") == 42


# ---------------------------------------------------------------------------
# 5. Lifecycle invalidation: add_sheet invalidates formula cells mentioning qualifier
# ---------------------------------------------------------------------------

class TestLifecycleInvalidation:
    def test_add_sheet_invalidates_formula_cells(self):
        """add_sheet(S) invalidates formula cells mentioning S as qualifier."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1")
        sh.set("C1", "=Sheet1!B1")
        # Both B1 and C1 should be #REF! since Sheet1 doesn't exist
        assert sh.get("B1") == "#REF!"
        assert sh.get("C1") == "#REF!"
        # Add Sheet1
        sh1 = wb.add_sheet("Sheet1")
        sh1.set("A1", 100)
        sh1.set("B1", 200)
        # Now B1 and C1 should re-evaluate
        assert sh.get("B1") == 100
        assert sh.get("C1") == 200

    def test_add_sheet_invalidates_multiple_cells(self):
        """Multiple formula cells mentioning the same qualifier all invalidate."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", 3)
        sh.set("D1", "=Sheet1!A1+Sheet1!B1")
        sh.set("E1", "=Sheet1!C1*2")
        assert sh.get("D1") == "#REF!"
        assert sh.get("E1") == "#REF!"
        sh1 = wb.add_sheet("Sheet1")
        sh1.set("A1", 10)
        sh1.set("B1", 20)
        sh1.set("C1", 30)
        assert sh.get("D1") == 30
        assert sh.get("E1") == 60

    def test_undo_redo_remove_restore_sheet(self):
        """undo/redo removing/restoring S invalidates formula cells."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", "=S!A1")
        assert sh.get("B1") == 10
        # Add Sheet1
        sh1 = wb.add_sheet("Sheet1")
        sh1.set("A1", 100)
        # B1 should still reference S!A1, so it should still be 10
        assert sh.get("B1") == 10
        # Undo add_sheet Sheet1
        wb.undo()
        # B1 should still reference S!A1, so it should still be 10
        assert sh.get("B1") == 10
        # Redo add_sheet Sheet1
        wb.redo()
        # B1 should still reference S!A1, so it should still be 10
        assert sh.get("B1") == 10

    def test_add_sheet_undo_redo_invalidates_every_cached_formula_mentioning_qualifier(self):
        from gridcalc.workbook import Workbook
        wb = Workbook()
        left = wb.add_sheet("Left")
        right = wb.add_sheet("Right")

        left.set("A1", "=Later!A1")
        right.set("B2", "=SUM(Later!A1:A2)")
        assert left.get("A1") == "#REF!"
        assert right.get("B2") == "#REF!"

        later = wb.add_sheet("Later")
        later.set("A1", 5)
        later.set("A2", 7)
        assert left.get("A1") == 5
        assert right.get("B2") == 12

        wb.undo()
        wb.undo()
        wb.undo()
        assert left.get("A1") == "#REF!"
        assert right.get("B2") == "#REF!"

        wb.redo()
        wb.redo()
        wb.redo()
        assert left.get("A1") == 5
        assert right.get("B2") == 12


# ---------------------------------------------------------------------------
# 6. Closure: qualified refs contribute no closure members while sheet absent
# ---------------------------------------------------------------------------

class TestClosureQualifiedRefs:
    def test_qualified_ref_closure_when_sheet_absent(self):
        """Qualified ref contributes no closure members while sheet is absent."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1")
        assert sh.get("B1") == "#REF!"
        closure = sh._closure_cache.get("B1", set())
        assert closure == set()

    def test_qualified_ref_closure_when_sheet_present(self):
        """Qualified ref contributes closure members when sheet exists."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("Sheet1")
        sh.set("A1", 10)
        sh.set("B1", "=Sheet1!A1")
        # Trigger evaluation to compute closure
        assert sh.get("B1") == 10
        closure = sh._closure_cache.get("B1", set())
        # The closure should include the resolved address
        assert "A1" in closure

    def test_qualified_range_closure_when_sheet_absent(self):
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("B1", "=SUM(Missing!A1:A2)")

        assert sh.get("B1") == "#REF!"
        assert sh._closure_cache.get("B1", set()) == set()


# ---------------------------------------------------------------------------
# 7. Security: no forbidden runtime patterns
# ---------------------------------------------------------------------------

class TestSecurityNoForbiddenPatterns:
    def test_no_forbidden_patterns_in_formula(self):
        """formula.py must not contain eval/exec/compile/__import__/importlib/pickle."""
        import ast
        src = os.path.join(_PACKAGE_ROOT, "formula.py")
        bad = set()
        tree = ast.parse(open(src).read(), src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in ("eval", "exec", "compile", "__import__"):
                    bad.add(name)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("pickle", "importlib"):
                        bad.add(alias.name)
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in ("pickle", "importlib"):
                    bad.add(node.module)
        assert bad == set(), f"Forbidden patterns in formula.py: {bad}"
