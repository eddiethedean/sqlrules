from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table, Text
from sqlalchemy.dialects import mssql
from sqlrules_mssql import MssqlPlugin, __version__

from sqlrules import Compiler, JsonContains, JsonHasKey, UnsupportedConstraintError
from sqlrules.conformance import assert_builtins_preserved, assert_plugin_api_compatible


def test_version() -> None:
    assert __version__ == "1.0.0"


def test_plugin_api() -> None:
    plugin = MssqlPlugin()
    assert_plugin_api_compatible(plugin)
    assert_builtins_preserved(plugin, on_conflict="replace")


def test_length_uses_trailing_space_aware_len() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(min_length=2, max_length=10)]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[MssqlPlugin()],
        dialect="mssql",
        cache=False,
    ).compile(Filter, table)
    dialect = mssql.dialect()
    min_sql = str(rules["name"][0].compile(dialect=dialect)).lower()
    max_sql = str(rules["name"][1].compile(dialect=dialect)).lower()
    assert "len(" in min_sql and ">=" in min_sql
    assert "len(" in max_sql and "<=" in max_sql
    assert "||" in min_sql or "concat" in min_sql or "+" in min_sql
    assert "length(" not in min_sql
    assert "length(" not in max_sql


def test_json_operators_compile() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]

    table = Table("items", MetaData(), Column("meta", Text))
    rules = Compiler(
        plugins=[MssqlPlugin()],
        dialect="mssql",
        cache=False,
    ).compile(Filter, table)
    assert len(rules["meta"]) == 2
    dialect = mssql.dialect()
    contains_sql = str(rules["meta"][0].compile(dialect=dialect)).lower()
    has_key_sql = str(rules["meta"][1].compile(dialect=dialect)).lower()
    assert "json_value" in contains_sql
    assert "openjson" in has_key_sql


def test_json_contains_none_uses_openjson_null_type() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"a": None})]

    table = Table("items", MetaData(), Column("meta", Text))
    rules = Compiler(
        plugins=[MssqlPlugin()],
        dialect="mssql",
        cache=False,
    ).compile(Filter, table)
    compiled = str(
        rules["meta"][0].compile(
            dialect=mssql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()
    assert "openjson" in compiled
    assert "null" in compiled
    assert "'none'" not in compiled


def test_json_contains_nested_uses_compact_json_query() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"nested": {"x": 1}})]

    table = Table("items", MetaData(), Column("meta", Text))
    rules = Compiler(
        plugins=[MssqlPlugin()],
        dialect="mssql",
        cache=False,
    ).compile(Filter, table)
    compiled = str(
        rules["meta"][0].compile(
            dialect=mssql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert '{"x":1}' in compiled
    assert '{"x": 1}' not in compiled


def test_pattern_remains_unsupported() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    table = Table("items", MetaData(), Column("name", String))
    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        Compiler(
            plugins=[MssqlPlugin()],
            dialect="mssql",
            cache=False,
        ).compile(Filter, table)


def test_empty_json_contains_requires_object() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({})]

    table = Table("items", MetaData(), Column("meta", Text))
    rules = Compiler(
        plugins=[MssqlPlugin()],
        dialect="mssql",
        cache=False,
    ).compile(Filter, table)
    assert len(rules["meta"]) == 1
    compiled = str(
        rules["meta"][0].compile(
            dialect=mssql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()
    assert "isjson" in compiled
    assert "json_query" in compiled


def test_type_check_lax_float_string_unsupported() -> None:
    class Filter(BaseModel):
        score: float

    table = Table("rows", MetaData(), Column("score", String))
    with pytest.raises(UnsupportedConstraintError, match="float"):
        Compiler(
            plugins=[MssqlPlugin()],
            dialect="mssql",
            emit_type_checks=True,
            cache=False,
        ).compile(Filter, table)


def test_type_check_int_integer_column() -> None:
    from sqlalchemy import Integer

    class Filter(BaseModel):
        age: int

    table = Table("users", MetaData(), Column("age", Integer))
    rules = Compiler(
        plugins=[MssqlPlugin()],
        dialect="mssql",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["age"][0].compile(dialect=mssql.dialect()))
    assert "IS NOT NULL" in compiled.upper()
