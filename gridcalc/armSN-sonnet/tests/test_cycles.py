from gridcalc import Sheet


def test_self_reference_is_cycle():
    s = Sheet()
    s.set("A1", "=A1")
    assert s.get("A1") == "#CYCLE!"


def test_mutual_cycle():
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    assert s.get("B1") == "#CYCLE!"


def test_cycle_through_range():
    s = Sheet()
    s.set("A1", "=SUM(A1:B1)")
    s.set("B1", 1)
    assert s.get("A1") == "#CYCLE!"


def test_count_does_not_participate_in_cycle_detection():
    s = Sheet()
    s.set("A1", "=COUNT(A1:A1)")
    assert s.get("A1") == 1


def test_off_cycle_dependent_propagates_cycle():
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    s.set("C1", "=A1+1")
    assert s.get("C1") == "#CYCLE!"


def test_breaking_cycle_with_set_recovers():
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    s.set("B1", 5)
    assert s.get("A1") == 5
