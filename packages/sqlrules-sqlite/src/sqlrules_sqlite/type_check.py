from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String, Time
from sqlalchemy.sql import func
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.types import TypeEngine

from sqlrules.constraints import type_spec
from sqlrules.errors import UnsupportedConstraintError
from sqlrules.ir import CompilationContext, Constraint, TypeSpec

_INT_TEXT = r"^[+-]?(0|[1-9]\d*)$"
_FLOAT_TEXT = r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"
_DATE_TEXT = r"^\d{4}-\d{2}-\d{2}$"
_DATETIME_TEXT = r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?$"
_TIME_TEXT = r"^\d{2}:\d{2}:\d{2}(\.\d+)?$"
_UUID_TEXT = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _is_type(column: ColumnElement[Any], *bases: type[TypeEngine[Any]]) -> bool:
    col_type = column.type
    if isinstance(col_type, NullType):
        return False
    return isinstance(col_type, bases)


def _regexp(column: ColumnElement[Any], pattern: str) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column.op("REGEXP")(pattern))


def _wrap_none(
    column: ColumnElement[Any],
    predicate: ColumnElement[bool],
    *,
    allow_none: bool,
) -> ColumnElement[bool]:
    if allow_none:
        return cast(ColumnElement[bool], column.is_(None) | predicate)
    return predicate


def _unsupported(field: str, spec: TypeSpec, suggestion: str) -> None:
    raise UnsupportedConstraintError(
        field=field,
        operator="type_check",
        value=spec,
        suggestion=suggestion,
    )


def _predicate_int(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if _is_type(column, Integer):
        return cast(ColumnElement[bool], column.isnot(None))
    if spec.strict:
        # SQLite typeof can distinguish integer storage even on loosely typed columns.
        return cast(ColumnElement[bool], func.typeof(column) == "integer")
    if _is_type(column, String):
        return _regexp(column, _INT_TEXT)
    if _is_type(column, Float, Numeric):
        return cast(ColumnElement[bool], column == column.cast(Integer).cast(Float))
    # Affinity-agnostic: integer typeof OR integer-shaped text.
    return cast(
        ColumnElement[bool],
        (func.typeof(column) == "integer") | _regexp(column, _INT_TEXT),
    )


def _predicate_bool(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if spec.strict:
        if _is_type(column, Boolean, Integer):
            return cast(ColumnElement[bool], column.in_((True, False, 0, 1)))
        return cast(
            ColumnElement[bool],
            (func.typeof(column) == "integer") & column.in_((0, 1)),
        )
    _unsupported(
        field,
        spec,
        "SQLite lax bool type_check is not supported. Use strict=True.",
    )
    raise AssertionError("unreachable")


def _predicate_str(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if _is_type(column, String):
        return cast(ColumnElement[bool], column.isnot(None))
    return cast(ColumnElement[bool], func.typeof(column) == "text")


def _predicate_float(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if _is_type(column, Float, Numeric, Integer):
        return cast(ColumnElement[bool], column.isnot(None))
    if spec.strict:
        return cast(
            ColumnElement[bool],
            func.typeof(column).in_(("real", "integer")),
        )
    if _is_type(column, String):
        return _regexp(column, _FLOAT_TEXT)
    return cast(
        ColumnElement[bool],
        func.typeof(column).in_(("real", "integer")) | _regexp(column, _FLOAT_TEXT),
    )


def _predicate_temporal(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
    *,
    sa_types: tuple[type[TypeEngine[Any]], ...],
    text_pattern: str,
) -> ColumnElement[bool]:
    if _is_type(column, *sa_types):
        return cast(ColumnElement[bool], column.isnot(None))
    if spec.strict and not _is_type(column, String):
        type_name = spec.python_type.__name__
        _unsupported(
            field,
            spec,
            f"SQLite strict {type_name} type_check requires a typed or String column.",
        )
    return _regexp(column, text_pattern)


def _predicate_uuid(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if "uuid" in type(column.type).__name__.lower():
        return cast(ColumnElement[bool], column.isnot(None))
    if _is_type(column, String) or not spec.strict:
        return _regexp(column, _UUID_TEXT)
    _unsupported(
        field,
        spec,
        "SQLite strict UUID type_check requires a UUID or String column.",
    )
    raise AssertionError("unreachable")


def _build_predicate(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    python_type = spec.python_type
    if python_type is int:
        return _predicate_int(column, spec, field)
    if python_type is bool:
        return _predicate_bool(column, spec, field)
    if python_type is str:
        return _predicate_str(column, spec, field)
    if python_type in {float, Decimal}:
        return _predicate_float(column, spec, field)
    if python_type is date:
        return _predicate_temporal(column, spec, field, sa_types=(Date,), text_pattern=_DATE_TEXT)
    if python_type is datetime:
        return _predicate_temporal(
            column, spec, field, sa_types=(DateTime,), text_pattern=_DATETIME_TEXT
        )
    if python_type is time:
        return _predicate_temporal(column, spec, field, sa_types=(Time,), text_pattern=_TIME_TEXT)
    if python_type is UUID:
        return _predicate_uuid(column, spec, field)
    _unsupported(
        field,
        spec,
        f"SQLite type_check has no translator for {python_type!r}.",
    )
    raise AssertionError("unreachable")


def translate_type_check(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``type_check`` using SQLite ``typeof`` / ``REGEXP``.

    Text-shape checks use ``REGEXP``; call :func:`register_regexp` on the
    connection before executing the SQL.
    """
    del context
    spec = type_spec(constraint.value)
    predicate = _build_predicate(column, spec, constraint.field)
    return _wrap_none(column, predicate, allow_none=spec.allow_none)
