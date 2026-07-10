from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import String, func, literal, type_coerce
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def _json_path_for_key(key: Any) -> str:
    """Build a JSONPath for a single object key (never a full-path escape hatch)."""
    text = str(key)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'$."{escaped}"'


def _compact_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _extract_equals(
    column: ColumnElement[Any],
    path: str,
    expected: Any,
) -> ColumnElement[bool]:
    """Compare ``json_extract`` to ``expected`` using SQLite JSON1 affinities."""
    extracted = func.json_extract(column, path)
    if expected is None:
        return cast(ColumnElement[bool], func.json_type(column, path) == "null")
    if isinstance(expected, bool):
        return cast(ColumnElement[bool], extracted == (1 if expected else 0))
    if isinstance(expected, (dict, list)):
        compact = _compact_dumps(expected)
        return cast(
            ColumnElement[bool],
            func.json(extracted) == func.json(literal(compact)),
        )
    if isinstance(expected, (int, float)):
        return cast(ColumnElement[bool], extracted == expected)
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
    """Translate ``json_contains`` using SQLite JSON1 ``json_extract``.

    For object payloads, checks that each top-level key extracts to the
    expected JSON value. This is a deterministic subset of JSON containment
    suitable for common filter models; nested deep-merge semantics are not
    emulated.
    """
    value = constraint.value
    if isinstance(value, dict):
        if not value:
            # Align with PostgreSQL ``@> '{}'``: require a non-NULL JSON object.
            return cast(
                ColumnElement[bool],
                column.is_not(None) & (func.json_type(column) == "object"),
            )
        parts: list[ColumnElement[bool]] = []
        for key, expected in value.items():
            parts.append(_extract_equals(column, _json_path_for_key(key), expected))
        expression = parts[0]
        for part in parts[1:]:
            expression = expression & part
        return cast(ColumnElement[bool], expression)

    # Scalar / array payload: compare whole-document JSON text via json().
    compact = _compact_dumps(value)
    return cast(
        ColumnElement[bool],
        func.json(type_coerce(column, String)) == func.json(literal(compact)),
    )


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` via ``json_type(column, path) IS NOT NULL``."""
    path = _json_path_for_key(constraint.value)
    return cast(ColumnElement[bool], func.json_type(column, path).is_not(None))
