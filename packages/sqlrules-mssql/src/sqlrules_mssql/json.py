from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import String, exists, func, literal, select, type_coerce
from sqlalchemy import cast as sa_cast
from sqlalchemy import column as sa_column
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def _json_path_for_key(key: Any) -> str:
    """Build a JSONPath for a single object key (never a full-path escape hatch)."""
    text = str(key)
    # SQL Server JSON path quotes use doubled double-quotes inside the name.
    escaped = text.replace('"', '""')
    return f'$."{escaped}"'


def _compact_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _openjson_key_exists(
    column: ColumnElement[Any],
    key: str,
    *,
    json_type: str | None = None,
) -> ColumnElement[bool]:
    """True when OPENJSON lists ``key`` (optionally with a specific JSON type)."""
    oj = (
        func.openjson(column)
        .table_valued(
            sa_column("key", String),
            sa_column("value", String),
            sa_column("type", String),
        )
        .render_derived(name="oj", with_types=True)
        .alias("oj")
    )
    predicate = oj.c.key == key
    if json_type is not None:
        predicate = predicate & (oj.c.type == json_type)
    return cast(ColumnElement[bool], exists(select(1).select_from(oj).where(predicate)))


def translate_json_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_contains`` using SQL Server JSON functions.

    Object payloads use shallow key checks via ``JSON_VALUE`` /
    ``JSON_QUERY`` / ``OPENJSON``. Nested deep-merge containment is not
    emulated.
    """
    value = constraint.value
    if isinstance(value, dict):
        if not value:
            # Align with PostgreSQL ``@> '{}'``: require a non-NULL JSON object.
            return cast(
                ColumnElement[bool],
                column.is_not(None)
                & (func.isjson(column) == 1)
                & func.json_query(column, "$").is_not(None),
            )
        parts: list[ColumnElement[bool]] = []
        for key, expected in value.items():
            path = _json_path_for_key(key)
            key_text = str(key)
            if expected is None:
                parts.append(_openjson_key_exists(column, key_text, json_type="null"))
            elif isinstance(expected, (dict, list)):
                compact = _compact_dumps(expected)
                parts.append(
                    cast(
                        ColumnElement[bool],
                        func.json_query(column, path)
                        == func.json_query(sa_cast(literal(compact), String), "$"),
                    )
                )
            elif isinstance(expected, bool):
                expected_text = "true" if expected else "false"
                parts.append(
                    cast(
                        ColumnElement[bool],
                        func.json_value(column, path) == literal(expected_text),
                    )
                )
            elif isinstance(expected, str):
                parts.append(
                    cast(
                        ColumnElement[bool],
                        func.json_value(column, path) == literal(expected),
                    )
                )
            else:
                parts.append(
                    cast(
                        ColumnElement[bool],
                        func.json_value(column, path) == literal(str(expected)),
                    )
                )
        expression = parts[0]
        for part in parts[1:]:
            expression = expression & part
        return cast(ColumnElement[bool], expression)

    compact = _compact_dumps(value)
    return cast(
        ColumnElement[bool],
        type_coerce(column, String) == func.json_query(sa_cast(literal(compact), String), "$"),
    )


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` via ``OPENJSON`` key presence (includes JSON null)."""
    return _openjson_key_exists(column, str(constraint.value))
