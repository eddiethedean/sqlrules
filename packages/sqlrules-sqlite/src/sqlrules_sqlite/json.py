from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import String, case, func, literal, type_coerce
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def _json_path_for_key(key: Any) -> str:
    """Build a JSONPath for a single object key (never a full-path escape hatch)."""
    text = str(key)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'$."{escaped}"'


def _compact_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _safe_json(column: ColumnElement[Any]) -> ColumnElement[Any]:
    """Replace malformed documents before any JSON1 function can inspect them."""
    return case(
        (func.json_valid(column), type_coerce(column, String)),
        else_=literal("{}"),
    )


def _extract_equals(
    column: ColumnElement[Any],
    path: str,
    expected: Any,
) -> ColumnElement[bool]:
    """Compare ``json_extract`` to ``expected`` using SQLite JSON1 affinities."""
    safe_json = _safe_json(column)
    extracted = func.json_extract(safe_json, path)
    if expected is None:
        return cast(
            ColumnElement[bool],
            func.json_type(safe_json, path) == "null",
        )
    if isinstance(expected, bool):
        json_type = "true" if expected else "false"
        return cast(ColumnElement[bool], func.json_type(safe_json, path) == json_type)
    if isinstance(expected, (dict, list)):
        compact = _compact_dumps(expected)
        return cast(
            ColumnElement[bool],
            func.json(extracted) == func.json(literal(compact)),
        )
    if isinstance(expected, (int, float)):
        return cast(
            ColumnElement[bool],
            func.json_type(safe_json, path).in_(("integer", "real")) & (extracted == expected),
        )
    if isinstance(expected, str):
        return cast(ColumnElement[bool], extracted == expected)
    compact = _compact_dumps(expected)
    return cast(
        ColumnElement[bool],
        func.json(extracted) == func.json(literal(compact)),
    )


def translate_json_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate the supported SQLite JSON containment subset safely."""
    value = constraint.value
    safe_json = _safe_json(column)
    valid_document = func.json_valid(column)
    if isinstance(value, dict):
        if not value:
            return cast(
                ColumnElement[bool],
                column.is_not(None) & valid_document & (func.json_type(safe_json) == "object"),
            )
        parts = [
            _extract_equals(column, _json_path_for_key(key), expected)
            for key, expected in value.items()
        ]
        expression = parts[0]
        for part in parts[1:]:
            expression = expression & part
        return cast(ColumnElement[bool], valid_document & expression)

    compact = _compact_dumps(value)
    return cast(
        ColumnElement[bool],
        valid_document & (func.json(safe_json) == func.json(literal(compact))),
    )


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` without evaluating JSON1 on malformed input."""
    path = _json_path_for_key(constraint.value)
    return cast(
        ColumnElement[bool],
        func.json_valid(column) & func.json_type(_safe_json(column), path).is_not(None),
    )
