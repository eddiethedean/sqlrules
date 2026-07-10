from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY, INT4RANGE, JSONB, TEXT
from sqlrules_postgresql import PostgresPlugin, __version__

from sqlrules import (
    ArrayContains,
    ArrayOverlap,
    Compiler,
    JsonContains,
    JsonHasKey,
    RangeContains,
    RangeOverlap,
)
from sqlrules.conformance import run_basic_conformance


def test_version() -> None:
    assert __version__ == "0.4.0"


def test_conformance() -> None:
    run_basic_conformance(PostgresPlugin(), operator="pattern")


def test_pattern_compiles() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["name"][0].compile(dialect=postgresql.dialect()))
    assert "~" in compiled


def test_pattern_ignore_case_uses_star() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A", re.I))]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["name"][0].compile(dialect=postgresql.dialect()))
    assert "~*" in compiled


def test_json_array_range_operators() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]
        tags: Annotated[list[str], ArrayContains(["admin"]), ArrayOverlap(["x"])]
        span: Annotated[int, RangeContains(5), RangeOverlap([1, 10])]

    table = Table(
        "rows",
        MetaData(),
        Column("meta", JSONB),
        Column("tags", ARRAY(TEXT)),
        Column("span", INT4RANGE),
    )
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    assert len(rules["meta"]) == 2
    assert len(rules["tags"]) == 2
    assert len(rules["span"]) == 2

    dialect = postgresql.dialect()
    meta_sql = " ".join(str(expr.compile(dialect=dialect)) for expr in rules["meta"])
    assert "@>" in meta_sql or "?" in meta_sql or "has_key" in meta_sql.lower()
    tags_sql = " ".join(str(expr.compile(dialect=dialect)) for expr in rules["tags"])
    assert "@>" in tags_sql or "&&" in tags_sql
    span_sql = " ".join(str(expr.compile(dialect=dialect)) for expr in rules["span"])
    assert "@>" in span_sql or "&&" in span_sql
