"""SQLRules 0.4 markers, PatternSpec, and list/dict type support."""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules
from assert_sql import assert_custom_op
from sqlrules import (
    ArrayContains,
    ArrayOverlap,
    Compiler,
    FullTextMatch,
    JsonContains,
    JsonHasKey,
    RangeContains,
    RangeOverlap,
    UnsupportedConstraintError,
)
from sqlrules.ir import Constraint
from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import default_registry


@pytest.fixture
def items() -> Table:
    return Table(
        "items",
        MetaData(),
        Column("name", String),
        Column("meta", String),
        Column("tags", String),
        Column("span", Integer),
        Column("body", String),
        Column("age", Integer),
    )


def test_marker_extracted_into_ir(items: Table) -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"active": True})]
        tags: Annotated[list[str], ArrayContains(["admin"]), ArrayOverlap(["x"])]
        span: Annotated[int, RangeContains(5), RangeOverlap([1, 10])]
        body: Annotated[str, FullTextMatch("hello")]

    model_ir = Compiler(cache=False).compile_model(Filter)
    by_field = {field.descriptor.name: field.constraints for field in model_ir.fields}
    assert by_field["meta"] == (Constraint("meta", "json_contains", {"active": True}),)
    assert by_field["tags"] == (
        Constraint("tags", "array_contains", ["admin"]),
        Constraint("tags", "array_overlap", ["x"]),
    )
    assert by_field["span"] == (
        Constraint("span", "range_contains", 5),
        Constraint("span", "range_overlap", [1, 10]),
    )
    assert by_field["body"] == (Constraint("body", "fulltext_match", "hello"),)


def test_marker_requires_plugin_translator(items: Table) -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonHasKey("active")]

    with pytest.raises(UnsupportedConstraintError, match="json_has_key"):
        sqlrules.compile(Filter, items)


def test_marker_compiles_with_custom_translator(items: Table) -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"a": 1})]

    registry = default_registry().copy()
    registry.register_constraint(
        "json_contains",
        lambda c, col, ctx: col.op("@>")(c.value),
        on_conflict="raise",
    )
    rules = Compiler(registry=registry, cache=False).compile(Filter, items)
    assert_custom_op(
        rules["meta"][0],
        column_name="meta",
        opstring="@>",
        value={"a": 1},
    )


def test_each_marker_compiles_with_dedicated_translator(items: Table) -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonHasKey("k")]
        tags: Annotated[list[str], ArrayContains(["a"]), ArrayOverlap(["b"])]
        span: Annotated[int, RangeContains(3), RangeOverlap([0, 9])]
        body: Annotated[str, FullTextMatch("q")]

    registry = default_registry().copy()
    registry.register_constraint(
        "json_has_key",
        lambda c, col, ctx: col.op("?")(c.value),
        on_conflict="raise",
    )
    registry.register_constraint(
        "array_contains",
        lambda c, col, ctx: col.op("@>")(c.value),
        on_conflict="raise",
    )
    registry.register_constraint(
        "array_overlap",
        lambda c, col, ctx: col.op("&&")(c.value),
        on_conflict="raise",
    )
    registry.register_constraint(
        "range_contains",
        lambda c, col, ctx: col.op("@>")(c.value),
        on_conflict="raise",
    )
    registry.register_constraint(
        "range_overlap",
        lambda c, col, ctx: col.op("&&")(c.value),
        on_conflict="raise",
    )
    registry.register_constraint(
        "fulltext_match",
        lambda c, col, ctx: col.op("@@")(c.value),
        on_conflict="raise",
    )
    rules = Compiler(registry=registry, cache=False).compile(Filter, items)
    assert_custom_op(rules["meta"][0], column_name="meta", opstring="?", value="k")
    assert_custom_op(rules["tags"][0], column_name="tags", opstring="@>", value=["a"])
    assert_custom_op(rules["tags"][1], column_name="tags", opstring="&&", value=["b"])
    assert_custom_op(rules["span"][0], column_name="span", opstring="@>", value=3)
    assert_custom_op(rules["span"][1], column_name="span", opstring="&&", value=[0, 9])
    assert_custom_op(rules["body"][0], column_name="body", opstring="@@", value="q")


def test_portable_constraint_on_list_rejected(items: Table) -> None:
    class Filter(BaseModel):
        tags: Annotated[list[int], Field(ge=1)]  # type: ignore[type-var]

    with pytest.raises(UnsupportedConstraintError, match="list/dict"):
        Compiler(cache=False).compile_model(Filter)


def test_pattern_on_list_rejected(items: Table) -> None:
    class Filter(BaseModel):
        tags: Annotated[list[str], Field(pattern=r"x")]  # type: ignore[type-var]

    with pytest.raises(UnsupportedConstraintError, match="list/dict"):
        Compiler(cache=False).compile_model(Filter)


def test_markers_exported() -> None:
    assert sqlrules.JsonContains({"a": 1}).operator == "json_contains"
    assert sqlrules.JsonHasKey("a").operator == "json_has_key"
    assert sqlrules.ArrayContains([1]).operator == "array_contains"
    assert sqlrules.ArrayOverlap([1]).operator == "array_overlap"
    assert sqlrules.RangeContains(1).operator == "range_contains"
    assert sqlrules.RangeOverlap([1, 2]).operator == "range_overlap"
    assert sqlrules.FullTextMatch("foo").operator == "fulltext_match"
    assert PLUGIN_API_VERSION == "1"
