from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import String, and_, case, func, literal, select, type_coerce
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


def _json_child_count(
    document: ColumnElement[Any],
    path: str,
) -> ColumnElement[Any]:
    children = func.json_each(document, path).table_valued("key").alias()
    return select(func.count()).select_from(children).scalar_subquery()


def _join_json_path(parent: str, child: str) -> str:
    return f"{parent}{child[1:]}"


def _json_value_equals(
    document: ColumnElement[Any],
    path: str,
    expected: Any,
) -> ColumnElement[bool]:
    """Compare JSON values structurally, independent of object key order."""
    json_type = func.json_type(document, path)
    extracted = func.json_extract(document, path)
    if expected is None:
        return cast(ColumnElement[bool], json_type == "null")
    if isinstance(expected, bool):
        expected_type = "true" if expected else "false"
        return cast(ColumnElement[bool], json_type == expected_type)
    if isinstance(expected, dict):
        parts: list[ColumnElement[bool]] = [
            cast(ColumnElement[bool], json_type == "object"),
            cast(ColumnElement[bool], _json_child_count(document, path) == len(expected)),
        ]
        parts.extend(
            _json_value_equals(
                document,
                _join_json_path(path, _json_path_for_key(key)),
                child,
            )
            for key, child in expected.items()
        )
        return cast(ColumnElement[bool], and_(*parts))
    if isinstance(expected, list):
        parts = [
            cast(ColumnElement[bool], json_type == "array"),
            cast(ColumnElement[bool], _json_child_count(document, path) == len(expected)),
        ]
        parts.extend(
            _json_value_equals(document, f"{path}[{index}]", child)
            for index, child in enumerate(expected)
        )
        return cast(ColumnElement[bool], and_(*parts))
    if isinstance(expected, (int, float)):
        return cast(
            ColumnElement[bool],
            json_type.in_(("integer", "real")) & (extracted == expected),
        )
    if isinstance(expected, str):
        return cast(ColumnElement[bool], (json_type == "text") & (extracted == expected))
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
            _json_value_equals(safe_json, _json_path_for_key(key), expected)
            for key, expected in value.items()
        ]
        return cast(
            ColumnElement[bool],
            valid_document & (func.json_type(safe_json) == "object") & and_(*parts),
        )

    return cast(
        ColumnElement[bool],
        valid_document & _json_value_equals(safe_json, "$", value),
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
