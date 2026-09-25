from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Numeric,
    String,
    Time,
    and_,
    case,
    false,
    func,
    null,
)
from sqlalchemy import cast as sa_cast
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.types import TypeEngine

from sqlrules.errors import CapabilityError
from sqlrules.ir import CompilationContext, PreparedValue, RuleField


def _source_kind(column: ColumnElement[Any]) -> str | None:
    column_type = column.type
    if isinstance(column_type, NullType):
        return None
    if isinstance(column_type, Boolean):
        return "bool"
    if isinstance(column_type, BigInteger):
        return "int"
    if isinstance(column_type, TypeEngine) and type(column_type).__name__.lower() in {
        "integer",
        "smallinteger",
        "tinyint",
    }:
        return "int"
    if isinstance(column_type, Float):
        return "float"
    if isinstance(column_type, Numeric):
        return "decimal"
    if isinstance(column_type, String):
        return "str"
    if isinstance(column_type, DateTime):
        return "datetime"
    if isinstance(column_type, Date):
        return "date"
    if isinstance(column_type, Time):
        return "time"
    type_name = type(column_type).__name__.lower()
    if "uuid" in type_name or "uniqueidentifier" in type_name:
        return "uuid"
    if "json" in type(column_type).__name__.lower():
        return "json"
    if "array" in type(column_type).__name__.lower():
        return "array"
    if "range" in type(column_type).__name__.lower():
        return "range"
    return None


def _target_kind(python_type: Any) -> str:
    if python_type is bool:
        return "bool"
    if python_type is int:
        return "int"
    if python_type is float:
        return "float"
    if python_type is Decimal:
        return "decimal"
    if python_type is str:
        return "str"
    if python_type is date:
        return "date"
    if python_type is datetime:
        return "datetime"
    if python_type is time:
        return "time"
    if python_type is UUID:
        return "uuid"
    if python_type is list:
        return "array"
    if python_type is dict:
        return "json"
    return getattr(python_type, "__name__", str(python_type)).lower()


def _target_sql_type(kind: str) -> TypeEngine[Any]:
    types: dict[str, TypeEngine[Any]] = {
        "bool": Boolean(),
        "int": BigInteger(),
        "float": Float(),
        "decimal": Numeric(),
        "str": String(),
        "date": Date(),
        "datetime": DateTime(),
        "time": Time(),
        "uuid": String(36),
    }
    return types[kind]


def _total(predicate: ColumnElement[Any]) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], func.coalesce(predicate, false()))


def _known_mismatch(
    column: ColumnElement[Any],
    field: RuleField,
    source_kind: str,
    target_kind: str,
) -> PreparedValue:
    target_sql_type = _target_sql_type(target_kind)
    value = cast(ColumnElement[Any], sa_cast(null(), target_sql_type))
    return PreparedValue(
        source=column,
        value=value,
        valid=cast(ColumnElement[bool], false()),
        is_null=cast(ColumnElement[bool], column.is_(None)),
        logical_type=target_kind,
        coercion=f"strict-mismatch:{source_kind}-to-{target_kind}",
        capability="known-type-mismatch",
    )


def _text_pattern(kind: str) -> str:
    if kind == "int":
        # SQLRules 2.0 profile accepts whitespace, signs, and zero padding.
        return r"^\s*[+-]?[0-9]+\s*$"
    if kind in {"float", "decimal"}:
        return r"^\s*[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?\s*$"
    raise KeyError(kind)


def _validate_string_domain_collation(
    column: ColumnElement[Any],
    field: RuleField,
    *,
    backend: str,
    source: str,
) -> None:
    if field.python_type is not str or not any(
        constraint.operator in {"literal", "enum"} for constraint in field.constraints
    ):
        return
    collation = getattr(column.type, "collation", None)
    if backend == "postgresql" and collation not in {"C", "POSIX"}:
        reason = "string domain membership requires an explicit deterministic C or POSIX collation."
    elif backend == "sqlite" and collation not in {None, "BINARY"}:
        reason = "string domain membership requires SQLite's BINARY collation."
    elif (
        backend == "mysql"
        and not (
            isinstance(collation, str)
            and (collation.lower().endswith("_bin") or "_cs" in collation.lower())
        )
        or backend == "mssql"
        and not (
            isinstance(collation, str)
            and ("_bin" in collation.lower() or "_cs" in collation.lower())
        )
    ):
        reason = (
            "string domain membership requires an explicit case-sensitive or binary "
            "column collation."
        )
    else:
        return
    raise CapabilityError(backend, field.name, "str", source, reason)


