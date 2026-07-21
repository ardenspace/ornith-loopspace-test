"""AST node types for gridcalc formula expressions."""

from __future__ import annotations


class Node:
    """Base class for all AST nodes."""


class IntLit(Node):
    __slots__ = ("value",)

    def __init__(self, value: int) -> None:
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover
        return f"IntLit({self.value})"


class StringLit(Node):
    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover
        return f'StringLit({self.value!r})'


class Ref(Node):
    """A cell reference, possibly qualified and/or absolute."""

    __slots__ = ("col", "row", "abs_col", "abs_row", "qualifier", "_has_leading_zero")

    def __init__(
        self,
        col: str,
        row: int,
        abs_col: bool = False,
        abs_row: bool = False,
        qualifier: str | None = None,
        _has_leading_zero: bool = False,
    ) -> None:
        self.col = col
        self.row = row
        self.abs_col = abs_col
        self.abs_row = abs_row
        self.qualifier = qualifier
        self._has_leading_zero = _has_leading_zero

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Ref({self.qualifier or ''}{self.col}${self.abs_col}{self.row}"
            f"{'$' if self.abs_row else ''})"
        )


class Name(Node):
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:  # pragma: no cover
        return f"Name({self.name!r})"


class HashRef(Node):
    """The #REF! token used inside formulas."""

    def __repr__(self) -> str:  # pragma: no cover
        return "HashRef()"


class Range(Node):
    """A range REF:REF (only valid as a RANGE-ARG)."""

    __slots__ = ("start", "end")

    def __init__(self, start: Ref, end: Ref) -> None:
        self.start = start
        self.end = end

    def __repr__(self) -> str:  # pragma: no cover
        return f"Range({self.start} : {self.end})"


class UnaryMinus(Node):
    __slots__ = ("operand",)

    def __init__(self, operand: Node) -> None:
        self.operand = operand

    def __repr__(self) -> str:  # pragma: no cover
        return f"UnaryMinus({self.operand})"


class BinOp(Node):
    __slots__ = ("op", "left", "right")

    def __init__(self, op: str, left: Node, right: Node) -> None:
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self) -> str:  # pragma: no cover
        return f"BinOp({self.op}, {self.left}, {self.right})"


class FuncCall(Node):
    """A function call.

    *args* holds the parsed argument nodes.  For SUM/MIN/MAX/COUNT the
    single element is a *Range*, *Name*, or *HashRef* (a RANGE-ARG).
    For CONCAT it is one or more expression nodes.
    For LEN/IF the count is fixed.
    For NOW it is empty.
    """

    __slots__ = ("name", "args")

    def __init__(self, name: str, args: list[Node]) -> None:
        self.name = name
        self.args = args

    def __repr__(self) -> str:  # pragma: no cover
        return f"FuncCall({self.name}, {self.args})"
