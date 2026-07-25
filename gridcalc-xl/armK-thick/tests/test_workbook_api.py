"""Task 1.1: Package skeleton and workbook API — R21 surface tests."""
import ast
import importlib
import inspect
import os
import sys
import textwrap
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = os.path.join(os.path.dirname(__file__), "..", "gridcalc")


def _runtime_source_files():
    """Return absolute paths of every .py file in the runtime package (recursive)."""
    out = []
    for dirpath, _dirnames, filenames in os.walk(_PACKAGE_ROOT):
        # Skip __pycache__ directories at any depth.
        if "__pycache__" in dirpath.split(os.sep):
            continue
        for name in sorted(filenames):
            if name.endswith(".py") and not name.startswith("__pycache__"):
                out.append(os.path.join(dirpath, name))
    return out


def _forbidden_imports(tree):
    """Return set of import names that are non-stdlib, file I/O, or network.

    Intra-package imports (gridcalc.*) are allowed.
    Stdlib file I/O and network modules are also forbidden.
    """
    # All stdlib modules available in Python 3.10+ (comprehensive set).
    _STDLIB = {
        "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
        "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
        "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
        "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
        "colorsys", "compileall", "concurrent", "configparser", "contextlib",
        "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
        "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
        "difflib", "dis", "distutils", "doctest", "email", "encodings",
        "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
        "fnmatch", "formatter", "fractions", "ftplib", "functools", "gc",
        "getopt", "getpass", "gettext", "glob", "grp", "gzip", "hashlib",
        "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr",
        "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
        "json", "keyword", "lib2to3", "linecache", "locale", "logging",
        "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
        "mmap", "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
        "numbers", "operator", "optparse", "os", "ossaudiodev", "parser",
        "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "platform", "plistlib", "poplib", "posix", "posixpath", "pprint",
        "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
        "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
        "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
        "selectors", "shelve", "shlex", "shutil", "signal", "site",
        "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
        "sqlite3", "sre_compile", "sre_constants", "sre_parse", "ssl",
        "stat", "statistics", "string", "stringprep", "struct", "subprocess",
        "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
        "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
        "threading", "time", "timeit", "tkinter", "token", "tokenize",
        "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo",
        "types", "typing", "unicodedata", "unittest", "urllib", "uu",
        "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
        "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
        "zipapp", "zipfile", "zipimport", "zlib", "_thread",
        # Also allow common relative imports (no module name).
    }
    # Stdlib modules that are forbidden even though they're stdlib
    # (file I/O, network, etc.).
    _FORBIDDEN_STDLIB = {
        "pathlib", "io", "ftplib", "socket", "http", "urllib", "xmlrpc",
        "xml", "xml.etree", "smtplib", "poplib", "imaplib", "telnetlib",
        "subprocess", "os", "shutil", "tempfile", "fileinput", "filecmp",
        "pickle", "shelve", "dbm", "sqlite3", "zipfile", "tarfile",
        "gzip", "bz2", "lzma", "zlib", "mmap", "ctypes", "fcntl",
        "posixpath", "ntpath", "genericpath",
    }
    forbidden = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Allow intra-package imports (gridcalc.*).
                if alias.name.startswith("gridcalc"):
                    continue
                top = alias.name.split(".")[0]
                if top in _FORBIDDEN_STDLIB:
                    forbidden.add(alias.name)
                elif top not in _STDLIB:
                    forbidden.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                # Allow intra-package imports (gridcalc.*).
                if node.module.startswith("gridcalc"):
                    continue
                top = node.module.split(".")[0]
                if top in _FORBIDDEN_STDLIB:
                    forbidden.add(node.module)
                elif top not in _STDLIB:
                    forbidden.add(node.module)
    return forbidden


def _forbidden_patterns(tree):
    """Return set of disallowed runtime patterns found in the AST."""
    bad = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in ("eval", "exec", "compile", "__import__", "open"):
                bad.add(name)
            if isinstance(func, ast.Attribute) and func.attr == "load":
                # pickle.load etc.
                pass
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("pickle",):
                    bad.add("pickle")
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in ("pickle", "importlib"):
                bad.add(node.module)
    return bad


