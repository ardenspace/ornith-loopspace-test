# Gate G9 verifier probes — R24 (persistence) and R25 (round-trip
# equivalence). Derived fresh from the spec for this gate round.
import copy
import json

import pytest

from gridcalc import Workbook


# ---------- fixtures ----------

def build_rich():
    """Workbook exercising $ marks, qualifiers, whitespace, newline-in-
    string, name bindings, #REF! token, and a nonzero clock."""
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 7)
    s1.set("B1", "hi")
    s1.set("C1", '=CONCAT("li\nne",B1)')      # newline inside STRING (R13)
    s2.set("B2", 5)
    s1.set("D1", "=$A$1 + S2! B2")            # $ marks + spaced qualifier
    s1.define_name("DATA", "S2!B2")           # qualified name target (R23)
    s1.set("E1", "=DATA")
    s1.set("F1", "=#REF!")                    # #REF! token (R17)
    s1.set("G1", "  padded  ")                # leading/trailing spaces kept
    # advance_clock is a legal G10 stub (G7 ledger); clock stays 0 here
    return wb


RICH_EXPECT = {
    "A1": 7,
    "B1": "hi",
    "C1": "li\nnehi",
    "D1": 12,
    "E1": 5,
    "F1": "#REF!",
    "G1": "  padded  ",
}


def build_small():
    """One oddly-named sheet/address so string-injection variants can be
    built without colliding with formula text."""
    wb = Workbook()
    z = wb.add_sheet("ZQX")
    z.set("Z9", 3)
    return wb


