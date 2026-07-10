"""SQLRules 0.4 markers, PatternSpec, and list/dict type support."""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules
from sqlrules import (
    ArrayContains,
    Compiler,
    JsonContains,
    JsonHasKey,
    PatternSpec,
    UnsupportedConstraintError,
)
from sqlrules.constraints import _normalize_pattern, pattern_text
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
        Column("age", Integer),
    )


def test_marker_extracted_into_ir(items: Table) -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"active": True})]
        tags: Annotated[list[str], ArrayContains(["admin"])]

    model_ir = Compiler(cache=False).compile_model(Filter)
    by_field = {field.descriptor.name: field.constraints for field in model_ir.fields}
    assert by_field["meta"] == (Constraint("meta", "json_contains", {"active": True}),)
    assert by_field["tags"] == (Constraint("tags", "array_contains", ["admin"]),)


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
    assert "meta" in rules
    assert len(rules["meta"]) == 1
    assert rules["meta"][0] is not None


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


def test_pattern_spec_from_str() -> None:
    assert _normalize_pattern("name", r"^A") == PatternSpec(pattern=r"^A")


def test_pattern_text_helper() -> None:
    assert pattern_text(PatternSpec(pattern=r"x", ignore_case=True)) == ("x", True)
    assert pattern_text("x") == ("x", False)


def test_markers_exported() -> None:
    assert sqlrules.JsonContains({"a": 1}).operator == "json_contains"
    assert sqlrules.FullTextMatch("foo").operator == "fulltext_match"
    assert PLUGIN_API_VERSION == "1"
