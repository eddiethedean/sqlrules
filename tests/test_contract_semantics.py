"""SPEC-driven contract regressions: portable matrix, footguns, policy scope."""

from __future__ import annotations

import re
from datetime import timedelta
from enum import Enum
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, Field, Strict
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules
from assert_sql import assert_rules_sql, sql_literal
from sqlrules import (
    Compiler,
    JsonContains,
    MissingColumnError,
    PatternSpec,
    TypeSpec,
    UnsupportedConstraintError,
    clear_model_cache,
    type_spec,
)
from sqlrules.cache import ModelIRCache, default_cache
from sqlrules.constraints import pattern_text
from sqlrules.ir import Constraint


class Status(Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


@pytest.fixture
def matrix_table() -> Table:
    return Table(
        "t",
        MetaData(),
        Column("age", Integer),
        Column("qty", Integer),
        Column("name", String),
        Column("status", String),
        Column("kind", String),
    )


def test_portable_constraint_matrix_exact_sql(matrix_table: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18, le=65, multiple_of=2)]
        qty: Annotated[int, Field(gt=0, lt=100)]
        name: Annotated[str, Field(min_length=2, max_length=40)]
        status: Literal["ACTIVE", "DISABLED"]
        kind: Status

    rules = sqlrules.compile(Filter, matrix_table, cache=False)
    assert_rules_sql(
        rules,
        {
            "age": [
                "t.age >= 18",
                "t.age <= 65",
                "t.age % 2 = 0",
            ],
            "qty": ["t.qty > 0", "t.qty < 100"],
            "name": ["length(t.name) >= 2", "length(t.name) <= 40"],
            "status": ["t.status IN ('ACTIVE', 'DISABLED')"],
            "kind": ["t.kind IN ('ACTIVE', 'DISABLED')"],
        },
    )


def test_where_concatenation_order(matrix_table: Table) -> None:
    class Filter(BaseModel):
        qty: Annotated[int, Field(gt=0, lt=10)]
        age: Annotated[int, Field(ge=18)]
        name: Annotated[str, Field(min_length=1)]

    rules = sqlrules.compile(Filter, matrix_table, cache=False)
    flat = sqlrules.where(rules)
    assert [sql_literal(e) for e in flat] == [
        "t.qty > 0",
        "t.qty < 10",
        "t.age >= 18",
        "length(t.name) >= 1",
    ]
    assert sqlrules.flatten(rules) == flat


def test_on_unsupported_softens_pattern_not_bad_types(matrix_table: Table) -> None:
    class PatternOnly(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    assert sqlrules.compile(PatternOnly, matrix_table, on_unsupported="ignore") == {}

    class TimedeltaModel(BaseModel):
        delay: timedelta

    with pytest.raises(UnsupportedConstraintError, match="timedelta"):
        sqlrules.compile(TimedeltaModel, matrix_table, on_unsupported="ignore")

    class BadMultiple(BaseModel):
        age: Annotated[int, Field(multiple_of=0)]

    with pytest.raises(UnsupportedConstraintError, match="multiple_of"):
        sqlrules.compile(BadMultiple, matrix_table, on_unsupported="ignore")

    class LengthOnInt(BaseModel):
        age: Annotated[int, Field(min_length=1)]  # type: ignore[type-var]

    with pytest.raises(UnsupportedConstraintError, match="min_length"):
        sqlrules.compile(LengthOnInt, matrix_table, on_unsupported="ignore")


def test_on_unsupported_softens_marker_missing_translator(matrix_table: Table) -> None:
    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"a": 1})]

    table = Table("rows", MetaData(), Column("meta", String))
    assert sqlrules.compile(Filter, table, on_unsupported="ignore", cache=False) == {}


def test_strict_not_a_constraint_operator_feeds_typespec() -> None:
    class Filter(BaseModel):
        age: Annotated[int, Strict(), Field(ge=1)]

    without = Compiler(emit_type_checks=False, cache=False).compile_model(Filter)
    assert [c.operator for c in without.fields[0].constraints] == ["ge"]

    with_checks = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    ops = [c.operator for c in with_checks.fields[0].constraints]
    assert ops == ["ge", "type_check"]
    assert type_spec(with_checks.fields[0].constraints[1].value) == TypeSpec(
        python_type=int,
        strict=True,
        allow_none=False,
    )


