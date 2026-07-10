from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String, Time
from sqlalchemy import cast as sa_cast
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.types import TypeEngine

from sqlrules.constraints import type_spec
from sqlrules.errors import UnsupportedConstraintError
from sqlrules.ir import CompilationContext, Constraint, TypeSpec

_UUID_LIKE = (
    "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
    "[0-9A-Fa-f][0-9A-Fa-f]-"
    "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]-"
    "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]-"
    "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]-"
    "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
    "[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
)


def _is_type(column: ColumnElement[Any], *bases: type[TypeEngine[Any]]) -> bool:
    col_type = column.type
    if isinstance(col_type, NullType):
        return False
    return isinstance(col_type, bases)


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
        _unsupported(
            field,
            spec,
            "SQL Server strict int type_check requires an Integer column.",
        )
    if _is_type(column, String):
        unsigned = column.like("[0-9]%") & ~column.like("%[^0-9]%")
        signed = column.like("[-+][0-9]%") & ~column.like("[-+]%[^0-9]%")
        return cast(ColumnElement[bool], unsigned | signed)
    if _is_type(column, Float, Numeric):
        return cast(
            ColumnElement[bool],
            column == sa_cast(sa_cast(column, Integer), Float),
        )
    _unsupported(
        field,
        spec,
        "SQL Server lax int type_check supports Integer, String, Float, or Numeric columns.",
    )
    raise AssertionError("unreachable")


def _predicate_bool(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if spec.strict:
        if _is_type(column, Boolean, Integer):
            return cast(ColumnElement[bool], column.in_((True, False, 0, 1)))
        _unsupported(
            field,
            spec,
            "SQL Server strict bool type_check requires a Boolean/Integer column.",
        )
    _unsupported(
        field,
        spec,
        "SQL Server lax bool type_check is not supported. Use strict=True.",
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
        "SQL Server str type_check requires a String/Text column.",
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
            "SQL Server strict float/Decimal type_check requires a numeric column.",
        )
    if _is_type(column, String):
        _unsupported(
            field,
            spec,
            "SQL Server lax float/Decimal type_check on String columns is not "
            "supported (no portable numeric shape check). Use a numeric column "
            "or strict=True with Float/Numeric/Integer.",
        )
    _unsupported(
        field,
        spec,
        "SQL Server float/Decimal type_check supports Float, Numeric, or Integer "
        "columns.",
    )
    raise AssertionError("unreachable")


def _predicate_temporal(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
    *,
    sa_types: tuple[type[TypeEngine[Any]], ...],
) -> ColumnElement[bool]:
    if _is_type(column, *sa_types):
        return cast(ColumnElement[bool], column.isnot(None))
    type_name = spec.python_type.__name__
    _unsupported(
        field,
        spec,
        f"SQL Server {type_name} type_check requires a typed {type_name} column "
        "(string date parsing is not emitted without a portable regex).",
    )
    raise AssertionError("unreachable")


def _predicate_uuid(
    column: ColumnElement[Any],
    spec: TypeSpec,
    field: str,
) -> ColumnElement[bool]:
    if "uuid" in type(column.type).__name__.lower():
        return cast(ColumnElement[bool], column.isnot(None))
    if spec.strict:
        _unsupported(
            field,
            spec,
            "SQL Server strict UUID type_check requires a UUID column.",
        )
    if _is_type(column, String):
        return cast(ColumnElement[bool], column.like(_UUID_LIKE))
    _unsupported(
        field,
        spec,
        "SQL Server UUID type_check supports UUID or String columns.",
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
        return _predicate_temporal(column, spec, field, sa_types=(Date,))
    if python_type is datetime:
        return _predicate_temporal(column, spec, field, sa_types=(DateTime,))
    if python_type is time:
        return _predicate_temporal(column, spec, field, sa_types=(Time,))
    if python_type is UUID:
        return _predicate_uuid(column, spec, field)
    _unsupported(
        field,
        spec,
        f"SQL Server type_check has no translator for {python_type!r}.",
    )
    raise AssertionError("unreachable")


def translate_type_check(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    """Translate ``type_check`` into SQL Server shape/type predicates."""
    del context
    spec = type_spec(constraint.value)
    predicate = _build_predicate(column, spec, constraint.field)
    return _wrap_none(column, predicate, allow_none=spec.allow_none)
