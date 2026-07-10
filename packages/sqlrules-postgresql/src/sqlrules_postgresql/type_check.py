from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String, Time
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.types import TypeEngine

from sqlrules.constraints import type_spec
from sqlrules.errors import UnsupportedConstraintError
from sqlrules.ir import CompilationContext, Constraint, TypeSpec

# Integer-like text (Pydantic lax int accepts digit strings).
_INT_TEXT = r"^[+-]?(0|[1-9]\d*)$"
# Float / Decimal-like text (simplified; not full Pydantic parity).
_FLOAT_TEXT = r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"
# ISO-ish date / datetime / time (approximate).
_DATE_TEXT = r"^\d{4}-\d{2}-\d{2}$"
_DATETIME_TEXT = r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?$"
_TIME_TEXT = r"^\d{2}:\d{2}:\d{2}(\.\d+)?$"
_UUID_TEXT = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _col_type(column: ColumnElement[Any]) -> TypeEngine[Any]:
    return column.type


def _is_type(column: ColumnElement[Any], *bases: type[TypeEngine[Any]]) -> bool:
    col_type = _col_type(column)
    if isinstance(col_type, NullType):
        return False
    return isinstance(col_type, bases)


def _regex(column: ColumnElement[Any], pattern: str) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column.op("~")(pattern))


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
        # Typed integer column: every non-null value is already an int.
        return cast(ColumnElement[bool], column.isnot(None))
    if spec.strict:
        _unsupported(
            field,
            spec,
            "PostgreSQL strict int type_check requires an Integer column "
            "(Pydantic strict mode rejects string/bool coercion).",
        )
    if _is_type(column, String):
        return _regex(column, _INT_TEXT)
    if _is_type(column, Float, Numeric):
        # Whole numbers only (approximate Pydantic float→int when no fractional part).
        return cast(ColumnElement[bool], column == column.cast(Integer).cast(Float))
    _unsupported(
        field,
        spec,
        "PostgreSQL lax int type_check supports Integer, String, Float, or Numeric columns.",
    )
    raise AssertionError("unreachable")


def _predicate_bool(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if spec.strict:
        if _is_type(column, Boolean):
            return cast(ColumnElement[bool], column.in_((True, False)))
        _unsupported(
            field,
            spec,
            "PostgreSQL strict bool type_check requires a Boolean column.",
        )
    _unsupported(
        field,
        spec,
        "PostgreSQL lax bool type_check is not supported (coercion set is not "
        "deterministically expressible). Use Field(strict=True) or model_config "
        "strict=True with a Boolean column.",
    )
    raise AssertionError("unreachable")


def _predicate_str(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if _is_type(column, String):
        return cast(ColumnElement[bool], column.isnot(None))
    _unsupported(
        field,
        spec,
        "PostgreSQL str type_check requires a String/Text column "
        "(Pydantic does not coerce other SQL types to str by default).",
    )
    raise AssertionError("unreachable")


def _predicate_float(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if _is_type(column, Float, Numeric, Integer):
        return cast(ColumnElement[bool], column.isnot(None))
    if spec.strict:
        _unsupported(
            field,
            spec,
            "PostgreSQL strict float/Decimal type_check requires a numeric column.",
        )
    if _is_type(column, String):
        return _regex(column, _FLOAT_TEXT)
    _unsupported(
        field,
        spec,
        "PostgreSQL float/Decimal type_check supports numeric or String columns.",
    )
    raise AssertionError("unreachable")


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
    if spec.strict:
        type_name = spec.python_type.__name__
        _unsupported(
            field,
            spec,
            f"PostgreSQL strict {type_name} type_check requires a typed {type_name} column.",
        )
    if _is_type(column, String):
        return _regex(column, text_pattern)
    type_name = spec.python_type.__name__
    _unsupported(
        field,
        spec,
        f"PostgreSQL {type_name} type_check supports typed {type_name} or String columns.",
    )
    raise AssertionError("unreachable")


def _predicate_uuid(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    col_type = _col_type(column)
    type_name = type(col_type).__name__.lower()
    if "uuid" in type_name:
        return cast(ColumnElement[bool], column.isnot(None))
    if spec.strict:
        _unsupported(
            field,
            spec,
            "PostgreSQL strict UUID type_check requires a UUID column.",
        )
    if _is_type(column, String):
        return _regex(column, _UUID_TEXT)
    _unsupported(
        field,
        spec,
        "PostgreSQL UUID type_check supports UUID or String columns.",
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
        f"PostgreSQL type_check has no translator for {python_type!r}.",
    )
    raise AssertionError("unreachable")


def translate_type_check(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``type_check`` into a PostgreSQL shape/type predicate."""
    del context  # dialect hint unused; plugin is already PostgreSQL-specific
    spec = type_spec(constraint.value)
    predicate = _build_predicate(column, spec, constraint.field)
    return _wrap_none(column, predicate, allow_none=spec.allow_none)
