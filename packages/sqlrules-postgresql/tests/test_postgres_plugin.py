from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects.postgresql import ARRAY, INT4RANGE, JSONB, dialect
from sqlrules_postgresql import PostgresPlugin, __version__

from sqlrules import ArrayContains, Compiler, JsonContains, RangeContains, RuleSchema
from sqlrules.conformance import run_basic_conformance


def test_version_and_plugin_conformance() -> None:
    assert __version__ == "2.0.0"
    run_basic_conformance(PostgresPlugin(server_version=(16, 0)), operator="pattern")


def test_pattern_json_array_and_range_compile_with_v2_provider() -> None:
    class Rules(RuleSchema):
        name: Annotated[str, Field(pattern=re.compile(r"^a", re.I))]
        meta: Annotated[dict[str, Any], JsonContains({"active": True})]
        tags: Annotated[list[str], ArrayContains(["admin"])]
        span: Annotated[int, RangeContains(5)]

    table = Table(
        "rows",
        MetaData(),
        Column("name", String),
        Column("meta", JSONB),
        Column("tags", ARRAY(String)),
        Column("span", INT4RANGE),
    )
    compiled = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))]).compile(Rules, table)
    assert len(compiled.fields) == 4
    assert compiled.fields[-1].logical_type == "range"
    sql = str(compiled.predicate.compile(dialect=dialect()))
    assert "~*" in sql
    assert "@>" in sql
    assert "@>" in sql


def test_string_literal_requires_explicit_deterministic_collation() -> None:
    from typing import Literal

    from sqlrules import CapabilityError

    class Rules(RuleSchema):
        status: Literal["ready", "pending"]

    table = Table("rows", MetaData(), Column("status", String))
    try:
        Compiler(plugins=[PostgresPlugin()]).compile(Rules, table)
    except CapabilityError as exc:
        assert "C or POSIX" in str(exc)
    else:  # pragma: no cover - assertion is the capability contract
        raise AssertionError("string literal compilation needs explicit collation")