# ---------------------------------------------------------------------------
# 1. Package import and __all__
# ---------------------------------------------------------------------------

class TestPackageImport:
    def test_import_workbook(self):
        import gridcalc
        assert hasattr(gridcalc, "Workbook")

    def test_all_exports_only_workbook(self):
        import gridcalc
        assert gridcalc.__all__ == ["Workbook"]


# ---------------------------------------------------------------------------
# 2. Empty workbook state
# ---------------------------------------------------------------------------

class TestEmptyWorkbook:
    def setup_method(self):
        from gridcalc import Workbook
        self.wb = Workbook()

    def test_sheet_names_empty(self):
        assert self.wb.sheet_names == []

    def test_clock_zero(self):
        assert self.wb.clock == 0

    def test_undo_empty_returns_false(self):
        assert self.wb.undo() is False

    def test_redo_empty_returns_false(self):
        assert self.wb.redo() is False


# ---------------------------------------------------------------------------
# 3. add_sheet — valid names, handles, creation order
# ---------------------------------------------------------------------------

class TestAddSheet:
    def setup_method(self):
        from gridcalc import Workbook
        self.wb = Workbook()

    def test_add_sheet_returns_handle(self):
        h = self.wb.add_sheet("S1")
        assert h is not None
        assert hasattr(h, "set")
        assert hasattr(h, "get")
        assert hasattr(h, "copy")
        assert hasattr(h, "define_name")
        assert hasattr(h, "eval_count")

    def test_add_sheet_preserves_creation_order(self):
        h1 = self.wb.add_sheet("Alpha")
        h2 = self.wb.add_sheet("Beta")
        h3 = self.wb.add_sheet("Gamma")
        assert self.wb.sheet_names == ["Alpha", "Beta", "Gamma"]

    def test_sheet_names_is_fresh_list(self):
        self.wb.add_sheet("S1")
        a = self.wb.sheet_names
        b = self.wb.sheet_names
        assert a is not b
        assert a == b

    def test_sheet_names_mutation_does_not_affect_wb(self):
        self.wb.add_sheet("S1")
        names = self.wb.sheet_names
        names.append("FAKE")
        assert self.wb.sheet_names == ["S1"]
        names.clear()
        assert self.wb.sheet_names == ["S1"]

    def test_add_sheet_rejects_non_str(self):
        with pytest.raises(ValueError):
            self.wb.add_sheet(123)
        with pytest.raises(ValueError):
            self.wb.add_sheet(None)
        with pytest.raises(ValueError):
            self.wb.add_sheet(["S1"])

    def test_add_sheet_rejects_empty(self):
        with pytest.raises(ValueError):
            self.wb.add_sheet("")

    def test_add_sheet_rejects_too_long(self):
        with pytest.raises(ValueError):
            self.wb.add_sheet("A" * 33)

    def test_add_sheet_rejects_first_char_digit(self):
        with pytest.raises(ValueError):
            self.wb.add_sheet("1Sheet")

    def test_add_sheet_rejects_first_char_underscore(self):
        with pytest.raises(ValueError):
            self.wb.add_sheet("_Sheet")

    def test_add_sheet_rejects_invalid_chars(self):
        with pytest.raises(ValueError):
            self.wb.add_sheet("Sheet Name")  # space
        with pytest.raises(ValueError):
            self.wb.add_sheet("Sheet-Name")  # hyphen
        with pytest.raises(ValueError):
            self.wb.add_sheet("Sheet.Name")  # dot

    def test_add_sheet_rejects_duplicate(self):
        self.wb.add_sheet("S1")
        with pytest.raises(ValueError):
            self.wb.add_sheet("S1")

    def test_add_sheet_case_sensitive(self):
        # Names are case-sensitive: "S1" and "s1" are different valid names.
        h1 = self.wb.add_sheet("S1")
        h2 = self.wb.add_sheet("s1")
        assert h1 is not h2
        assert self.wb.sheet_names == ["S1", "s1"]

    def test_add_sheet_accepts_str_subclass(self):
        class MyStr(str):
            pass
        h = self.wb.add_sheet(MyStr("S1"))
        assert h is not None
        # stored name should be plain str
        assert self.wb.sheet_names == ["S1"]
        assert isinstance(self.wb.sheet_names[0], str)
        assert type(self.wb.sheet_names[0]) is str

    def test_add_sheet_valid_names(self):
        valid = ["A", "Z", "Sheet1", "MySheet", "a1", "abc_xyz", "S" * 32]
        for name in valid:
            self.wb.add_sheet(name)
        assert self.wb.sheet_names == valid


