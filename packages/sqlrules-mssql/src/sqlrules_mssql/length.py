from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Unicode, func, literal
from sqlalchemy import cast as sa_cast
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def _char_length(column: ColumnElement[Any]) -> ColumnElement[Any]:
    """Count Unicode code points and trailing spaces on supported SQL Server.

    SQL Server ``LEN`` counts a UTF-16 surrogate pair as two under ordinary
    collations. Convert to an unbounded Unicode expression with an SC-aware
    collation before measuring; the appended character keeps trailing spaces
    in the count.
    """
    unicode_column = sa_cast(column, Unicode()).collate("Latin1_General_100_CI_AS_SC")
    sentinel = literal(".", type_=Unicode())
    return func.len(unicode_column.concat(sentinel)) - 1


def translate_min_length(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Override portable ``length`` with trailing-space-aware SQL Server length."""
    return cast(ColumnElement[bool], _char_length(column) >= constraint.value)


def translate_max_length(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Override portable ``length`` with trailing-space-aware SQL Server length."""
    return cast(ColumnElement[bool], _char_length(column) <= constraint.value)
