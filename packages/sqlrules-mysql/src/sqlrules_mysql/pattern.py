from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.constraints import pattern_text
from sqlrules.ir import CompilationContext, Constraint


def translate_pattern(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``pattern`` to MySQL/MariaDB ``REGEXP``.

    MySQL's default matching follows the expression collation. Preserve an
    explicit ``re.IGNORECASE`` flag with ``REGEXP_LIKE``'s match type.
    """
    pattern, ignore_case = pattern_text(constraint.value)
    if ignore_case:
        return cast(ColumnElement[bool], func.regexp_like(column, pattern, "i"))
    return cast(ColumnElement[bool], column.op("REGEXP")(pattern))
