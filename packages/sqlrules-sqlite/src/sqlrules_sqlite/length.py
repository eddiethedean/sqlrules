from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_min_length(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Use the registered Python-compatible code-point counter."""
    return cast(
        ColumnElement[bool],
        func.sqlrules_char_length(column) >= constraint.value,
    )


def translate_max_length(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Use the registered Python-compatible code-point counter."""
    return cast(
        ColumnElement[bool],
        func.sqlrules_char_length(column) <= constraint.value,
    )


__all__ = ["translate_max_length", "translate_min_length"]
