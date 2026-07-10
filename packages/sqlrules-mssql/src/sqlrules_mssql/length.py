from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func, literal
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def _char_length(column: ColumnElement[Any]) -> ColumnElement[Any]:
    """Character length including trailing spaces (``LEN`` alone strips them)."""
    return func.len(column.concat(literal("."))) - 1


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
