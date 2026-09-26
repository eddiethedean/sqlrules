from __future__ import annotations

import sqlite3
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import JSON, Column, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects.sqlite import dialect
from sqlrules_sqlite import SQLitePlugin, __version__, register_regexp

from sqlrules import Compiler, JsonContains, JsonHasKey, RuleSchema
from sqlrules.conformance import run_basic_conformance


def test_version_and_plugin_conformance() -> None:
    assert __version__ == "2.0.0"
    run_basic_conformance(SQLitePlugin(), operator="pattern")


def test_pattern_and_json_markers_compile() -> None:
    class Rules(RuleSchema):
        name: Annotated[str, Field(pattern=r"^A")]
        meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]

    table = Table(
        "rows",
        MetaData(),
        Column("name", String),
        Column("meta", JSON),
    )
    compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)
    sql = str(compiled.predicate.compile(dialect=dialect()))
    assert "REGEXP" in sql
    assert "json_type" in sql
    assert "json_valid" in sql


def test_regexp_handles_text_and_non_text_values() -> None:
    db = sqlite3.connect(":memory:")
    register_regexp(db)
    assert db.execute("SELECT 'Ada' REGEXP '^A'").fetchone() == (1,)
    assert db.execute("SELECT 12 REGEXP '^1'").fetchone() == (0,)
    assert db.execute("SELECT NULL REGEXP '^1'").fetchone() == (0,)
    db.close()


def test_json_contains_executes_on_sqlite() -> None:
    class Rules(RuleSchema):
        meta: Annotated[dict[str, Any], JsonContains({"active": True})]

    table = Table(
        "rows",
        MetaData(),
        Column("id", Integer),
        Column("meta", JSON),
    )
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO rows (id, meta) VALUES (1, '{\"active\": true}'), "
            "(2, '{\"active\": false}'), (3, 'not json'), (4, NULL)"
        )
        compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)
        found = connection.execute(select(table.c.id).where(compiled.predicate)).all()
    assert found == [(1,)]
    engine.dispose()
