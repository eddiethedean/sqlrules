from __future__ import annotations

import re
import sqlite3
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects import sqlite
from sqlrules_sqlite import SQLitePlugin, __version__, register_regexp

from sqlrules import Compiler, JsonContains, JsonHasKey
from sqlrules.conformance import run_basic_conformance


def test_version() -> None:
    assert __version__ == "1.0.1"


def test_conformance() -> None:
    run_basic_conformance(SQLitePlugin(), operator="pattern")


def test_pattern_compiles() -> None:
    """SQLite REGEXP uses ``re.search`` (not Pydantic fullmatch); anchors are caller-owned."""

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)
    compiled = str(
        rules["name"][0].compile(
            dialect=sqlite.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert compiled == "items.name REGEXP '^A'"


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
    assert compiled == "items.name REGEXP '(?i)^A'"


def test_register_regexp_null_inputs_are_false() -> None:
    conn = sqlite3.connect(":memory:")
    register_regexp(conn)
    assert conn.execute("SELECT NULL REGEXP '^a'").fetchone()[0] == 0
    assert conn.execute("SELECT 'Abc' REGEXP NULL").fetchone()[0] == 0
    conn.close()


def test_register_regexp_matches() -> None:
    conn = sqlite3.connect(":memory:")
    register_regexp(conn)
    assert conn.execute("SELECT 'Abc' REGEXP '(?i)^a'").fetchone()[0] == 1
    assert conn.execute("SELECT 'Abc' REGEXP '^a'").fetchone()[0] == 0
    # Empty pattern: re.search('', value) is True for any string.
    assert conn.execute("SELECT 'Abc' REGEXP ''").fetchone()[0] == 1
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


def test_json_contains_executes_for_bool_str_int_null() -> None:
    class Filter(BaseModel):
        meta: Annotated[
            dict[str, Any],
            JsonContains({"active": True, "name": "hello", "n": 1, "missing": None}),
        ]

    metadata = MetaData()
    table = Table("items", metadata, Column("id", String), Column("meta", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            table.insert(),
            [
                {
                    "id": "match",
                    "meta": '{"active": true, "name": "hello", "n": 1, "missing": null}',
                },
                {
                    "id": "partial",
                    "meta": '{"active": true, "name": "hello", "n": 2}',
                },
                {"id": "null", "meta": None},
            ],
        )
        rows = [
            row[0]
            for row in conn.execute(select(table.c.id).where(*rules["meta"]).order_by(table.c.id))
        ]
    assert rows == ["match"]


def test_json_contains_dotted_key_and_array_payload() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"a.b": 1})]
        tags: Annotated[list[Any], JsonContains([1, 2])]

    metadata = MetaData()
    table = Table(
        "items",
        metadata,
        Column("id", String),
        Column("meta", String),
        Column("tags", String),
    )
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            table.insert(),
            [
                {"id": "match", "meta": '{"a.b": 1}', "tags": "[1,2]"},
                {"id": "nested", "meta": '{"a": {"b": 1}}', "tags": "[1,2]"},
                {"id": "spaced", "meta": '{"a.b": 1}', "tags": "[1, 2]"},
            ],
        )
        meta_rows = [
            row[0]
            for row in conn.execute(select(table.c.id).where(*rules["meta"]).order_by(table.c.id))
        ]
        tag_rows = [
            row[0]
            for row in conn.execute(select(table.c.id).where(*rules["tags"]).order_by(table.c.id))
        ]
    assert meta_rows == ["match", "spaced"]
    assert tag_rows == ["match", "nested", "spaced"]


def test_empty_json_contains_requires_object() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({})]

    metadata = MetaData()
    table = Table("items", metadata, Column("id", String), Column("meta", String))
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
    ).lower()
    assert "json_type" in compiled
    assert "object" in compiled

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            table.insert(),
            [
                {"id": "obj", "meta": "{}"},
                {"id": "arr", "meta": "[]"},
                {"id": "null", "meta": None},
            ],
        )
        rows = [
            row[0]
            for row in conn.execute(select(table.c.id).where(*rules["meta"]).order_by(table.c.id))
        ]
    assert rows == ["obj"]


def test_register_regexp_invalid_pattern_raises() -> None:
    conn = sqlite3.connect(":memory:")
    register_regexp(conn)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT 'Abc' REGEXP '['").fetchone()
    conn.close()


def test_type_check_int_integer_column() -> None:
    from sqlalchemy import Integer

    class Filter(BaseModel):
        age: int

    table = Table("users", MetaData(), Column("age", Integer))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["age"][0].compile(dialect=sqlite.dialect()))
    assert "IS NOT NULL" in compiled.upper()


def test_type_check_lax_int_string_uses_regexp() -> None:
    class Filter(BaseModel):
        age: int

    table = Table("rows", MetaData(), Column("age", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    compiled = str(
        rules["age"][0].compile(
            dialect=sqlite.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "REGEXP" in compiled
    assert "rows.age" in compiled


def test_type_check_lax_int_string_executes_with_register_regexp() -> None:
    class Filter(BaseModel):
        age: int

    metadata = MetaData()
    table = Table("rows", metadata, Column("id", String), Column("age", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        raw = conn.connection.dbapi_connection
        register_regexp(raw)  # type: ignore[arg-type]
        metadata.create_all(conn)
        conn.execute(
            table.insert(),
            [
                {"id": "ok", "age": "42"},
                {"id": "bad", "age": "x"},
                {"id": "null", "age": None},
            ],
        )
        rows = [
            row[0]
            for row in conn.execute(select(table.c.id).where(*rules["age"]).order_by(table.c.id))
        ]
    assert rows == ["ok"]
