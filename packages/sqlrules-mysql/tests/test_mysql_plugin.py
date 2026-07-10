from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table, Text
from sqlalchemy.dialects import mysql
from sqlrules_mysql import MysqlPlugin, __version__

from sqlrules import Compiler, FullTextMatch, JsonContains, JsonHasKey
from sqlrules.conformance import run_basic_conformance


def test_version() -> None:
    assert __version__ == "0.4.0"


def test_conformance() -> None:
    run_basic_conformance(MysqlPlugin(), operator="pattern")


def test_pattern_and_json_compile() -> None:
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
    dialect = mysql.dialect()
    assert "REGEXP" in str(rules["name"][0].compile(dialect=dialect))
    meta_sql = " ".join(str(expr.compile(dialect=dialect)) for expr in rules["meta"])
    assert "json_contains" in meta_sql.lower()
    body_sql = str(rules["body"][0].compile(dialect=dialect))
    assert "match" in body_sql.lower() or "against" in body_sql.lower()
