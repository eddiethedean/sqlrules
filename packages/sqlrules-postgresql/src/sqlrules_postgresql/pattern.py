from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.constraints import pattern_text
from sqlrules.ir import CompilationContext, Constraint


def translate_pattern(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``pattern`` to PostgreSQL ``~`` or case-insensitive ``~*``."""
    pattern, ignore_case = pattern_text(constraint.value)
    op = "~*" if ignore_case else "~"
    return cast(ColumnElement[bool], column.op(op)(pattern))