def test_cache_key_includes_emit_type_checks_and_clear_scopes() -> None:
    class Filter(BaseModel):
        age: int

    custom = ModelIRCache()
    default_cache().clear()

    Compiler(cache=True, emit_type_checks=False).compile_model(Filter)
    Compiler(cache=True, emit_type_checks=True).compile_model(Filter)
    assert default_cache().get(Filter, emit_type_checks=False) is not None
    assert default_cache().get(Filter, emit_type_checks=True) is not None
    assert default_cache().get(Filter, emit_type_checks=False) is not default_cache().get(
        Filter, emit_type_checks=True
    )

    Compiler(cache=True, model_cache=custom, emit_type_checks=False).compile_model(Filter)
    assert custom.get(Filter, emit_type_checks=False) is not None

    clear_model_cache()
    assert default_cache().get(Filter, emit_type_checks=False) is None
    assert default_cache().get(Filter, emit_type_checks=True) is None
    # Custom caches are not cleared by clear_model_cache().
    assert custom.get(Filter, emit_type_checks=False) is not None


def test_dialect_hint_does_not_load_pattern_translator(matrix_table: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        Compiler(dialect="postgresql", cache=False).compile(Filter, matrix_table)


def test_pattern_flags_dotall_and_multiline_rejected() -> None:
    class Dotall(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A", re.DOTALL))]

    class Multiline(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A", re.MULTILINE))]

    with pytest.raises(UnsupportedConstraintError, match="DOTALL|flag"):
        Compiler(cache=False).compile_model(Dotall)
    with pytest.raises(UnsupportedConstraintError, match="MULTILINE|flag"):
        Compiler(cache=False).compile_model(Multiline)


def test_unanchored_pattern_still_extracts_pattern_spec() -> None:
    """Dialects may use search/substring match; Pydantic validates fullmatch.

    SQLRules extracts the pattern text as-is. Dialects are not required to
    emulate Pydantic fullmatch for unanchored patterns.
    """

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"abc")]

    model_ir = Compiler(cache=False).compile_model(Filter)
    assert model_ir.fields[0].constraints == (
        Constraint("name", "pattern", PatternSpec(pattern=r"abc")),
    )
    assert pattern_text(model_ir.fields[0].constraints[0].value) == ("abc", False)


def test_pattern_text_helper_round_trip() -> None:
    assert pattern_text(PatternSpec(pattern=r"x", ignore_case=True)) == ("x", True)
    assert pattern_text("x") == ("x", False)


def test_constrained_field_missing_column_raises(matrix_table: Table) -> None:
    class Filter(BaseModel):
        missing: Annotated[int, Field(ge=1)]

    with pytest.raises(MissingColumnError, match="missing"):
        sqlrules.compile(Filter, matrix_table, cache=False)


def test_pattern_text_rejects_invalid_value() -> None:
    with pytest.raises(TypeError, match="PatternSpec"):
        pattern_text(123)  # type: ignore[arg-type]


def test_invalid_pattern_value_rejected_at_normalize() -> None:
    from sqlrules.constraints import _normalize_pattern

    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        _normalize_pattern("name", 123)


def test_pattern_spec_passthrough_and_ignore_case() -> None:
    from sqlrules.constraints import _normalize_pattern

    spec = PatternSpec(pattern=r"x", ignore_case=True)
    assert _normalize_pattern("name", spec) is spec


def test_translator_must_return_column_element(matrix_table: Table) -> None:
    from sqlrules.translators import default_registry

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    registry = default_registry().copy()
    registry.register_constraint(
        "ge",
        lambda c, col, ctx: "not-an-expression",  # type: ignore[return-value,arg-type]
        on_conflict="replace",
    )
    with pytest.raises(sqlrules.TranslatorError, match="ColumnElement"):
        Compiler(registry=registry, cache=False).compile(Filter, matrix_table)


def test_unsupported_constraint_error_str_without_suggestion() -> None:
    err = UnsupportedConstraintError(field="age", operator="pattern", value=r"x")
    assert "age" in str(err)
    assert "pattern" in str(err)


def test_invalid_translator_error_str() -> None:
    err = sqlrules.InvalidTranslatorError(operator="gt", translator=None)
    assert "gt" in str(err)
    assert "None" in str(err)


def test_enum_and_literal_constraint_mismatches_still_raise() -> None:
    class Status(Enum):
        A = "A"

    class EnumBad(BaseModel):
        kind: Annotated[Status, Field(ge=1)]

    class LiteralBad(BaseModel):
        status: Annotated[Literal["A", "B"], Field(min_length=1)]

    with pytest.raises(UnsupportedConstraintError, match="ge"):
        Compiler(cache=False).compile_model(EnumBad)
    with pytest.raises(UnsupportedConstraintError, match="min_length"):
        Compiler(cache=False).compile_model(LiteralBad)
