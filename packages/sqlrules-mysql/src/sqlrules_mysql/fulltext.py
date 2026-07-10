from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_fulltext_match(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``fulltext_match`` to MySQL ``MATCH (...) AGAINST (...)``.

    Applications remain responsible for having a FULLTEXT index on the
    target column(s).
    """
    return cast(ColumnElement[bool], column.match(constraint.value))