# ---------------------------------------------------------------------------
# 4. sheet() — existing, unknown, invalid, non-str
# ---------------------------------------------------------------------------

class TestSheet:
    def setup_method(self):
        from gridcalc import Workbook
        self.wb = Workbook()
        self.wb.add_sheet("S1")
        self.wb.add_sheet("S2")

    def test_sheet_returns_handle_for_existing(self):
        h = self.wb.sheet("S1")
        assert h is not None
        assert hasattr(h, "set")

    def test_sheet_same_handle_for_same_name(self):
        h1 = self.wb.sheet("S1")
        h2 = self.wb.sheet("S1")
        # May or may not be same object; both must work.
        assert h1 is not None
        assert h2 is not None

    def test_sheet_raises_for_unknown(self):
        with pytest.raises(ValueError):
            self.wb.sheet("NonExistent")

    def test_sheet_raises_for_non_str(self):
        with pytest.raises(ValueError):
            self.wb.sheet(123)
        with pytest.raises(ValueError):
            self.wb.sheet(None)

    def test_sheet_raises_for_invalid_name(self):
        with pytest.raises(ValueError):
            self.wb.sheet("")
        with pytest.raises(ValueError):
            self.wb.sheet("1Bad")
        with pytest.raises(ValueError):
            self.wb.sheet("Bad Name")

    def test_sheet_accepts_str_subclass(self):
        class MyStr(str):
            pass
        h = self.wb.sheet(MyStr("S1"))
        assert h is not None


# ---------------------------------------------------------------------------
# 5. Public surface — no extra public attrs
# ---------------------------------------------------------------------------

class TestPublicSurface:
    def test_workbook_public_attrs(self):
        from gridcalc import Workbook
        wb = Workbook()
        # Get all non-underscore, non-dunder public attributes.
        public = {
            name for name in dir(wb)
            if not name.startswith("_")
        }
        expected = {
            "add_sheet", "sheet", "sheet_names", "undo", "redo",
            "advance_clock", "clock", "to_json", "from_json",
        }
        extra = public - expected
        assert extra == set(), f"Unexpected public attrs on Workbook: {extra}"

    def test_sheet_handle_public_attrs(self):
        from gridcalc import Workbook
        wb = Workbook()
        h = wb.add_sheet("S1")
        public = {
            name for name in dir(h)
            if not name.startswith("_")
        }
        expected = {
            "set", "get", "copy", "define_name", "eval_count",
        }
        extra = public - expected
        assert extra == set(), f"Unexpected public attrs on sheet handle: {extra}"


# ---------------------------------------------------------------------------
# 6. Static checks — stdlib only, no I/O, no network, no dangerous patterns
# ---------------------------------------------------------------------------

class TestStaticChecks:
    def test_no_forbidden_imports_in_init(self):
        src = os.path.join(_PACKAGE_ROOT, "__init__.py")
        tree = ast.parse(open(src).read(), src)
        bad = _forbidden_imports(tree)
        assert bad == set(), f"Forbidden imports in __init__.py: {bad}"

    def test_no_forbidden_imports_in_workbook(self):
        src = os.path.join(_PACKAGE_ROOT, "workbook.py")
        tree = ast.parse(open(src).read(), src)
        bad = _forbidden_imports(tree)
        assert bad == set(), f"Forbidden imports in workbook.py: {bad}"

    def test_no_forbidden_patterns_in_init(self):
        src = os.path.join(_PACKAGE_ROOT, "__init__.py")
        tree = ast.parse(open(src).read(), src)
        bad = _forbidden_patterns(tree)
        assert bad == set(), f"Forbidden patterns in __init__.py: {bad}"

    def test_no_forbidden_patterns_in_workbook(self):
        src = os.path.join(_PACKAGE_ROOT, "workbook.py")
        tree = ast.parse(open(src).read(), src)
        bad = _forbidden_patterns(tree)
        assert bad == set(), f"Forbidden patterns in workbook.py: {bad}"

    def test_all_runtime_files_no_forbidden_imports(self):
        for src in _runtime_source_files():
            tree = ast.parse(open(src).read(), src)
            bad = _forbidden_imports(tree)
            assert bad == set(), (
                f"Forbidden imports in {os.path.basename(src)}: {bad}"
            )

    def test_all_runtime_files_no_forbidden_patterns(self):
        for src in _runtime_source_files():
            tree = ast.parse(open(src).read(), src)
            bad = _forbidden_patterns(tree)
            assert bad == set(), (
                f"Forbidden patterns in {os.path.basename(src)}: {bad}"
            )


