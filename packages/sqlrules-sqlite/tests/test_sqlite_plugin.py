from __future__ import annotations

import re
import sqlite3
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
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


def test_register_regexp_matches() -> None:
    conn = sqlite3.connect(":memory:")
    register_regexp(conn)
    assert conn.execute("SELECT 'Abc' REGEXP '(?i)^a'").fetchone()[0] == 1
    assert conn.execute("SELECT 'Abc' REGEXP '^a'").fetchone()[0] == 0
    conn.close()


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
    sql = " ".join(str(expr.compile(dialect=sqlite.dialect())) for expr in rules["meta"])
    assert "json_extract" in sql.lower() or "json_type" in sql.lower()
