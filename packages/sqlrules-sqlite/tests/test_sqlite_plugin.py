from __future__ import annotations

import re
import sqlite3
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects import sqlite
from sqlrules_sqlite import SQLitePlugin, __version__, register_regexp

from sqlrules import Compiler, JsonContains, JsonHasKey
from sqlrules.conformance import run_basic_conformance


def test_version() -> None:
    assert __version__ == "0.4.0"


def test_conformance() -> None:
    run_basic_conformance(SQLitePlugin(), operator="pattern")


def test_pattern_compiles() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["name"][0].compile(dialect=sqlite.dialect()))
    assert "REGEXP" in compiled
    assert "(?i)" not in compiled


def test_pattern_ignore_case_prefix() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A", re.I))]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["name"][0].compile(compile_kwargs={"literal_binds": True}))
    assert "(?i)" in compiled
    assert "REGEXP" in compiled


def test_register_regexp_matches() -> None:
    conn = sqlite3.connect(":memory:")
    register_regexp(conn)
    assert conn.execute("SELECT 'Abc' REGEXP '(?i)^a'").fetchone()[0] == 1
    assert conn.execute("SELECT 'Abc' REGEXP '^a'").fetchone()[0] == 0
    conn.close()


def test_pattern_translator_with_register_regexp_executes() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^a", re.I))]

    metadata = MetaData()
    table = Table("items", metadata, Column("name", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        raw = conn.connection.dbapi_connection
        register_regexp(raw)  # type: ignore[arg-type]
        metadata.create_all(conn)
        conn.execute(table.insert(), [{"name": "Abc"}, {"name": "zzz"}])
        stmt = select(table.c.name).where(*rules["name"])
        rows = [row[0] for row in conn.execute(stmt)]
    assert rows == ["Abc"]


def test_json_operators_compile() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]

    table = Table("items", MetaData(), Column("meta", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)
    assert len(rules["meta"]) == 2
    contains_sql = str(rules["meta"][0].compile(dialect=sqlite.dialect())).lower()
    has_key_sql = str(rules["meta"][1].compile(dialect=sqlite.dialect())).lower()
    assert "json_extract" in contains_sql
    assert "json_type" in has_key_sql
    assert "json_extract" not in has_key_sql


def test_empty_json_contains() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({})]

    table = Table("items", MetaData(), Column("meta", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)
    compiled = str(
        rules["meta"][0].compile(
            dialect=sqlite.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert compiled.strip() in {"1", "true", "True"}
