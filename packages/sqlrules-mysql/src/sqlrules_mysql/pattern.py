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

    MySQL's default matching follows the expression collation. Use
    ``REGEXP_LIKE``'s match type to keep SQLRules patterns case-sensitive by
    default and preserve an explicit ``re.IGNORECASE`` flag.
    """
    pattern, ignore_case = pattern_text(constraint.value)
    match_type = "i" if ignore_case else "c"
    return cast(ColumnElement[bool], func.regexp_like(column, pattern, match_type))
