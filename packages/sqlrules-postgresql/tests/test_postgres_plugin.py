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


def _sql(expr: object, *, literal_binds: bool = True) -> str:
    return str(
        expr.compile(  # type: ignore[union-attr]
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": literal_binds} if literal_binds else {},
        )
    )


def test_version() -> None:
    assert __version__ == "1.0.1"


def test_conformance() -> None:
    run_basic_conformance(PostgresPlugin(), operator="pattern")


def test_pattern_compiles() -> None:
    """PG ``~`` is substring search; Pydantic validates fullmatch — patterns often use ^/$."""

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    assert _sql(rules["name"][0]) == "items.name ~ '^A'"


def test_pattern_ignore_case_uses_star() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A", re.I))]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    assert _sql(rules["name"][0]) == "items.name ~* '^A'"


def test_unanchored_pattern_emits_search_semantics() -> None:
    """Unanchored patterns are emitted as-is (PG ``~`` search, not Pydantic fullmatch)."""

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"abc")]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    assert _sql(rules["name"][0]) == "items.name ~ 'abc'"


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

    # JSONB containment: operator + bound payload (literal_binds unsupported for JSONB).
    contains = rules["meta"][0]
    assert getattr(contains.operator, "opstring", None) == "@>"  # type: ignore[attr-defined]
    assert contains.right.value == {"active": True}  # type: ignore[attr-defined]
    assert "@>" in _sql(contains, literal_binds=False)

    assert _sql(rules["meta"][1]) == "rows.meta ? 'active'"
    assert _sql(rules["tags"][0]) == "rows.tags @> ARRAY['admin']"
    assert _sql(rules["tags"][1]) == "rows.tags && ARRAY['x']"
    assert _sql(rules["span"][0]) == "rows.span @> 5"
    overlap = rules["span"][1]
    assert getattr(overlap.operator, "opstring", None) == "&&"  # type: ignore[attr-defined]
    assert overlap.right.value == [1, 10]  # type: ignore[attr-defined]


def test_empty_json_contains_uses_containment() -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({})]

    table = Table("rows", MetaData(), Column("meta", JSONB))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    expr = rules["meta"][0]
    assert getattr(expr.operator, "opstring", None) == "@>"  # type: ignore[attr-defined]
    assert expr.right.value == {}  # type: ignore[attr-defined]
    assert "@>" in _sql(expr, literal_binds=False)


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
    assert _sql(rules["age"][0], literal_binds=False).upper().count("IS NOT NULL") == 1
    assert "users.age" in _sql(rules["age"][0], literal_binds=False)
    assert "users.name" in _sql(rules["name"][0], literal_binds=False)
    assert "IS NOT NULL" in _sql(rules["name"][0], literal_binds=False).upper()


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
    compiled = _sql(rules["age"][0])
    assert "rows.age" in compiled
    assert "~" in compiled
    # Lax int-on-text uses a digit regex, not a bare IS NOT NULL.
    assert "IS NOT NULL" not in compiled.upper() or "~" in compiled


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
    compiled = _sql(rules["active"][0])
    assert "rows.active" in compiled
    assert "IN" in compiled.upper()
    assert "true" in compiled.lower() or "True" in compiled


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
    compiled = _sql(rules["age"][0], literal_binds=False).upper()
    assert "IS NULL" in compiled
    assert "IS NOT NULL" in compiled
