from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import Integer, String, Unicode, and_, exists, func, literal, select, type_coerce
from sqlalchemy import cast as sa_cast
from sqlalchemy import column as sa_column
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.errors import CapabilityError
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
    predicate = _exact_text_equals(
        oj.c.key,
        literal(key, type_=Unicode()),
    )
    if json_type is not None:
        predicate = predicate & (oj.c.type == json_type)
    if expected_value is not None:
        predicate = predicate & _exact_text_equals(
            oj.c.value,
            literal(expected_value, type_=Unicode()),
        )
    return cast(ColumnElement[bool], exists(select(1).select_from(oj).where(predicate)))


def _openjson_child_count(document: ColumnElement[Any]) -> ColumnElement[Any]:
    children = func.openjson(document).table_valued(sa_column("key", String)).alias("children")
    return select(func.count()).select_from(children).scalar_subquery()


def _openjson_object_equals(
    document: ColumnElement[Any],
    expected: dict[Any, Any],
    field: str,
) -> ColumnElement[bool]:
    parts: list[ColumnElement[bool]] = [
        cast(ColumnElement[bool], _openjson_child_count(document) == len(expected))
    ]
    parts.extend(
        _openjson_value_equals(document, str(key), value, field) for key, value in expected.items()
    )
    return cast(ColumnElement[bool], and_(*parts))


def _openjson_array_equals(
    document: ColumnElement[Any],
    expected: list[Any],
    field: str,
) -> ColumnElement[bool]:
    parts: list[ColumnElement[bool]] = [
        cast(ColumnElement[bool], _openjson_child_count(document) == len(expected))
    ]
    parts.extend(
        _openjson_value_equals(document, str(index), value, field)
        for index, value in enumerate(expected)
    )
    return cast(ColumnElement[bool], and_(*parts))


def _openjson_value_equals(
    document: ColumnElement[Any],
    key: str,
    expected: Any,
    field: str,
) -> ColumnElement[bool]:
    if expected is None:
        return _openjson_key_exists(document, key, json_type=0)
    if isinstance(expected, bool):
        return _openjson_key_matches(
            document,
            key,
            json_type=3,
            expected_value="true" if expected else "false",
        )
    if isinstance(expected, str):
        return _openjson_key_matches(
            document,
            key,
            json_type=1,
            expected_value=expected,
        )
    if isinstance(expected, dict):
        nested = func.json_query(document, _json_path_for_key(key))
        return cast(
            ColumnElement[bool],
            _openjson_key_exists(document, key, json_type=5)
            & _openjson_object_equals(nested, expected, field),
        )
    if isinstance(expected, list):
        nested = func.json_query(document, _json_path_for_key(key))
        return cast(
            ColumnElement[bool],
            _openjson_key_exists(document, key, json_type=4)
            & _openjson_array_equals(nested, expected, field),
        )
    if isinstance(expected, (int, float)):
        raise CapabilityError(
            "mssql",
            field,
            "exact JSON numeric equality",
            "OPENJSON.value text",
            "SQL Server exposes JSON numbers as text, and the provider cannot "
            "guarantee exact numeric equivalence without lossy conversion.",
        )
    raise CapabilityError(
        "mssql",
        field,
        "JSON scalar equality",
        type(expected).__name__,
        "Only null, boolean, string, object, and array values are supported by "
        "the SQL Server JSON containment translator.",
    )


def _is_json_object(document: ColumnElement[Any]) -> ColumnElement[bool]:
    """Check the root shape using functions available since SQL Server 2016."""
    text: ColumnElement[Any] = sa_cast(document, Unicode())
    # LTRIM on supported SQL Server versions removes spaces only. Normalize
    # the other JSON whitespace characters first so valid pretty-printed
    # documents receive the same root-shape check.
    for whitespace in ("\t", "\n", "\r"):
        text = cast(
            ColumnElement[Any],
            func.replace(
                text,
                literal(whitespace, type_=Unicode()),
                literal(" ", type_=Unicode()),
            ),
        )
    return cast(
        ColumnElement[bool],
        (func.isjson(document) == 1)
        & (func.left(func.ltrim(text), 1) == literal("{", type_=Unicode())),
    )


def translate_json_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_contains`` using SQL Server JSON functions.

    Object payloads contain their requested top-level keys. Nested objects and
    arrays are matched exactly by structure, independent of whitespace and
    object key order. Numeric comparisons are rejected because ``OPENJSON``
    exposes numbers as text and SQL Server cannot guarantee exact equality
    without a potentially lossy conversion.
    """
    value = constraint.value
    if isinstance(value, dict):
        if not value:
            return _is_json_object(column)
        parts: list[ColumnElement[bool]] = []
        for key, expected in value.items():
            parts.append(_openjson_value_equals(column, str(key), expected, constraint.field))
        expression = parts[0]
        for part in parts[1:]:
            expression = expression & part
        return cast(ColumnElement[bool], _is_json_object(column) & expression)

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
    return cast(
        ColumnElement[bool],
        _is_json_object(column) & _openjson_key_exists(column, str(constraint.value)),
    )
