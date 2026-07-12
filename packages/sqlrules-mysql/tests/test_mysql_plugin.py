from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table, Text
from sqlalchemy.dialects import mysql
from sqlrules_mysql import MysqlPlugin, __version__

from sqlrules import Compiler, FullTextMatch, JsonContains, JsonHasKey
from sqlrules.conformance import run_basic_conformance


def _sql(expr: object, *, literal_binds: bool = True) -> str:
    return str(
        expr.compile(  # type: ignore[union-attr]
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": literal_binds} if literal_binds else {},
        )
    )


def test_version() -> None:
    assert __version__ == "1.0.1"


def test_conformance() -> None:
    run_basic_conformance(MysqlPlugin(), operator="pattern")


def test_pattern_and_json_compile() -> None:
    """MySQL REGEXP is CI for non-binary collations; ignore_case is intentionally unused."""

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]
        meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]
        body: Annotated[str, FullTextMatch("hello")]

    table = Table(
        "items",
        MetaData(),
        Column("name", String),
        Column("meta", Text),
        Column("body", Text),
    )
    rules = Compiler(
        plugins=[MysqlPlugin()],
        dialect="mysql",
        cache=False,
    ).compile(Filter, table)

    assert _sql(rules["name"][0]) == "items.name REGEXP '^A'"

    contains_sql = _sql(rules["meta"][0]).lower()
    assert "json_contains(items.meta" in contains_sql
    assert '{"active":true}' in contains_sql.replace(" ", "")
    assert "json_contains_path" not in contains_sql

    has_key_sql = _sql(rules["meta"][1]).lower()
    assert "json_contains_path(items.meta" in has_key_sql
    assert '$."active"' in has_key_sql or "$" in has_key_sql

    body_sql = _sql(rules["body"][0]).lower()
    assert "match" in body_sql and "against" in body_sql
    assert "hello" in body_sql


def test_pattern_ignore_case_does_not_invent_binary() -> None:
    """Case-insensitive PatternSpec must not invent REGEXP BINARY (collation owns CI)."""

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A", re.I))]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[MysqlPlugin()],
        dialect="mysql",
        cache=False,
    ).compile(Filter, table)
    compiled = _sql(rules["name"][0])
    assert compiled == "items.name REGEXP '^A'"
    assert "BINARY" not in compiled.upper()
    assert "(?i)" not in compiled


def test_type_check_int_and_lax_string() -> None:
    from sqlalchemy import Integer

    class Typed(BaseModel):
        age: int

    class Textual(BaseModel):
        age: int

    typed_table = Table("users", MetaData(), Column("age", Integer))
    text_table = Table("rows", MetaData(), Column("age", String))
    compiler = Compiler(
        plugins=[MysqlPlugin()],
        dialect="mysql",
        emit_type_checks=True,
        cache=False,
    )
    typed_sql = _sql(compiler.compile(Typed, typed_table)["age"][0], literal_binds=False)
    text_sql = _sql(compiler.compile(Textual, text_table)["age"][0])
    assert "users.age" in typed_sql or "`users`.age" in typed_sql
    assert "IS NOT NULL" in typed_sql.upper()
    assert "age REGEXP" in text_sql.replace("`", "")
    assert "REGEXP" in text_sql
    assert "^[+-]?(0|[1-9][0-9]*)$" in text_sql


def test_type_check_optional_allow_none() -> None:
    from sqlalchemy import Integer

    class Filter(BaseModel):
        age: int | None = None

    table = Table("users", MetaData(), Column("age", Integer))
    rules = Compiler(
        plugins=[MysqlPlugin()],
        dialect="mysql",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    compiled = _sql(rules["age"][0], literal_binds=False).upper()
    assert "IS NULL" in compiled
    assert "IS NOT NULL" in compiled
