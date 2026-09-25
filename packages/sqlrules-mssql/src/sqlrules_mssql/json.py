from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import Integer, String, Unicode, exists, func, literal, select, type_coerce
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


def _exact_text_equals(
    left: ColumnElement[Any],
    right: ColumnElement[Any],
) -> ColumnElement[bool]:
    """Compare text ordinally and distinguish trailing spaces on SQL Server."""
    left_text = sa_cast(left, Unicode()).collate("Latin1_General_100_BIN2")
    right_text = sa_cast(right, Unicode()).collate("Latin1_General_100_BIN2")
    return cast(
        ColumnElement[bool],
        (left_text == right_text) & (func.datalength(left_text) == func.datalength(right_text)),
    )


def _openjson_key_exists(
    column: ColumnElement[Any],
    key: str,
    *,
    json_type: int | None = None,
) -> ColumnElement[bool]:
    """True when OPENJSON lists ``key`` (optionally with a specific JSON type)."""
    return _openjson_key_matches(column, key, json_type=json_type)


def _openjson_key_matches(
    column: ColumnElement[Any],
    key: str,
    *,
    json_type: int | None = None,
    expected_value: str | None = None,
) -> ColumnElement[bool]:
    """True when a top-level JSON key has the requested type and value."""
    oj = (
        func.openjson(column)
        .table_valued(
            sa_column("key", String),
            sa_column("value", Unicode),
            sa_column("type", Integer),
        )
        .alias("oj")
    )
    predicate = oj.c.key == key
    if json_type is not None:
        predicate = predicate & (oj.c.type == json_type)
    if expected_value is not None:
        predicate = predicate & _exact_text_equals(
            oj.c.value,
            literal(expected_value, type_=Unicode()),
        )
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
                # OPENJSON's type code is an integer: 0 means JSON null.
                parts.append(_openjson_key_exists(column, key_text, json_type=0))
            elif isinstance(expected, (dict, list)):
                compact = _compact_dumps(expected)
                parts.append(
                    _exact_text_equals(
                        func.json_query(column, path),
                        func.json_query(sa_cast(literal(compact), String), "$"),
                    )
                )
            elif isinstance(expected, bool):
                expected_text = "true" if expected else "false"
                parts.append(
                    _openjson_key_matches(
                        column,
                        key_text,
                        json_type=3,
                        expected_value=expected_text,
                    )
                )
            elif isinstance(expected, str):
                parts.append(
                    _openjson_key_matches(
                        column,
                        key_text,
                        json_type=1,
                        expected_value=expected,
                    )
                )
            else:
                parts.append(
                    _openjson_key_matches(
                        column,
                        key_text,
                        json_type=2,
                        expected_value=str(expected),
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
