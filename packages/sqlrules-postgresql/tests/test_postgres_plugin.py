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
    assert __version__ == "1.0.0"


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
    assert "~*" not in compiled


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
    contains_sql = str(rules["meta"][0].compile(dialect=dialect))
    has_key_sql = str(rules["meta"][1].compile(dialect=dialect))
    assert "@>" in contains_sql
    assert "?" in has_key_sql
    assert "@>" not in has_key_sql

    array_contains_sql = str(rules["tags"][0].compile(dialect=dialect))
    array_overlap_sql = str(rules["tags"][1].compile(dialect=dialect))
    assert "@>" in array_contains_sql and "&&" not in array_contains_sql
    assert "&&" in array_overlap_sql

    range_contains_sql = str(rules["span"][0].compile(dialect=dialect))
    range_overlap_sql = str(rules["span"][1].compile(dialect=dialect))
    assert "@>" in range_contains_sql and "&&" not in range_contains_sql
    assert "&&" in range_overlap_sql


def test_type_check_int_and_str() -> None:
    from sqlalchemy import Integer

    class Filter(BaseModel):
        age: int
        name: str

    table = Table(
        "users",
        MetaData(),
        Column("age", Integer),
        Column("name", String),
    )
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    dialect = postgresql.dialect()
    age_sql = str(rules["age"][0].compile(dialect=dialect))
    name_sql = str(rules["name"][0].compile(dialect=dialect))
    assert "IS NOT NULL" in age_sql.upper()
    assert "IS NOT NULL" in name_sql.upper()


def test_type_check_lax_int_on_string() -> None:
    class Filter(BaseModel):
        age: int

    table = Table("rows", MetaData(), Column("age", String))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["age"][0].compile(dialect=postgresql.dialect()))
    assert "~" in compiled


def test_type_check_strict_bool() -> None:
    from pydantic import ConfigDict
    from sqlalchemy import Boolean

    class Filter(BaseModel):
        model_config = ConfigDict(strict=True)
        active: bool

    table = Table("rows", MetaData(), Column("active", Boolean))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    compiled = str(
        rules["active"][0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "IN" in compiled.upper()


def test_type_check_optional_or_null() -> None:
    from sqlalchemy import Integer

    class Filter(BaseModel):
        age: int | None = None

    table = Table("rows", MetaData(), Column("age", Integer))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["age"][0].compile(dialect=postgresql.dialect()))
    assert "IS NULL" in compiled.upper()
