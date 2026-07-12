"""Independent SQL oracles for behavioral tests (SPEC-driven, not implementation)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.elements import ColumnElement


def sql_literal(
    expr: object,
    *,
    dialect: Dialect | None = None,
) -> str:
    """Compile a SQLAlchemy expression with literal binds (default: SQLite)."""
    chosen = dialect if dialect is not None else sqlite.dialect()
    return str(
        expr.compile(  # type: ignore[union-attr]
            dialect=chosen,
            compile_kwargs={"literal_binds": True},
        )
    )


def pg_sql(expr: object) -> str:
    """Compile with PostgreSQL dialect + literal binds."""
    return sql_literal(expr, dialect=postgresql.dialect())


def assert_expr_equals(actual: ColumnElement[Any], expected: ColumnElement[Any]) -> None:
    """Assert two Core expressions are semantically equal via ``.compare()``."""
    assert actual.compare(expected), (
        "expression mismatch:\n"
        f"  actual:   {sql_literal(actual)}\n"
        f"  expected: {sql_literal(expected)}"
    )


def _match_one(actual_sql: str, expected: str | re.Pattern[str]) -> bool:
    if isinstance(expected, re.Pattern):
        return expected.search(actual_sql) is not None
    return actual_sql == expected


def assert_rules_sql(
    rules: Mapping[str, Sequence[ColumnElement[Any]]],
    expected: Mapping[str, Sequence[str | re.Pattern[str]]],
    *,
    dialect: Dialect | None = None,
    check_field_order: bool = True,
) -> None:
    """Assert rule dict field order and per-expression SQL against SPEC oracles.

    ``expected`` maps field names to a list of exact SQL strings or regexes,
    in extraction order. Exact strings are preferred for portable core ops.
    """
    if check_field_order:
        assert list(rules) == list(expected), (
            f"field order/keys mismatch: {list(rules)!r} != {list(expected)!r}"
        )
    else:
        assert set(rules) == set(expected), (
            f"field keys mismatch: {set(rules)!r} != {set(expected)!r}"
        )

    for field, expected_exprs in expected.items():
        actual_exprs = rules[field]
        assert len(actual_exprs) == len(expected_exprs), (
            f"{field}: expected {len(expected_exprs)} exprs, got {len(actual_exprs)} "
            f"({[sql_literal(e, dialect=dialect) for e in actual_exprs]!r})"
        )
        for i, (actual, want) in enumerate(zip(actual_exprs, expected_exprs, strict=True)):
            got = sql_literal(actual, dialect=dialect)
            assert _match_one(got, want), f"{field}[{i}]: {got!r} does not match {want!r}"


def assert_custom_op(
    expr: ColumnElement[Any],
    *,
    column_name: str,
    opstring: str,
    value: Any,
) -> None:
    """Assert a BinaryExpression uses ``column.op(opstring)(value)``."""
    assert hasattr(expr, "left") and hasattr(expr, "right") and hasattr(expr, "operator")
    left = expr.left  # type: ignore[attr-defined]
    right = expr.right  # type: ignore[attr-defined]
    operator = expr.operator  # type: ignore[attr-defined]
    assert getattr(left, "name", None) == column_name, f"column {getattr(left, 'name', left)!r}"
    assert getattr(operator, "opstring", None) == opstring, (
        f"op {getattr(operator, 'opstring', operator)!r}"
    )
    bound = getattr(right, "value", right)
    assert bound == value, f"value {bound!r} != {value!r}"
