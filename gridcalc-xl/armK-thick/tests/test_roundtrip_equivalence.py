from gridcalc import Workbook


ALL_ADDRS = tuple(f"{chr(col)}{row}" for col in range(ord("A"), ord("Z") + 1) for row in range(1, 100))


def _semantic_snapshot(wb):
    return (
        tuple(wb.sheet_names),
        wb.clock,
        tuple(
            (sheet_name, addr, wb.sheet(sheet_name).get(addr))
            for sheet_name in wb.sheet_names
            for addr in ALL_ADDRS
        ),
    )


def _assert_roundtrip_equivalent(wb):
    loaded = Workbook.from_json(wb.to_json())
    assert _semantic_snapshot(loaded) == _semantic_snapshot(wb)
    assert _semantic_snapshot(Workbook.from_json(loaded.to_json())) == _semantic_snapshot(loaded)
    return loaded


def _seed_workbook():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s3 = wb.add_sheet("S3")
    s1.set("A1", 7)
    s1.set("B1", "=$A$1 + S2!A1")
    s1.set("C1", "=SUM(S2!A1:B2)+AA")
    s1.define_name("AA", "S3!A1:A2")
    s2.set("A1", 3)
    s2.set("B2", "=S1!A1+1")
    s3.set("A1", 2)
    s3.set("A2", "text")
    wb.advance_clock()
    return wb


def test_round_trip_preserves_sheet_names_clock_and_full_grid_values():
    wb = _seed_workbook()

    _assert_roundtrip_equivalent(wb)


def test_subsequent_successful_non_undo_redo_api_sequences_remain_equivalent():
    original = _seed_workbook()
    loaded = _assert_roundtrip_equivalent(original)

    operations = (
        lambda wb: wb.sheet("S1").set("D1", "=S2!B2+S3!A1"),
        lambda wb: wb.sheet("S2").copy("S1!B1", "C3"),
        lambda wb: wb.sheet("S3").define_name("BB", "S1!A1:D1"),
        lambda wb: wb.advance_clock(),
        lambda wb: wb.add_sheet("S4"),
        lambda wb: wb.sheet("S4").set("A1", "=S1!D1+SUM(S3!BB)"),
    )
    for op in operations:
        original_result = op(original)
        loaded_result = op(loaded)
        if isinstance(original_result, (type(None), bool, int, str)):
            assert loaded_result == original_result
        assert _semantic_snapshot(loaded) == _semantic_snapshot(original)
        assert _semantic_snapshot(Workbook.from_json(loaded.to_json())) == _semantic_snapshot(loaded)


def test_copy_after_round_trip_rewrites_restored_formula_text_identically():
    before = Workbook()
    before_s1 = before.add_sheet("S1")
    before.add_sheet("S2")
    before_s1.set("A1", 5)
    before_s1.set("B2", "=$A1 + A$1 + S2!A1 + SUM(A1:B2)")

    after = _assert_roundtrip_equivalent(before)

    before.sheet("S1").copy("B2", "C3")
    after.sheet("S1").copy("B2", "C3")

    assert after.sheet("S1")._cells["C3"] == before.sheet("S1")._cells["C3"]
    assert _semantic_snapshot(after) == _semantic_snapshot(before)
