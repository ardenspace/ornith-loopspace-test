from gridcalc.parser import BinaryOp, Group, IntLiteral, Ref, UnaryOp, parse


def test_parse_int_keeps_source_text_for_leading_zeroes():
    assert parse("007") == IntLiteral(text="007", value=7)


def test_parse_ref_leaves_address_validity_to_evaluator():
    assert parse("A01") == Ref(name="A01")


def test_parse_unary_minus_and_binary_minus_are_distinct():
    assert parse("2--3") == BinaryOp(
        op="-",
        left=IntLiteral(text="2", value=2),
        right=UnaryOp(op="-", operand=IntLiteral(text="3", value=3)),
    )


def test_parse_binary_precedence_and_left_associativity():
    assert parse("1+2*3-4") == BinaryOp(
        op="-",
        left=BinaryOp(
            op="+",
            left=IntLiteral(text="1", value=1),
            right=BinaryOp(
                op="*",
                left=IntLiteral(text="2", value=2),
                right=IntLiteral(text="3", value=3),
            ),
        ),
        right=IntLiteral(text="4", value=4),
    )


def test_parse_parentheses_are_preserved_in_ast():
    assert parse("(1+2)*3") == BinaryOp(
        op="*",
        left=Group(
            expr=BinaryOp(
                op="+",
                left=IntLiteral(text="1", value=1),
                right=IntLiteral(text="2", value=2),
            )
        ),
        right=IntLiteral(text="3", value=3),
    )


def test_parse_all_comparisons_left_associative_with_space_and_tab():
    for op in ("=", "<>", "<", "<=", ">", ">="):
        assert parse(f"1 \t {op} \t 2 {op} 3") == BinaryOp(
            op=op,
            left=BinaryOp(
                op=op,
                left=IntLiteral(text="1", value=1),
                right=IntLiteral(text="2", value=2),
            ),
            right=IntLiteral(text="3", value=3),
        )


def test_parse_returns_marker_not_exception_for_malformed_input():
    for formula in ("", "1$2", "1 < = 2", "1 > = 2", "1 < > 2", "(1+2"):
        assert parse(formula) == "#PARSE!"


def test_parse_multi_letter_ref_rejected():
    for formula in ("AA1", "AB12", "Z99extra"):
        assert parse(formula) == "#PARSE!"


def test_parse_multi_letter_ident_rejected():
    for formula in ("AA", "SUM", "TOTAL"):
        assert parse(formula) == "#PARSE!"


def test_parse_lowercase_ref_rejected():
    assert parse("a1") == "#PARSE!"
    assert parse("z99") == "#PARSE!"


def test_parse_lowercase_function_like_rejected():
    assert parse("sum(A1:B2)") == "#PARSE!"


def test_parse_single_letter_ref_with_digits_valid():
    assert parse("A1") == Ref(name="A1")
    assert parse("Z99") == Ref(name="Z99")
    assert parse("M50") == Ref(name="M50")


def test_parse_stacked_unary_minus_is_nested():
    assert parse("--1") == UnaryOp(
        op="-",
        operand=UnaryOp(op="-", operand=IntLiteral(text="1", value=1)),
    )


def test_parse_unary_minus_binds_tighter_than_multiply():
    assert parse("-2*3") == BinaryOp(
        op="*",
        left=UnaryOp(op="-", operand=IntLiteral(text="2", value=2)),
        right=IntLiteral(text="3", value=3),
    )


def test_parse_binary_division_produces_binary_op():
    assert parse("6/2") == BinaryOp(
        op="/",
        left=IntLiteral(text="6", value=6),
        right=IntLiteral(text="2", value=2),
    )


def test_parse_division_respects_multiplication_precedence():
    assert parse("2*6/3") == BinaryOp(
        op="/",
        left=BinaryOp(
            op="*",
            left=IntLiteral(text="2", value=2),
            right=IntLiteral(text="6", value=6),
        ),
        right=IntLiteral(text="3", value=3),
    )


def test_parse_mixed_whitespace_around_all_token_classes():
    assert parse("\t( 1 \t+ 2 )\t* - 3") == BinaryOp(
        op="*",
        left=Group(
            expr=BinaryOp(
                op="+",
                left=IntLiteral(text="1", value=1),
                right=IntLiteral(text="2", value=2),
            )
        ),
        right=UnaryOp(op="-", operand=IntLiteral(text="3", value=3)),
    )


def test_parse_r12_tower_within_512_chars_parses():
    tower = "-" * 510 + "1"
    assert len(tower) == 511
    assert parse(tower) != "#PARSE!"
    assert isinstance(parse(tower), UnaryOp)


def test_parse_r12_32_deep_parens_parses():
    parens = "(" * 32 + "1" + ")" * 32
    assert len(parens) == 65
    assert parse(parens) != "#PARSE!"
    assert isinstance(parse(parens), Group)


def test_parse_r12_source_too_long_returns_parse_error():
    too_long = "1" * 513
    assert parse(too_long) == "#PARSE!"


def test_parse_r12_parens_too_deep_returns_parse_error():
    too_deep = "(" * 33 + "1" + ")" * 33
    assert parse(too_deep) == "#PARSE!"


def test_parse_r12_bounds_are_enforced_without_exceptions():
    for formula in (
        "-" * 510 + "1",
        "(" * 32 + "1" + ")" * 32,
        "1" * 513,
        "(" * 33 + "1" + ")" * 33,
    ):
        result = parse(formula)
        assert result == "#PARSE!" or isinstance(
            result, (IntLiteral, Ref, UnaryOp, BinaryOp, Group)
        )
