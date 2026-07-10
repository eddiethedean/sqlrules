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
    """Override portable ``length`` with SQL Server ``LEN``."""
    return cast(ColumnElement[bool], func.len(column) >= constraint.value)


def translate_max_length(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Override portable ``length`` with SQL Server ``LEN``."""
    return cast(ColumnElement[bool], func.len(column) <= constraint.value)
