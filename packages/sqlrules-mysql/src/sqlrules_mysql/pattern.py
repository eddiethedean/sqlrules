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
    """Translate ``pattern`` to MySQL/MariaDB ``REGEXP``.

    MySQL ``REGEXP`` is case-insensitive for non-binary collations. SQLRules
    follows that dialect behavior rather than inventing ``REGEXP BINARY``.
    """
    pattern, _ignore_case = pattern_text(constraint.value)
    return cast(ColumnElement[bool], column.op("REGEXP")(pattern))
