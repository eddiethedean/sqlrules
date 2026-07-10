from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import func, literal
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def _json_path_for_key(key: Any) -> str:
    """Build a JSONPath for a single object key (never a full-path escape hatch)."""
    text = str(key)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'$."{escaped}"'


def translate_json_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_contains`` to MySQL ``JSON_CONTAINS``."""
    payload = constraint.value
    if not isinstance(payload, str):
        payload = json.dumps(payload, separators=(",", ":"))
    return cast(ColumnElement[bool], func.json_contains(column, payload) == 1)


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` to MySQL ``JSON_CONTAINS_PATH``."""
    path = _json_path_for_key(constraint.value)
    return cast(
        ColumnElement[bool],
        func.json_contains_path(column, literal("one"), path) == 1,
    )
