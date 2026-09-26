from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects.mssql import dialect
from sqlrules_mssql import MssqlPlugin, __version__

from sqlrules import Compiler, JsonContains, JsonHasKey, RuleSchema
from sqlrules.conformance import run_basic_conformance


def test_version_and_plugin_conformance() -> None:
    assert __version__ == "2.0.0"
    run_basic_conformance(MssqlPlugin(), operator="min_length")


def test_length_and_json_constraints_compile() -> None:
    class Rules(RuleSchema):
        name: Annotated[str, Field(min_length=2, max_length=40)]
        meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]

    table = Table(
        "rows",
        MetaData(),
        Column("name", String),
        Column("meta", String),
    )
    compiled = Compiler(
        plugins=[MssqlPlugin(server_version=(16, 0), compatibility_level=160)]
    ).compile(Rules, table)
    sql = str(compiled.predicate.compile(dialect=dialect()))
    assert "len(" in sql.lower()
    assert "isjson" in sql.lower()
    assert "left(ltrim" in sql.lower()
    assert "openjson" in sql.lower()
    assert " as oj" in sql.lower()
    assert "as oj(" not in sql.lower()
    assert compiled.fields[1].coercion == "validated-json-text"


def test_empty_json_contains_checks_for_an_object_root() -> None:
    class Rules(RuleSchema):
        meta: Annotated[dict[str, Any], JsonContains({})]

    table = Table("rows", MetaData(), Column("meta", String))
    compiled = Compiler(
        plugins=[MssqlPlugin(server_version=(16, 0), compatibility_level=160)]
    ).compile(Rules, table)
    sql = str(compiled.predicate.compile(dialect=dialect())).lower()
    assert "left(ltrim" in sql


def test_text_to_integer_uses_try_cast_and_digit_validation() -> None:
    class Rules(RuleSchema):
        value: int

    table = Table("rows", MetaData(), Column("value", String))
    compiled = Compiler(plugins=[MssqlPlugin(server_version=(16, 0))]).compile(Rules, table)
    sql = str(compiled.predicate.compile(dialect=dialect()))
    assert "TRY_CAST" in sql
    assert "NOT LIKE" in sql
    assert compiled.fields[0].coercion == "text-to-int"


def test_sql_server_totalizes_predicates_with_case_expressions() -> None:
    class Rules(RuleSchema):
        value: int

    table = Table("rows", MetaData(), Column("value", String))
    compiled = Compiler(plugins=[MssqlPlugin(server_version=(16, 0))]).compile(Rules, table)
    sql = str(compiled.predicate.compile(dialect=dialect())).lower()
    assert "case when" in sql
    assert "coalesce(" not in sql


def test_pattern_remains_a_capability_error() -> None:
    class Rules(RuleSchema):
        name: Annotated[str, Field(pattern="^A")]

    table = Table("rows", MetaData(), Column("name", String))
    from sqlrules import CapabilityError

    try:
        Compiler(plugins=[MssqlPlugin()]).compile(Rules, table)
    except CapabilityError as exc:
        assert "pattern" in str(exc)
    else:  # pragma: no cover - assertion is the capability contract
        raise AssertionError("SQL Server does not promise regex equivalence")


def test_json_requires_server_version_and_database_compatibility_level() -> None:
    class Rules(RuleSchema):
        meta: Annotated[dict[str, Any], JsonContains({"active": True})]

    table = Table("rows", MetaData(), Column("meta", String))
    from sqlrules import CapabilityError

    try:
        Compiler(plugins=[MssqlPlugin(server_version=(16, 0))]).compile(Rules, table)
    except CapabilityError as exc:
        assert "compatibility level 130" in str(exc)
    else:  # pragma: no cover - assertion is the capability contract
        raise AssertionError("OPENJSON requires an explicit compatibility level")

    try:
        Compiler(plugins=[MssqlPlugin(server_version=(16, 0), compatibility_level=120)]).compile(
            Rules, table
        )
    except CapabilityError as exc:
        assert "compatibility level 130" in str(exc)
    else:  # pragma: no cover - assertion is the capability contract
        raise AssertionError("OPENJSON requires compatibility level 130 or higher")