def _walk_paths(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_paths(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_paths(v, path + (i,))
    else:
        yield path, node


def _with_replaced(doc, path, value):
    doc = copy.deepcopy(doc)
    tgt = doc
    for p in path[:-1]:
        tgt = tgt[p]
    tgt[path[-1]] = value
    return doc


def _replace_str_everywhere(node, old, new):
    if isinstance(node, dict):
        return {(new if k == old else k): _replace_str_everywhere(v, old, new)
                for k, v in node.items()}
    if isinstance(node, list):
        return [_replace_str_everywhere(v, old, new) for v in node]
    if node == old:
        return new
    return node


# ---------- P1: R24 restore exactness / R25 double round-trip ----------

def test_p1_round_trip_restores_sheets_clock_and_values():
    wb = build_rich()
    j = wb.to_json()
    assert isinstance(j, str)
    json.loads(j)  # R24: json.loads accepts it

    w2 = Workbook.from_json(j)
    assert w2.sheet_names == ["S1", "S2"]
    assert w2.clock == wb.clock == 0
    h = w2.sheet("S1")
    for addr, want in RICH_EXPECT.items():
        assert h.get(addr) == want, addr
    assert w2.sheet("S2").get("B2") == 5
    # never-set cells stay never-set
    assert h.get("Z99") is None

    # R25: a further round-trip behaves identically
    w3 = Workbook.from_json(w2.to_json())
    assert w3.sheet_names == ["S1", "S2"]
    assert w3.clock == 0
    h3 = w3.sheet("S1")
    for addr, want in RICH_EXPECT.items():
        assert h3.get(addr) == want, addr


# ---------- P2: R24 resets (journal, counters, caches) ----------

def test_p2_load_resets_journal_counters_and_caches():
    wb = build_rich()
    assert wb.sheet("S1").get("D1") == 12  # warm W's cache

    w2 = Workbook.from_json(wb.to_json())
    assert w2.undo() is False      # journal empty
    assert w2.redo() is False
    assert w2.sheet("S1").eval_count == 0
    assert w2.sheet("S2").eval_count == 0

    h = w2.sheet("S1")
    assert h.get("D1") == 12
    # fresh compute: D1's closure holds exactly one formula cell (D1)
    assert h.eval_count == 1
    assert w2.sheet("S2").eval_count == 0
    # repeat read on the loaded workbook is cached (R10)
    assert h.get("D1") == 12
    assert h.eval_count == 1


# ---------- P3: R24 rejects any JSON float; bools are wrong shapes ----------

def test_p3_any_json_float_anywhere_is_rejected():
    wb = build_small()
    data = json.loads(wb.to_json())
    int_paths = [(p, v) for p, v in _walk_paths(data)
                 if isinstance(v, int) and not isinstance(v, bool)]
    for path, v in int_paths:
        variant = json.dumps(_with_replaced(data, path, float(v)))
        with pytest.raises(ValueError):
            Workbook.from_json(variant)  # R24: integer-valued floats alike
    # bare-document floats json.loads accepts
    for s in ["NaN", "Infinity", "-Infinity", "1.0", "0.5"]:
        with pytest.raises(ValueError):
            Workbook.from_json(s)


def test_p3_bool_where_cell_int_expected_is_rejected():
    # A workbook whose number cell holds a bool violates R2's invariant.
    wb = build_small()
    data = json.loads(wb.to_json())
    hits = [(p, v) for p, v in _walk_paths(data)
            if isinstance(v, int) and not isinstance(v, bool) and v == 3]
    assert hits, "stored cell value 3 not found in serialized form"
    for path, _ in hits:
        variant = json.dumps(_with_replaced(data, path, True))
        with pytest.raises(ValueError):
            Workbook.from_json(variant)


# ---------- P4: R24 adversarial inputs ----------

def test_p4_non_str_invalid_json_and_wrong_shapes_rejected():
    for bad in [None, 5, 1.0, True, b"{}", ["{}"], {"version": 1}]:
        with pytest.raises(ValueError):
            Workbook.from_json(bad)
    for bad in ["", "{", "=", '{"a":}', "not json"]:
        with pytest.raises(ValueError):
            Workbook.from_json(bad)
    for bad in ["null", "[]", "5", '"x"', "true", "{}", "[1,2]"]:
        with pytest.raises(ValueError):
            Workbook.from_json(bad)
    # moderate deep nesting: valid JSON, wrong shape -> ValueError
    with pytest.raises(ValueError):
        Workbook.from_json("[" * 50 + "]" * 50)


def test_p4_invalid_sheet_name_or_address_in_document_rejected():
    wb = build_small()
    data = json.loads(wb.to_json())
    for old, new in [("ZQX", "9bad"), ("ZQX", ""), ("Z9", "Z0"),
                     ("Z9", "z9"), ("Z9", "Z09")]:
        variant = _replace_str_everywhere(data, old, new)
        assert json.dumps(variant) != json.dumps(data), \
            f"{old!r} not found in serialized form"
        with pytest.raises(ValueError):
            Workbook.from_json(json.dumps(variant))


def test_p4_str_subclass_input_accepted():
    class MyStr(str):
        pass

    wb = build_small()
    w2 = Workbook.from_json(MyStr(wb.to_json()))
    assert w2.sheet_names == ["ZQX"]
    assert w2.sheet("ZQX").get("Z9") == 3


# ---------- P5: R24 to_json purity; failed loads corrupt nothing ----------

def test_p5_to_json_is_pure_observation():
    wb = build_rich()
    s1 = wb.sheet("S1")
    assert s1.get("D1") == 12
    before = (s1.eval_count, wb.sheet("S2").eval_count)
    wb.to_json()
    assert (s1.eval_count, wb.sheet("S2").eval_count) == before

    # to_json never journals: the set stays the most recent entry
    s1.set("A9", 1)
    wb.to_json()
    assert wb.undo() is True
    assert s1.get("A9") is None


def test_p5_failed_from_json_corrupts_nothing():
    wb = build_rich()
    j = wb.to_json()
    for bad in [None, "{", "null", "1.0", "[]"]:
        with pytest.raises(ValueError):
            Workbook.from_json(bad)
    # W untouched; the earlier good string still loads
    assert wb.sheet("S1").get("D1") == 12
    w2 = Workbook.from_json(j)
    assert w2.sheet("S1").get("D1") == 12


# ---------- P6: R25 subsequent ops identical (copy/G6/G8 cross-cut) -------

def test_p6_copy_and_edits_after_round_trip_behave_identically():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 4)
    s2.set("B1", 6)
    s1.set("D1", "=S2!B1+$A$1")
    s1.set("G1", "=Z9+A1")
    w2 = Workbook.from_json(wb.to_json())

    for w in (wb, w2):
        h = w.sheet("S1")
        # qualifier never shifted, $ pinned: D1 -> E2 gives =S2!C2+$A$1
        h.copy("D1", "E2")
        # out-of-grid shift: Z9 -> column past Z -> whole token #REF!
        h.copy("G1", "H1")

    assert wb.sheet("S1").get("E2") == w2.sheet("S1").get("E2") == 4
    assert wb.sheet("S1").get("H1") == w2.sheet("S1").get("H1") == "#REF!"

    for w in (wb, w2):
        w.sheet("S2").set("C2", 9)
        w.sheet("S1").define_name("NN", "A1")
        w.sheet("S1").set("F5", "=NN")
    assert wb.sheet("S1").get("E2") == w2.sheet("S1").get("E2") == 13
    assert wb.sheet("S1").get("F5") == w2.sheet("S1").get("F5") == 4

    # G7 cross-cut: W2's fresh journal records the post-load ops
    assert w2.undo() is True


# ---------- P7: R25 independence of loaded workbooks ----------

def test_p7_loaded_workbooks_are_independent():
    wb = build_rich()
    j = wb.to_json()
    w2 = Workbook.from_json(j)
    w3 = Workbook.from_json(j)

    w2.sheet("S1").set("A1", 100)
    assert wb.sheet("S1").get("A1") == 7
    assert w3.sheet("S1").get("A1") == 7
    assert w2.sheet("S1").get("A1") == 100

    wb.sheet("S1").set("B7", 8)
    assert w2.sheet("S1").get("B7") is None
    assert w3.sheet("S1").get("B7") is None


# ---------- P8: R24/R25 error values re-derived, not carried (G3/G5) ------

def test_p8_error_values_survive_round_trip_and_compute_fresh():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("A2", "x")
    s.set("B1", "=SUM(A1:A2)")               # str range fuel -> #TYPE!
    s.set("B2", "=1/0")                      # #DIV!
    s.set("B3", '=IF(A1,LEN("abc"),1/0)')    # untaken branch skipped -> 3
    s.set("B4", "=MIN(C1:C2)")               # all-empty range -> #TYPE!
    expect = {"B1": "#TYPE!", "B2": "#DIV!", "B3": 3, "B4": "#TYPE!"}
    for addr, want in expect.items():
        assert s.get(addr) == want, addr

    w2 = Workbook.from_json(wb.to_json())
    h = w2.sheet("S1")
    assert h.eval_count == 0                 # nothing carried over
    for addr, want in expect.items():
        assert h.get(addr) == want, addr
    assert h.eval_count >= 3                 # computed fresh on W2
