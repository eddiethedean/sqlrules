from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlrules_mysql import MysqlPlugin
from sqlrules_postgresql import PostgresPlugin
from sqlrules_sqlite import SQLitePlugin

import sqlrules
from sqlrules import (
    CapabilityError,
    Compiler,
    InvalidModelError,
    MissingColumnError,
    PluginError,
    RuleConfig,
    RuleSchema,
    TranslatorRegistry,
    notwhere,
    where,
)


def test_compiled_result_contains_one_total_root_and_explain_plan() -> None:
    class Rules(RuleSchema):
        age: Annotated[int, Field(ge=18)]
        name: Annotated[str, Field(min_length=2)]

    table = Table(
        "users",
        MetaData(),
        Column("age", Integer),
        Column("name", String),
    )
    compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)
    assert where(compiled) == [compiled.predicate]
    assert sqlrules.flatten(compiled) == [compiled.predicate]
    assert str(notwhere(compiled)[0]) == str(~compiled.predicate)
    assert tuple(item.name for item in compiled.fields) == ("age", "name")
    explanation = compiled.explain()
    assert explanation["backend"] == "sqlite"
    assert explanation["fields"][0]["logical_type"] == "int"
    assert explanation["fields"][0]["coercion"] == "sqlite-int64"
    assert "predicate" in explanation["fields"][0]


def test_compiler_requires_exactly_one_explicit_backend_provider() -> None:
    class Rules(RuleSchema):
        age: int

    with pytest.raises(PluginError, match="exactly one"):
        Compiler().compile(Rules, Table("items", MetaData(), Column("age", Integer)))
    with pytest.raises(PluginError, match="exactly one"):
        Compiler(plugins=[SQLitePlugin(), PostgresPlugin()])


def test_plain_pydantic_models_need_explicit_conversion() -> None:
    class Request(BaseModel):
        age: int

    compiler = Compiler(plugins=[SQLitePlugin()])
    with pytest.raises(InvalidModelError, match="from_pydantic"):
        compiler.compile(Request, Table("items", MetaData(), Column("age", Integer)))  # type: ignore[arg-type]


def test_column_mapping_and_missing_columns() -> None:
    class Rules(RuleSchema):
        source_name: str

    table = Table("users", MetaData(), Column("db_name", String))
    compiler = Compiler(plugins=[SQLitePlugin()])
    compiled = compiler.compile(Rules, table, column_map={"source_name": table.c.db_name})
    assert compiled.fields[0].column is table.c.db_name

    class Missing(RuleSchema):
        absent: int

    with pytest.raises(MissingColumnError, match="absent"):
        compiler.compile(Missing, table)


def test_sqlrules_field_column_binding_overrides_python_field_name() -> None:
    class Rules(RuleSchema):
        value: int = sqlrules.Field(column="stored_value")

    table = Table("items", MetaData(), Column("stored_value", Integer))
    compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)
    assert compiled.fields[0].column is table.c.stored_value


def test_backend_capability_errors_are_compile_time_errors() -> None:
    class NumericText(RuleSchema):
        value: int

    table = Table("items", MetaData(), Column("value", String))
    with pytest.raises(CapabilityError, match="PostgreSQL 16"):
        Compiler(plugins=[PostgresPlugin()]).compile(NumericText, table)

    class FloatText(RuleSchema):
        value: float

    with pytest.raises(CapabilityError, match="precision and range"):
        Compiler(plugins=[MysqlPlugin(server_version=(8, 0, 36))]).compile(FloatText, table)


def test_strict_text_int_is_a_known_mismatch_and_sqlite_strict_bool_is_unsupported() -> None:
    class StrictNumber(RuleSchema):
        value: StrictInt

    text_table = Table("items", MetaData(), Column("value", String))
    compiled = Compiler(plugins=[SQLitePlugin()]).compile(StrictNumber, text_table)
    assert compiled.fields[0].capability == "sqlite-runtime-storage-class"
    assert compiled.fields[0].coercion == "runtime-type-match"

    class StrictBoolean(RuleSchema):
        value: bool = Field(strict=True)

    bool_table = Table("items", MetaData(), Column("value", Integer))
    with pytest.raises(CapabilityError, match="no native boolean storage class"):
        Compiler(plugins=[SQLitePlugin()]).compile(StrictBoolean, bool_table)


def test_empty_schema_compiles_to_true_only_when_explicitly_allowed() -> None:
    class Empty(RuleSchema):
        __rule_config__ = RuleConfig(allow_empty=True)

    compiled = Compiler(plugins=[SQLitePlugin()]).compile(Empty, Table("items", MetaData()))
    assert "case when" in str(compiled.predicate).lower()
    assert "true" in str(compiled.predicate)


def test_conflict_policy_uses_a_private_registry_snapshot() -> None:
    registry = TranslatorRegistry()
    compiler = Compiler(plugins=[SQLitePlugin()], registry=registry)
    assert "pattern" in compiler.registry
    assert "pattern" not in registry


def test_compiler_rejects_removed_unsupported_policies() -> None:
    with pytest.raises(sqlrules.ConfigurationError, match="on_unsupported"):
        Compiler(on_unsupported="ignore")  # type: ignore[arg-type]


def test_string_domains_require_deterministic_collation() -> None:
    class Rules(RuleSchema):
        status: Literal["ready", "pending"]

    table = Table("items", MetaData(), Column("status", String(collation="NOCASE")))
    with pytest.raises(CapabilityError, match="BINARY"):
        Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)

    binary = Table("items", MetaData(), Column("status", String(collation="BINARY")))
    compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, binary)
    assert compiled.fields[0].logical_type == "str"


def test_concurrent_compiles_keep_diagnostics_local_and_cache_shims_inert() -> None:
    class Rules(RuleSchema):
        age: Annotated[int, Field(ge=18)]

    class DiagnosticPlugin(SQLitePlugin):
        def register(self, registry: TranslatorRegistry) -> None:
            super().register(registry)

            def translate(constraint, value, context):
                context.record(
                    severity="info",
                    field=constraint.field,
                    operator=constraint.operator,
                    value=constraint.value,
                    message="translated in this compile",
                    code="test_translation",
                )
                return value >= constraint.value

            registry.register_constraint("ge", translate, on_conflict="replace")

    table = Table("users", MetaData(), Column("age", Integer))
    compiler = Compiler(plugins=[DiagnosticPlugin()], cache=True)

    def compile_once(_: int):
        return compiler.compile(Rules, table)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(compile_once, range(32)))

    assert all(len(result.diagnostics) == 1 for result in results)
    assert all(result.diagnostics[0].code == "test_translation" for result in results)
    assert len({str(result.predicate) for result in results}) == 1

    uncached = Compiler(plugins=[DiagnosticPlugin()], cache=False).compile(Rules, table)
    sqlrules.clear_model_cache()
    assert str(uncached.predicate) == str(results[0].predicate)