def prepare_scalar(
    column: ColumnElement[Any],
    field: RuleField,
    context: CompilationContext,
    *,
    backend: str,
) -> PreparedValue:
    """Prepare a known typed source for scalar rules, using only safe casts.

    The initial 2.0 conversion profile supports native typed values everywhere,
    integer-to-float and integral-float-to-integer conversion, and guarded text
    to integer/float/Decimal conversion where the backend provides a safe
    validity primitive. Other recognized type pairs are known mismatches in
    strict mode and explicit capability errors in lax mode.
    """
    target = _target_kind(field.python_type)
    source = _source_kind(column)
    if type(column.type).__name__ == "Uuid" and backend == "mysql":
        # SQLAlchemy's generic Uuid is emulated as text on MySQL; the
        # annotation alone cannot prove that the stored value is a UUID.
        source = "str"

    if any(item.operator in {"range_contains", "range_overlap"} for item in field.constraints):
        if source != "range":
            raise CapabilityError(
                backend,
                field.name,
                "range",
                source or type(column.type).__name__,
                "RangeContains and RangeOverlap require a database range column.",
            )
        return PreparedValue(
            source=column,
            value=column,
            valid=true_expression(),
            is_null=cast(ColumnElement[bool], column.is_(None)),
            logical_type="range",
            capability="native-range",
        )

    if target in {"array", "json", "range"}:
        supported = source == target or (target == "json" and source == "json")
        if not supported:
            raise CapabilityError(
                backend,
                field.name,
                target,
                source or type(column.type).__name__,
                "the bound column does not expose the container or range type "
                "required by its marker.",
            )
        return PreparedValue(
            source=column,
            value=column,
            valid=true_expression(),
            is_null=cast(ColumnElement[bool], column.is_(None)),
            logical_type=target,
            capability="native-container",
        )

    if source is None:
        raise CapabilityError(
            backend,
            field.name,
            target,
            type(column.type).__name__,
            "source type evidence is unavailable; provide a typed column or "
            "wait for an explicit storage mapping.",
        )

    valid: ColumnElement[Any]
    converted: ColumnElement[Any]

    _validate_string_domain_collation(
        column,
        field,
        backend=backend,
        source=source,
    )

    compatible = source == target
    if target == "float" and source in {"int", "decimal"} and not field.strict:
        max_float = Decimal("1.7976931348623157e308")
        in_float_range = and_(column >= -max_float, column <= max_float)
        converted = case(
            (in_float_range, sa_cast(column, Float())),
            else_=sa_cast(null(), Float()),
        )
        return PreparedValue(
            source=column,
            value=converted,
            valid=_total(in_float_range),
            is_null=cast(ColumnElement[bool], column.is_(None)),
            logical_type=target,
            coercion=f"{source}-to-float",
            capability="bounded-numeric-to-float",
        )
    if target == "decimal" and source == "int" and not field.strict:
        converted = sa_cast(column, Numeric())
        return PreparedValue(
            source=column,
            value=converted,
            valid=true_expression(),
            is_null=cast(ColumnElement[bool], column.is_(None)),
            logical_type=target,
            coercion="int-to-decimal",
            capability="exact-integer-to-decimal",
        )
    if target == "int" and source in {"float", "decimal"} and not field.strict:
        in_range = and_(column >= -(2**63), column <= (2**63) - 1)
        value: ColumnElement[Any]
        if backend == "mssql":
            from sqlalchemy.dialects.mssql import try_cast

            value = try_cast(column, BigInteger())
        else:
            value = case(
                (in_range, sa_cast(column, BigInteger())),
                else_=sa_cast(null(), BigInteger()),
            )
        valid = and_(in_range, column == value)
        return PreparedValue(
            source=column,
            value=value,
            valid=_total(valid),
            is_null=cast(ColumnElement[bool], column.is_(None)),
            logical_type=target,
            coercion="integral-numeric-to-int64",
            capability="exact-integral-conversion",
        )
    if compatible:
        valid = true_expression()
        if target == "int" and backend == "mysql" and getattr(column.type, "unsigned", False):
            valid = and_(column >= 0, column <= (2**63) - 1)
        if target == "bool" and backend in {"mysql", "mssql"}:
            valid = column.in_((0, 1))
        return PreparedValue(
            source=column,
            value=column,
            valid=_total(valid),
            is_null=cast(ColumnElement[bool], column.is_(None)),
            logical_type=target,
            coercion="bounded-unsigned-int64"
            if target == "int" and backend == "mysql" and getattr(column.type, "unsigned", False)
            else "identity",
            capability="native",
        )

    if field.strict:
        return _known_mismatch(column, field, source, target)

    if source == "str" and target in {"int", "float", "decimal"}:
        if (backend in {"mysql", "mssql"} and target == "decimal") or (
            backend == "mysql" and target == "float"
        ):
            raise CapabilityError(
                backend,
                field.name,
                target,
                source,
                "the configured server cannot prove the full precision and "
                "range required by this text conversion.",
            )
        if backend == "postgresql":
            version = context.server_version
            if version is None or version < (16, 0):
                raise CapabilityError(
                    backend,
                    field.name,
                    target,
                    source,
                    "safe text conversion requires PostgreSQL 16+ and its "
                    "pg_input_is_valid primitive; pass server_version explicitly.",
                )
            target_name = {"int": "bigint", "float": "double precision", "decimal": "numeric"}[
                target
            ]
            valid = and_(
                func.pg_input_is_valid(column, target_name),
                column.op("~")(_text_pattern(target)),
            )
            converted = sa_cast(column, _target_sql_type(target))
        elif backend == "mysql":
            if context.server_version is None or context.server_version < (8, 0):
                raise CapabilityError(
                    backend,
                    field.name,
                    target,
                    source,
                    "safe text conversion requires MySQL 8.0+; pass server_version explicitly.",
                )
            pattern = column.op("REGEXP")(_text_pattern(target))
            valid = pattern
            if target == "int":
                digits = func.length(
                    func.replace(func.replace(func.trim(column), "+", ""), "-", "")
                )
                valid = and_(valid, digits <= 18)
            converted = sa_cast(column, _target_sql_type(target))
        elif backend == "sqlite":
            valid = column.op("REGEXP")(_text_pattern(target))
            if target == "int":
                # Restrict to at most 18 significant digits so SQLite's signed
                # 64-bit CAST cannot saturate; this conservative range is in
                # the published 2.0 semantic profile.
                digits = func.length(
                    func.replace(func.replace(func.trim(column), "+", ""), "-", "")
                )
                valid = and_(valid, digits <= 18)
            converted = sa_cast(column, _target_sql_type(target))
        elif backend == "mssql":
            if context.server_version is None or context.server_version < (11, 0):
                raise CapabilityError(
                    backend,
                    field.name,
                    target,
                    source,
                    "safe text conversion requires SQL Server 2012 or newer; "
                    "pass server_version explicitly.",
                )
            from sqlalchemy.dialects.mssql import try_cast

            converted = try_cast(column, _target_sql_type(target))
            valid = converted.isnot(None)
            trimmed = func.ltrim(func.rtrim(column))
            if target == "int":
                first = func.substring(trimmed, 1, 1)
                integer_digits = case(
                    (first.in_(("+", "-")), func.substring(trimmed, 2, 8000)),
                    else_=trimmed,
                )
                valid = and_(
                    valid,
                    integer_digits != "",
                    integer_digits.not_like("%[^0-9]%"),
                )
            elif target in {"float", "decimal"}:
                valid = and_(valid, trimmed.not_like("%[^0-9eE+.-]%"))
        else:
            raise CapabilityError(
                backend,
                field.name,
                target,
                source,
                "no safe text conversion adapter is registered.",
            )

        converted_expr = case(
            (valid, converted),
            else_=sa_cast(null(), _target_sql_type(target)),
        )
        return PreparedValue(
            source=column,
            value=converted_expr,
            valid=_total(valid),
            is_null=cast(ColumnElement[bool], column.is_(None)),
            logical_type=target,
            coercion=f"text-to-{target}",
            capability="guarded-text-conversion",
        )

    raise CapabilityError(
        backend,
        field.name,
        target,
        source,
        "the conversion is outside the frozen SQLRules 2.0 lax profile for this backend.",
    )


