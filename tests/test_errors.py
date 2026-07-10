from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table, column

import sqlrules
from sqlrules import MissingColumnError, SQLRulesWarning, UnsupportedConstraintError
from sqlrules.ir import CompilationContext, Constraint
from sqlrules.translators import TranslatorRegistry


class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18)]


def test_missing_column_error() -> None:
    table = Table("users", MetaData(), Column("id", Integer))

    with pytest.raises(MissingColumnError):
        sqlrules.compile(UserFilter, table)


def test_invalid_model_error(users: Table) -> None:
    with pytest.raises(sqlrules.InvalidModelError):
        sqlrules.compile(object, users)  # type: ignore[arg-type]


def test_invalid_on_unsupported() -> None:
    with pytest.raises(sqlrules.ConfigurationError):
        sqlrules.Compiler(on_unsupported="explode")  # type: ignore[arg-type]


def test_unsupported_constraint_raise() -> None:
    registry = TranslatorRegistry()
    with pytest.raises(UnsupportedConstraintError):
        registry.translate(
            Constraint("name", "pattern", r"^A"),
            column("name"),
            CompilationContext(on_unsupported="raise"),
        )


def test_unsupported_constraint_warn() -> None:
    registry = TranslatorRegistry()
    with pytest.warns(SQLRulesWarning):
        result = registry.translate(
            Constraint("name", "pattern", r"^A"),
            column("name"),
            CompilationContext(on_unsupported="warn"),
        )
    assert result is None


def test_unsupported_constraint_ignore() -> None:
    registry = TranslatorRegistry()
    result = registry.translate(
        Constraint("name", "pattern", r"^A"),
        column("name"),
        CompilationContext(on_unsupported="ignore"),
    )
    assert result is None


def test_optional_literal_and_enum() -> None:
    class Status(Enum):
        ACTIVE = "ACTIVE"
        DISABLED = "DISABLED"

    class OptionalFilter(BaseModel):
        status: Literal["ACTIVE", "DISABLED"] | None = None
        kind: Status | None = None

    table = Table(
        "items",
        MetaData(),
        Column("status", String),
        Column("kind", String),
    )
    rules = sqlrules.compile(OptionalFilter, table)
    assert "status" in rules
    assert "kind" in rules


def test_version_exposed() -> None:
    assert sqlrules.__version__ == "1.0.0"
    assert callable(sqlrules.clear_model_cache)


def test_clear_model_cache_drops_default_entries() -> None:
    from sqlrules.cache import default_cache

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    default_cache().clear()
    sqlrules.Compiler(cache=True).compile_model(Filter)
    assert default_cache().get(Filter) is not None
    sqlrules.clear_model_cache()
    assert default_cache().get(Filter) is None


def test_default_registry_returns_independent_copies() -> None:
    a = sqlrules.default_registry()
    b = sqlrules.default_registry()
    assert a is not b
    assert set(a.operators()) == set(b.operators())


def test_unknown_field_metadata_key_rejected() -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class WeirdMeta:
        not_a_sqlrules_op: int = 1

    class Filter(BaseModel):
        age: Annotated[int, WeirdMeta()]

    table = Table("t", MetaData(), Column("age", Integer))
    with pytest.raises(UnsupportedConstraintError, match="not_a_sqlrules_op|Unknown metadata"):
        sqlrules.compile(Filter, table, cache=False)


def test_max_digits_only_rejected_at_extract() -> None:
    class Filter(BaseModel):
        score: Annotated[Decimal, Field(max_digits=5)]

    table = Table("t", MetaData(), Column("score", Integer))
    with pytest.raises(UnsupportedConstraintError, match="max_digits"):
        sqlrules.compile(Filter, table, cache=False)
