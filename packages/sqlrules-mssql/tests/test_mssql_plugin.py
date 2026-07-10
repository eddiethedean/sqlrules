from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table, Text
from sqlalchemy.dialects import mssql
from sqlrules_mssql import MssqlPlugin, __version__

from sqlrules import Compiler, JsonContains, JsonHasKey
from sqlrules.conformance import assert_builtins_preserved, assert_plugin_api_compatible


def test_version() -> None:
    assert __version__ == "0.4.0"


def test_plugin_api() -> None:
    plugin = MssqlPlugin()
    assert_plugin_api_compatible(plugin)
    assert_builtins_preserved(plugin, on_conflict="replace")


def test_length_uses_len() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(min_length=2, max_length=10)]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[MssqlPlugin()],
        dialect="mssql",
        cache=False,
    ).compile(Filter, table)
    dialect = mssql.dialect()
    sql = " ".join(str(expr.compile(dialect=dialect)) for expr in rules["name"])
    assert "len(" in sql.lower()


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
    sql = " ".join(str(expr.compile(dialect=dialect)) for expr in rules["meta"])
    assert "json_value" in sql.lower() or "json_query" in sql.lower()
