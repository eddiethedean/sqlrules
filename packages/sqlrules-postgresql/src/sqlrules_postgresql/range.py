from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_range_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``range_contains`` to PostgreSQL range containment (``@>``)."""
    return cast(ColumnElement[bool], column.op("@>")(constraint.value))


def translate_range_overlap(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``range_overlap`` to PostgreSQL range overlap (``&&``)."""
    return cast(ColumnElement[bool], column.op("&&")(constraint.value))