# ---------------------------------------------------------------------------
# 7. Required public attrs (complement to "no extra" checks)
# ---------------------------------------------------------------------------

class TestRequiredPublicAttrs:
    def test_workbook_has_all_required_attrs(self):
        from gridcalc import Workbook
        wb = Workbook()
        required = {
            "add_sheet", "sheet", "sheet_names", "undo", "redo",
            "advance_clock", "clock", "to_json", "from_json",
        }
        present = {
            name for name in dir(wb)
            if not name.startswith("_")
        }
        missing = required - present
        assert missing == set(), f"Missing required public attrs on Workbook: {missing}"

    def test_sheet_handle_has_all_required_attrs(self):
        from gridcalc import Workbook
        wb = Workbook()
        h = wb.add_sheet("S1")
        required = {"set", "get", "copy", "define_name", "eval_count"}
        present = {
            name for name in dir(h)
            if not name.startswith("_")
        }
        missing = required - present
        assert missing == set(), (
            f"Missing required public attrs on sheet handle: {missing}"
        )


# ---------------------------------------------------------------------------
# 8. Forbidden runtime patterns include open()
# ---------------------------------------------------------------------------

class TestForbiddenPatternsOpen:
    def test_open_call_is_flagged(self):
        """A file containing a direct open() call must be flagged."""
        src = os.path.join(_PACKAGE_ROOT, "workbook.py")
        tree = ast.parse(open(src).read(), src)
        bad = _forbidden_patterns(tree)
        assert "open" not in bad, (
            f"open() should NOT be flagged (it's not in workbook.py)"
        )
        # Construct a synthetic tree with open() and verify it IS flagged.
        synthetic = ast.parse("open('/tmp/x')")
        bad_synthetic = _forbidden_patterns(synthetic)
        assert "open" in bad_synthetic, (
            f"_forbidden_patterns must flag direct open() calls, got: {bad_synthetic}"
        )


# ---------------------------------------------------------------------------
# 9. _runtime_source_files must recurse into subpackages
# ---------------------------------------------------------------------------

class TestRuntimeSourceFilesRecursive:
    def test_runtime_source_files_is_recursive(self):
        """_runtime_source_files must walk subdirectories, not just top-level."""
        files = _runtime_source_files()
        basenames = {os.path.basename(f) for f in files}
        # At minimum, __init__.py and workbook.py must be found.
        assert "__init__.py" in basenames
        assert "workbook.py" in basenames
        # Verify it would also find files in a subpackage if one existed.
        sub_dir = os.path.join(_PACKAGE_ROOT, "subpkg_test_marker")
        os.makedirs(sub_dir, exist_ok=True)
        try:
            marker = os.path.join(sub_dir, "marker.py")
            with open(marker, "w") as f:
                f.write("# marker\n")
            files_after = _runtime_source_files()
            basenames_after = {os.path.basename(f) for f in files_after}
            assert "marker.py" in basenames_after, (
                f"_runtime_source_files must recurse; found: {basenames_after}"
            )
        finally:
            os.remove(marker)
            os.rmdir(sub_dir)


# ---------------------------------------------------------------------------
# 10. str subclass __str__ bypass must be rejected
# ---------------------------------------------------------------------------

