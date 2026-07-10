from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_array_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``array_contains`` to PostgreSQL array containment."""
    return cast(ColumnElement[bool], column.contains(constraint.value))


def translate_array_overlap(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``array_overlap`` to PostgreSQL array overlap (``&&``)."""
    return cast(ColumnElement[bool], column.overlap(constraint.value))
