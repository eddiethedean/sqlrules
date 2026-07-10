from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_pattern(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``pattern`` to PostgreSQL ``column ~ pattern``."""
    return cast(ColumnElement[bool], column.op("~")(constraint.value))
