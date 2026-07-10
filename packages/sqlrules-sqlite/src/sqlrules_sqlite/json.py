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
    """Translate ``json_contains`` using SQLite JSON1 ``json_extract``.

    For object payloads, checks that each top-level key extracts to the
    expected JSON value. This is a deterministic subset of JSON containment
    suitable for common filter models; nested deep-merge semantics are not
    emulated.
    """
    value = constraint.value
    if isinstance(value, dict):
        parts: list[ColumnElement[bool]] = []
        for key, expected in value.items():
            extracted = func.json_extract(column, f"$.{key}")
            parts.append(
                cast(
                    ColumnElement[bool],
                    extracted == sa_cast(literal(json.dumps(expected)), String),
                )
            )
        if not parts:
            return cast(ColumnElement[bool], literal(True))
        expression = parts[0]
        for part in parts[1:]:
            expression = expression & part
        return cast(ColumnElement[bool], expression)

    # Scalar / array payload: compare whole-document JSON text.
    return cast(
        ColumnElement[bool],
        type_coerce(column, String) == literal(json.dumps(value)),
    )


def translate_json_has_key(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``json_has_key`` via ``json_type(column, '$.key') IS NOT NULL``."""
    key = constraint.value
    path = f"$.{key}" if not str(key).startswith("$") else str(key)
    return cast(ColumnElement[bool], func.json_type(column, path).is_not(None))
