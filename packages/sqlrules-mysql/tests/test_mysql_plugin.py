from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import JSON, Column, MetaData, String, Table
from sqlalchemy.dialects.mysql import dialect
from sqlrules_mysql import MysqlPlugin, __version__

from sqlrules import Compiler, FullTextMatch, JsonContains, RuleSchema
from sqlrules.conformance import run_basic_conformance


def test_version_and_plugin_conformance() -> None:
    assert __version__ == "2.0.0"
    run_basic_conformance(MysqlPlugin(), operator="pattern")


def test_pattern_json_and_fulltext_constraints_compile() -> None:
    class Rules(RuleSchema):
        name: Annotated[str, Field(pattern=r"^A")]
        meta: Annotated[dict[str, Any], JsonContains({"active": True})]
        body: Annotated[str, FullTextMatch("sqlrules")]

    table = Table(
        "rows",
        MetaData(),
        Column("name", String),
        Column("meta", JSON),
        Column("body", String),
    )
    compiled = Compiler(plugins=[MysqlPlugin(server_version=(8, 0, 36))]).compile(Rules, table)
    sql = str(compiled.predicate.compile(dialect=dialect()))
    assert "REGEXP" in sql
    assert "json_contains" in sql
    assert "MATCH" in sql


def test_integer_text_profile_is_server_version_gated() -> None:
    class Rules(RuleSchema):
        count: int

    table = Table("rows", MetaData(), Column("count", String))
    from sqlrules import CapabilityError

    try:
        Compiler(plugins=[MysqlPlugin()]).compile(Rules, table)
    except CapabilityError as exc:
        assert "MySQL 8.0+" in str(exc)
    else:  # pragma: no cover - assertion is the capability contract
        raise AssertionError("text-to-integer needs a configured MySQL version")

    compiled = Compiler(plugins=[MysqlPlugin(server_version=(8, 0, 36))]).compile(Rules, table)
    assert compiled.fields[0].coercion == "text-to-int"
