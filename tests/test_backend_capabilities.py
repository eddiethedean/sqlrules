from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import Field
from sqlalchemy import Column, Date, Float, Integer, MetaData, Numeric, String, Table
from sqlalchemy.dialects.mssql import dialect as mssql_dialect
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect
from sqlalchemy.sql.sqltypes import NullType
from sqlrules_mssql import MssqlPlugin
from sqlrules_mysql import MysqlPlugin
from sqlrules_postgresql import PostgresPlugin
from sqlrules_sqlite import SQLitePlugin

from sqlrules import CapabilityError, Compiler, RuleSchema


def test_sqlite_boolean_uses_runtime_integer_values_and_rejects_other_storage() -> None:
    class BooleanRules(RuleSchema):
        value: bool

    table = Table("items", MetaData(), Column("value", Integer))
    compiled = Compiler(plugins=[SQLitePlugin()]).compile(BooleanRules, table)
    assert compiled.fields[0].logical_type == "bool"
    assert compiled.fields[0].capability == "sqlite-runtime-storage-class"

    text_table = Table("text_items", MetaData(), Column("value", String))
    text_compiled = Compiler(plugins=[SQLitePlugin()]).compile(BooleanRules, text_table)
    assert text_compiled.fields[0].capability == "sqlite-runtime-storage-class"


def test_unknown_and_emulated_sqlite_types_raise_stable_capability_errors() -> None:
    class IntegerRules(RuleSchema):
        value: int

    untyped = Table("untyped", MetaData(), Column("value", NullType()))
    with pytest.raises(CapabilityError, match="source type evidence is unavailable"):
        Compiler(plugins=[PostgresPlugin()]).compile(IntegerRules, untyped)

    class DateRules(RuleSchema):
        value: date

    emulated = Table("emulated", MetaData(), Column("value", Date))
    with pytest.raises(CapabilityError, match="explicit storage adapter"):
        Compiler(plugins=[SQLitePlugin()]).compile(DateRules, emulated)


def test_numeric_lax_conversions_and_backend_limits_are_explicit() -> None:
    class FloatRules(RuleSchema):
        value: float

    integer = Table("integers", MetaData(), Column("value", Integer))
    converted_float = Compiler(plugins=[PostgresPlugin()]).compile(FloatRules, integer)
    assert converted_float.fields[0].coercion == "int-to-float"

    class DecimalRules(RuleSchema):
        value: Decimal

    converted_decimal = Compiler(plugins=[PostgresPlugin()]).compile(DecimalRules, integer)
    assert converted_decimal.fields[0].coercion == "int-to-decimal"

    class IntegerRules(RuleSchema):
        value: int

    numeric = Table("numeric", MetaData(), Column("value", Numeric(12, 2)))
    integral = Compiler(plugins=[PostgresPlugin()]).compile(IntegerRules, numeric)
    assert integral.fields[0].coercion == "integral-numeric-to-int64"

    floating = Table("floating", MetaData(), Column("value", Float))
    float_to_integer = Compiler(plugins=[PostgresPlugin()]).compile(IntegerRules, floating)
    postgres_sql = str(float_to_integer.predicate.compile(dialect=postgresql_dialect()))
    assert " < " in postgres_sql
    assert " <= " not in postgres_sql

    sql_server_conversion = Compiler(
        plugins=[MssqlPlugin(server_version=(16, 0))]
    ).compile(IntegerRules, floating)
    sql_server_sql = str(sql_server_conversion.predicate.compile(dialect=mssql_dialect()))
    assert " < " in sql_server_sql
    assert " <= " not in sql_server_sql
    assert "TRY_CAST" in sql_server_sql

    text = Table("text", MetaData(), Column("value", String))
    with pytest.raises(CapabilityError, match="precision and range"):
        Compiler(plugins=[MysqlPlugin(server_version=(8, 0, 36))]).compile(FloatRules, text)


def test_constraints_cannot_be_applied_to_a_known_mismatched_storage_type() -> None:
    class Positive(RuleSchema):
        value: int = Field(strict=True, gt=0)

    floating = Table("floating", MetaData(), Column("value", Float))
    compiled = Compiler(plugins=[PostgresPlugin()]).compile(Positive, floating)
    assert compiled.fields[0].coercion == "strict-mismatch:float-to-int"

    class BooleanRules(RuleSchema):
        value: bool

    text = Table("text", MetaData(), Column("value", String))
    with pytest.raises(CapabilityError, match="outside the frozen SQLRules 2.0 lax profile"):
        Compiler(plugins=[PostgresPlugin()]).compile(BooleanRules, text)
