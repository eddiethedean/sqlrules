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
    """Translate ``pattern`` to SQLite ``column REGEXP pattern``.

    Case-insensitive patterns are encoded with a ``(?i)`` prefix so
    :func:`sqlrules_sqlite.register_sqlite_functions` can apply
    ``re.IGNORECASE``.
    Callers must enable REGEXP on the SQLite connection before execution.
    """
    pattern, ignore_case = pattern_text(constraint.value)
    if ignore_case and not pattern.startswith("(?i)"):
        pattern = f"(?i){pattern}"
    return cast(ColumnElement[bool], column.op("REGEXP")(pattern))
