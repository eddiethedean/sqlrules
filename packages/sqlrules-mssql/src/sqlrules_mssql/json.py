from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import String, func, literal, type_coerce
from sqlalchemy import cast as sa_cast
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.ir import CompilationContext, Constraint


def translate_json_contains(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_contains`` using SQL Server JSON functions.

    Object payloads use shallow key checks via ``JSON_VALUE`` /
    ``JSON_QUERY``. Nested deep-merge containment is not emulated.
    """
    value = constraint.value
    if isinstance(value, dict):
        parts: list[ColumnElement[bool]] = []
        for key, expected in value.items():
            path = f"$.{key}"
            if isinstance(expected, (dict, list)):
                parts.append(
                    cast(
                        ColumnElement[bool],
                        func.json_query(column, path)
                        == sa_cast(literal(json.dumps(expected)), String),
                    )
                )
            else:
                expected_text = expected if isinstance(expected, str) else str(expected)
                if isinstance(expected, bool):
                    expected_text = "true" if expected else "false"
                parts.append(
                    cast(
                        ColumnElement[bool],
                        func.json_value(column, path) == literal(expected_text),
                    )
                )
        if not parts:
            return cast(ColumnElement[bool], literal(True))
        expression = parts[0]
        for part in parts[1:]:
            expression = expression & part
        return cast(ColumnElement[bool], expression)

    return cast(
        ColumnElement[bool],
        type_coerce(column, String) == literal(json.dumps(value)),
    )


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` via ``JSON_VALUE`` / ``JSON_QUERY`` IS NOT NULL."""
    key = constraint.value
    path = f"$.{key}" if not str(key).startswith("$") else str(key)
    return cast(
        ColumnElement[bool],
        func.json_value(column, path).is_not(None) | func.json_query(column, path).is_not(None),
    )
