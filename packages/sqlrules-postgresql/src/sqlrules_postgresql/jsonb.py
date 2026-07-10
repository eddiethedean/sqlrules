from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_json_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_contains`` to JSONB containment (``@>``)."""
    return cast(ColumnElement[bool], column.contains(constraint.value))


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` to JSONB ``?`` / ``has_key``."""
    return cast(ColumnElement[bool], column.has_key(constraint.value))
