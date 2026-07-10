from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import func, literal
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_json_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_contains`` to MySQL ``JSON_CONTAINS``."""
    payload = constraint.value
    if not isinstance(payload, str):
        payload = json.dumps(payload)
    return cast(ColumnElement[bool], func.json_contains(column, payload) == 1)


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` to MySQL ``JSON_CONTAINS_PATH``."""
    key = constraint.value
    path = f"$.{key}" if not str(key).startswith("$") else str(key)
    return cast(
        ColumnElement[bool],
        func.json_contains_path(column, literal("one"), path) == 1,
    )