class TestStrSubclassNormalization:
    def test_add_sheet_rejects_str_subclass_with_invalid_str(self):
        """A str subclass whose __str__ returns invalid text must be rejected."""
        from gridcalc import Workbook
        wb = Workbook()

        class BadStr(str):
            def __str__(self):
                return "1BadName"  # starts with digit — invalid

        with pytest.raises(ValueError):
            wb.add_sheet(BadStr("valid_input"))

    def test_add_sheet_stores_normalized_str_for_subclass(self):
        """A str subclass whose __str__ returns different text: normalize
        first per spec, so the overridden result is what gets stored and
        validated. This prevents bypass via overridden __str__."""
        from gridcalc import Workbook
        wb = Workbook()

        class AltStr(str):
            def __str__(self):
                return "Different"  # different from original

        wb.add_sheet(AltStr("RealName"))
        assert wb.sheet_names == ["Different"], (
            f"Expected ['Different'] (normalized) but got {wb.sheet_names}"
        )
        assert type(wb.sheet_names[0]) is str

    def test_sheet_rejects_str_subclass_with_invalid_str(self):
        """sheet() must also reject str subclasses whose __str__ is invalid."""
        from gridcalc import Workbook
        wb = Workbook()
        wb.add_sheet("S1")

        class BadStr(str):
            def __str__(self):
                return ""  # empty — invalid

        with pytest.raises(ValueError):
            wb.sheet(BadStr("S1"))


# ---------------------------------------------------------------------------
# 11. Callable stubs and read-only properties (prior finding fix)
# ---------------------------------------------------------------------------

class TestCallableStubsAndReadOnly:
    def test_sheet_set_is_callable(self):
        """sheet.set() must be callable (implemented in task 1.2)."""
        from gridcalc import Workbook
        wb = Workbook()
        h = wb.add_sheet("S1")
        assert callable(h.set)
        # Should not raise; task 1.2 implements set.
        h.set("A1", 1)

    def test_sheet_get_is_callable(self):
        """sheet.get() must be callable (implemented in task 1.2)."""
        from gridcalc import Workbook
        wb = Workbook()
        h = wb.add_sheet("S1")
        assert callable(h.get)
        # Should not raise; task 1.2 implements get.
        h.set("A1", 1)
        assert h.get("A1") == 1

    def test_sheet_copy_is_callable_stub(self):
        """sheet.copy() must be a callable stub that raises NotImplementedError."""
        from gridcalc import Workbook
        wb = Workbook()
        h = wb.add_sheet("S1")
        assert callable(h.copy)
        with pytest.raises(NotImplementedError):
            h.copy("A1", "B1")

    def test_sheet_define_name_is_callable(self):
        """sheet.define_name() must be a callable that binds names."""
        from gridcalc import Workbook
        wb = Workbook()
        h = wb.add_sheet("S1")
        assert callable(h.define_name)
        # Should work without raising
        h.define_name("MYNAME", "A1")
        assert h._names["MYNAME"] == "A1"

    def test_workbook_to_json_is_callable(self):
        """Workbook.to_json() must be callable and return JSON text."""
        from gridcalc import Workbook
        wb = Workbook()
        assert callable(wb.to_json)
        assert isinstance(wb.to_json(), str)

    def test_workbook_from_json_is_callable(self):
        """Workbook.from_json() must be callable and return a workbook."""
        from gridcalc import Workbook
        assert callable(Workbook.from_json)
        wb = Workbook.from_json('{"version":1,"clock":0,"sheets":[]}')
        assert isinstance(wb, Workbook)

    def test_workbook_advance_clock_increments_clock(self):
        """Workbook.advance_clock() must increment and return the workbook clock."""
        from gridcalc import Workbook
        wb = Workbook()
        assert callable(wb.advance_clock)
        assert wb.advance_clock() == 1
        assert wb.clock == 1

    def test_clock_is_read_only_property(self):
        """Workbook.clock must be a read-only property (cannot be set)."""
        from gridcalc import Workbook
        wb = Workbook()
        assert wb.clock == 0
        with pytest.raises(AttributeError):
            wb.clock = 5

    def test_eval_count_is_read_only_property(self):
        """SheetHandle.eval_count must be a read-only property (cannot be set)."""
        from gridcalc import Workbook
        wb = Workbook()
        h = wb.add_sheet("S1")
        assert h.eval_count == 0
        with pytest.raises(AttributeError):
            h.eval_count = 10