def true_expression() -> ColumnElement[bool]:
    from sqlalchemy import true

    return cast(ColumnElement[bool], true())


def prepare_sqlite_scalar(
    column: ColumnElement[Any],
    field: RuleField,
    context: CompilationContext,
) -> PreparedValue:
    """Use SQLite runtime storage tags instead of SQLAlchemy type affinity."""
    target = _target_kind(field.python_type)
    source_kind = _source_kind(column)
    _validate_string_domain_collation(
        column,
        field,
        backend="sqlite",
        source=source_kind or "dynamic",
    )
    runtime = func.typeof(column)
    is_null = cast(ColumnElement[bool], column.is_(None))
    if target in {"date", "datetime", "time", "uuid"}:
        raise CapabilityError(
            "sqlite",
            field.name,
            target,
            source_kind or type(column.type).__name__,
            "SQLite stores this Python type using an emulated representation; "
            "2.0 requires an explicit storage adapter to prove its logical type.",
        )
    if target in {"array", "json", "range"}:
        return prepare_scalar(column, field, context, backend="sqlite")

    valid: ColumnElement[Any]
    value: ColumnElement[Any] = column
    coercion = "runtime-type-match"
    capability = "sqlite-runtime-storage-class"

    if target == "bool":
        if field.strict:
            raise CapabilityError(
                "sqlite",
                field.name,
                target,
                source_kind or "dynamic",
                "SQLite has no native boolean storage class; strict bool "
                "requires an explicit storage mapping.",
            )
        valid = and_(runtime == "integer", column.in_((0, 1)))
        value = case((column == 1, true_expression()), else_=false())
    elif target == "int":
        integer = runtime == "integer"
        integral_real = and_(runtime == "real", column == sa_cast(column, BigInteger()))
        if field.strict:
            valid = integer
        else:
            text_integer = and_(runtime == "text", column.op("REGEXP")(_text_pattern("int")))
            digits = func.length(func.replace(func.replace(func.trim(column), "+", ""), "-", ""))
            valid = or_expression(
                integer,
                and_(integral_real, column >= -(2**63), column <= (2**63) - 1),
                and_(text_integer, digits <= 18),
            )
            value = case(
                (integer, column),
                (integral_real, sa_cast(column, BigInteger())),
                (text_integer, sa_cast(column, BigInteger())),
                else_=sa_cast(null(), BigInteger()),
            )
            coercion = "sqlite-int64"
    elif target == "float":
        if field.strict:
            valid = runtime == "real"
        else:
            text_float = and_(runtime == "text", column.op("REGEXP")(_text_pattern("float")))
            valid = or_expression(runtime == "real", runtime == "integer", text_float)
            value = case(
                (text_float, sa_cast(column, Float())),
                else_=sa_cast(column, Float()),
            )
            coercion = "sqlite-numeric-to-float"
    elif target == "decimal":
        raise CapabilityError(
            "sqlite",
            field.name,
            target,
            source_kind or "dynamic",
            "SQLite's integer/real storage classes cannot prove exact Decimal precision; "
            "an explicit storage adapter is required.",
        )
    elif target == "str":
        valid = runtime == "text"
    else:
        raise CapabilityError(
            "sqlite",
            field.name,
            target,
            source_kind or "dynamic",
            "no scalar adapter is registered.",
        )

    return PreparedValue(
        source=column,
        value=value,
        valid=_total(valid),
        is_null=is_null,
        logical_type=target,
        coercion=coercion,
        capability=capability,
    )


def or_expression(*items: ColumnElement[Any]) -> ColumnElement[bool]:
    from sqlalchemy import or_

    return or_(*items)


__all__ = ["prepare_scalar", "prepare_sqlite_scalar"]
